import hashlib
import logging
from datetime import datetime

import scrapy
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

from scrapy.http import Response

from op_tcg.backend.crawling.items import LimitlessPriceRow, ReleaseSetItem
from op_tcg.backend.etl.load import get_or_create_table
from op_tcg.backend.models.cards import CardPrice, Card, OPTcgLanguage, CardReleaseSet, OPTcgCardSetType
from google.cloud import bigquery

from op_tcg.backend.models.common import DataSource
from op_tcg.backend.models.input import get_meta_format_by_datetime, MetaFormat, meta_format2release_datetime


class LimitlessPricesSpider(scrapy.Spider):
    name = "limitless_prices"

    def get_release_sets(self) -> list[CardReleaseSet]:
        """Returns list of CardReleaseSet stored in bq"""
        release_sets: list[CardReleaseSet] = []
        for card_row in self.bq_client.query(
                f"SELECT * FROM `{self.release_set_table.full_table_id.replace(':', '.')}` where source = '{DataSource.LIMITLESS}'").result():
            release_sets.append(CardReleaseSet(**dict(card_row)))
        return release_sets


    def start_requests(self):
        self.bq_client = bigquery.Client(location="europe-west3")
        self.card_table = get_or_create_table(Card, client=self.bq_client)
        self.price_table = get_or_create_table(CardPrice, client=self.bq_client)
        self.release_set_table = get_or_create_table(CardReleaseSet, client=self.bq_client)
        self.price_count: dict[str, dict[int, int]] = {} # dict[card id, dict[aa_version, count]]

        start_url = "https://onepiece.limitlesstcg.com/cards/en"
        yield scrapy.Request(url=f"{start_url}",
                             callback=self.parse_set_url,
                             meta={"language": OPTcgLanguage.EN})

    def parse_set_url(self, response):
        # Format of date column
        bq_release_sets = self.get_release_sets()
        bq_release_set_ids = [bq_release_set.id for bq_release_set in bq_release_sets]

        try:
            limitless_release_sets: list[CardReleaseSet] = self.get_parsed_release_sets(response)
        except Exception as e:
            logging.warning(f"Something went wrong during release set crawling, {str(e)}")
            limitless_release_sets = []

        release_sets_not_yet_crawled = []
        for limitless_release_set in limitless_release_sets:
            if limitless_release_set.id not in bq_release_set_ids:
                release_sets_not_yet_crawled.append(limitless_release_set)
                # send to pipeline which updates big query
                yield ReleaseSetItem(release_set=limitless_release_set)

        for release_set in (bq_release_sets + release_sets_not_yet_crawled):
            yield scrapy.Request(url=f"{release_set.url}?display=list&sort=id&show=all&unique=prints",
                                 callback=self.parse,
                                 meta = {
                  'dont_redirect': True,
                  'handle_httpstatus_list': [302],
                  'release_set': release_set,
                  'language': response.meta.get('language')
                                 })

    @staticmethod
    def get_parsed_release_sets(response: Response) -> list[CardReleaseSet]:
        release_sets: list[CardReleaseSet] = []

        language: OPTcgLanguage = response.meta.get("language")
        base_url = f"{urlparse(response.url).scheme}://{urlparse(response.url).netloc}"

        # index must match the right table, as each table has different date format
        date_formats = ["%d %b %y", "%b %y"]
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        # Find the table with the class 'data-table striped highlight card-list'
        tables = soup.find_all('table', class_='data-table')
        if len(date_formats) != len(tables):
            raise ValueError("Date format is not defined for all tables")
        for i, table in enumerate(tables):
            date_format = date_formats[i]
            # Extract the table headers
            headers = [header.get_text(strip=True) for header in table.find("tr").find_all('th')]
            set_type: OPTcgCardSetType | None = None

            prev_sibling = table.previous_sibling.previous_sibling
            if prev_sibling and prev_sibling.get("id") == "promo":
                set_type = OPTcgCardSetType.PROMO

            # Extract the table rows
            for row in table.find_all('tr')[1:]:  # Skip the header row
                if row.find(class_="sub-heading") is not None:
                    if "booster" in row.find(class_="sub-heading").text.lower():
                        set_type = OPTcgCardSetType.BOOSTER
                    elif "starter deck" in row.find(class_="sub-heading").text.lower():
                        set_type = OPTcgCardSetType.STARTER_DECK
                    # skip row as it only contains a sub heading
                    continue

                cells = row.find_all('td')
                row_data = {header: cell for header, cell in zip(headers, cells)}
                code: str | None = row_data["Code"].get_text(strip=True) if "Code" in row_data else None

                # Parse the string into a datetime object
                date_string = row_data['Release Date'].get_text(strip=True)
                if date_string != "":
                    release_datetime = datetime.strptime(date_string, date_format)
                    # if day can not be extracted, we expect end of the month to prevent unexpected miss matching (e.g. meta format)
                    if "%d" not in date_format:
                        release_datetime = release_datetime.replace(day=28)

                    release_datetime = max(release_datetime, meta_format2release_datetime(MetaFormat.OP01))
                    meta_format = get_meta_format_by_datetime(release_datetime)
                else:
                    release_datetime = None
                    meta_format = None
                # ignore sets with japanese suffix or future release
                if row_data["Name"].get_text(strip=True)[-2:] == "JP" or (
                        release_datetime and (release_datetime > datetime.now())):
                    continue
                release_set_name = row_data["Name"].get_text(strip=True)
                id = LimitlessPricesSpider.get_release_set_id(release_set_name, code, release_datetime)
                release_sets.append(CardReleaseSet(
                    id=id,
                    language=language,
                    name=release_set_name,
                    meta_format=meta_format,
                    release_date=release_datetime.date() if release_datetime else None,
                    card_count=int(row_data["Cards"].get_text().split(" ")[0]),
                    code=code,
                    type=set_type,
                    url=f'{base_url}{row_data["Cards"].find("a").get("href")}',
                    source=DataSource.LIMITLESS
                ))

        return release_sets

    @staticmethod
    def get_release_set_id(release_set_name: str, code: str | None, release_datetime: datetime | None):
        id_hash_input = f"{release_set_name}{release_datetime.date() if release_datetime else ''}"
        if code is not None:
            id = f"{code}_{release_datetime.strftime('%y')}" if release_datetime else code
        else:
            id = hashlib.md5(id_hash_input.encode('utf-8')).hexdigest()
        return id

    @staticmethod
    def extract_price_usd(price_str: str) -> float:
        """
        Extracts the price as a float from a string formatted like "$1,787.98".

        Parameters:
        price_str (str): A string representing the price, starting with a dollar sign.

        Returns:
        float: The extracted price as a float.
        """
        # Remove the dollar sign and commas, then convert the remaining string to a float
        try:
            cleaned_str = price_str.replace('$', '').replace(',', '').strip()
            price = float(cleaned_str)
        except ValueError:
            raise ValueError("The input string is not in the expected format.")

        return price

    @staticmethod
    def extract_price_euro(price_str, decimal_seperator="."):
        """
        Extracts the price as a float from a string formatted like "2,250.00 €".

        Parameters:
        price_str (str): A string representing the price, ending with the euro sign.

        Returns:
        float: The extracted price as a float.
        """
        # Remove the euro sign and periods, replace commas with dots, then convert to float
        try:
            if decimal_seperator == ".":
                cleaned_str = price_str.replace('€', '').replace(',', '').strip()
            elif decimal_seperator == ",":
                cleaned_str = price_str.replace('€', '').replace('.', '').replace(',', '.').strip()
            else:
                raise NotImplementedError
            price = float(cleaned_str)
        except ValueError:
            raise ValueError("The input string is not in the expected format.")

        return price

    def parse(self, response):
        release_set: CardReleaseSet = response.meta.get("release_set")
        language = response.meta.get("language")
        if OPTcgLanguage.JP in urlparse(response.url).path.split('/'):
            language = OPTcgLanguage.JP

        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the table with the class 'data-table striped highlight card-list'
        table = soup.find('table', class_='data-table')

        # Extract the table headers
        headers = [header.get_text(strip=True) for header in table.find_all('th')]
        decimal_seperator = "."
        count_comma = len([price_eur.text for price_eur in table.find_all("a", class_="card-price eur") if "," in price_eur.text])
        count_dot = len([price_eur.text for price_eur in table.find_all("a", class_="card-price eur") if "." in price_eur.text])
        if count_comma > count_dot:
            decimal_seperator = ","

        # Extract the table rows
        rows: list[LimitlessPriceRow] = []
        for row in table.find_all('tr')[1:]:  # Skip the header row
            cells = row.find_all('td')
            row_data = {header: cell.get_text(strip=True) for header, cell in zip(headers, cells)}
            card_url = cells[headers.index("Card")].find("a").get("href")
            if row_data["Card"] not in card_url:
                raise ValueError(f"url id {card_url }does not match card id {row_data['Card']}")
            aa_version = parse_qs(urlparse(card_url).query).get("v", 0)
            if type(aa_version) == list:
                aa_version = int(aa_version[0])

            rows.append(LimitlessPriceRow(
                card_id=row_data["Card"],
                name=row_data["Rarity"],
                aa_version=aa_version,
                language=language,
                card_category=row_data["Category"],
                rarity=row_data["Rarity"],
                price_usd=self.extract_price_usd(row_data["USD"]),
                price_eur=self.extract_price_euro(row_data["EUR"], decimal_seperator=decimal_seperator)
            ))

        for row in rows:
            yield row

    def closed(self, reason):
        sum_price_updates = sum(count for card in self.price_count.values() for count in card.values())
        logging.info(f"Finished spider with {sum_price_updates} price updates")