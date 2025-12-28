import hashlib
import logging
from datetime import datetime

import scrapy
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

from pydantic import BaseModel, Field
from scrapy.http import Response

from op_tcg.backend.crawling.items import LimitlessPriceRow, ReleaseSetItem, CardsItem
from op_tcg.backend.etl.extract import extract_card_prices, limitless_soup2base_cards, limitless_soup2base_card, \
    base_card2bq_card, extract_marketplace_urls
from op_tcg.backend.etl.load import get_or_create_table
from op_tcg.backend.models.cards import CardPrice, Card, OPTcgLanguage, CardReleaseSet, OPTcgCardSetType, BaseCard, \
    CardMarketplaceUrl, OPTcgMarketplace
from google.cloud import bigquery

from op_tcg.backend.models.common import DataSource
from op_tcg.backend.models.input import get_meta_format_by_datetime, MetaFormat, meta_format2release_datetime, \
    MetaFormatRegion


class ReleaseSetCardsInfo(BaseModel):
    total_cards_to_crawl: int | None = Field(description="Expected number of cards which should be crawled at the end")
    cards: list[Card]
    marketplace_urls: list[CardMarketplaceUrl] = []

    def is_ready_for_bq_load(self):
        if self.total_cards_to_crawl is None:
            return False
        return self.total_cards_to_crawl == len(self.cards)


class LimitlessPricesSpider(scrapy.Spider):
    name = "limitless_prices"

    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
        'COOKIES_ENABLED': True,
    }
    def get_release_sets(self) -> list[CardReleaseSet]:
        """Returns list of CardReleaseSet stored in bq"""
        release_sets: list[CardReleaseSet] = []
        for card_row in self.bq_client.query(
                f"SELECT * FROM `{self.release_set_table.full_table_id.replace(':', '.')}` where source = '{DataSource.LIMITLESS}'").result():
            release_sets.append(CardReleaseSet(**dict(card_row)))
        return release_sets

    @staticmethod
    def get_id_language(id: str, language: OPTcgLanguage | str) -> str:
        return f"{id}_{language}"

    def get_card_ids(self) -> dict[str, list[str]]:
        """Returns dict of card ids + language and aa versions stored in bq"""
        card_ids_to_aa_version: dict[str, list[str]] = {}
        for card_row in self.bq_client.query(
                f"SELECT id, language, aa_version FROM `{self.card_table.full_table_id.replace(':', '.')}` order by aa_version").result():
            id = dict(card_row).get("id")
            language = dict(card_row).get("language")
            id_language = self.get_id_language(id, language)
            aa_version = dict(card_row).get("aa_version")
            if id_language not in card_ids_to_aa_version:
                card_ids_to_aa_version[id_language] = [aa_version]
            else:
                card_ids_to_aa_version[id_language].append(aa_version)
        return card_ids_to_aa_version

    def get_marketplace_urls(self) -> dict[str, list[int]]:
        """Returns dict of card ids + language and aa versions stored in bq for marketplace urls"""
        card_ids_to_aa_version: dict[str, list[int]] = {}
        try:
            for row in self.bq_client.query(
                    f"SELECT card_id, language, aa_version FROM `{self.marketplace_url_table.full_table_id.replace(':', '.')}`").result():
                id = dict(row).get("card_id")
                language = dict(row).get("language")
                id_language = self.get_id_language(id, language)
                aa_version = dict(row).get("aa_version")
                if id_language not in card_ids_to_aa_version:
                    card_ids_to_aa_version[id_language] = [aa_version]
                else:
                    card_ids_to_aa_version[id_language].append(aa_version)
        except Exception as e:
            logging.warning(f"Could not fetch marketplace urls: {e}")
        return card_ids_to_aa_version

    def start_requests(self):
        self.bq_client = bigquery.Client(location="europe-west3")
        self.card_table = get_or_create_table(Card, client=self.bq_client)
        self.price_table = get_or_create_table(CardPrice, client=self.bq_client)
        self.release_set_table = get_or_create_table(CardReleaseSet, client=self.bq_client)
        self.marketplace_url_table = get_or_create_table(CardMarketplaceUrl, client=self.bq_client)
        self.price_count: dict[str, dict[int, int]] = {}  # dict[card id, dict[aa_version, count]]
        self.card_count: dict[str, dict[int, int]] = {}  # dict[card id, dict[aa_version, count]]

        self.bq_card_ids = self.get_card_ids()
        self.bq_marketplace_urls = self.get_marketplace_urls()
        self.release_set_it_to_cards_info: dict[str, ReleaseSetCardsInfo] = {}

        start_urls = ["https://onepiece.limitlesstcg.com/cards/promos", "https://onepiece.limitlesstcg.com/cards"]
        for start_url in start_urls:
            yield scrapy.Request(url=start_url,
                                 callback=self.parse_set_url,
                                 errback=self.errback_httpbin,
                                 meta={"language": OPTcgLanguage.EN})

    def parse_set_url(self, response):
        is_promo_crawl = "promos" in response.url
        # Format of date column
        bq_release_sets = self.get_release_sets()
        bq_release_set_ids = [self.get_id_language(bq_release_set.id, bq_release_set.language) for bq_release_set in bq_release_sets]

        try:
            limitless_release_sets: list[CardReleaseSet] = self.get_parsed_release_sets(response, is_promo_crawl=is_promo_crawl)
        except Exception as e:
            logging.warning(f"Something went wrong during release set crawling, {str(e)}")
            limitless_release_sets = []

        release_sets_not_yet_crawled = []
        for limitless_release_set in limitless_release_sets:
            if self.get_id_language(limitless_release_set.id, limitless_release_set.language) not in bq_release_set_ids:
                release_sets_not_yet_crawled.append(limitless_release_set)
                # send to pipeline which updates big query
                yield ReleaseSetItem(release_set=limitless_release_set)

        release_sets_to_crawl = release_sets_not_yet_crawled
        if not is_promo_crawl:
            # in case of standard crawl we also update price information of existing sets in BQ
            release_sets_to_crawl.extend(bq_release_sets)

        for release_set in release_sets_to_crawl:
            yield scrapy.Request(url=f"{release_set.url}?display=list&sort=id&show=all&unique=prints",
                                 callback=self.parse_price_page,
                                 errback=self.errback_httpbin,
                                 meta={
                                     # 'dont_redirect': True,
                                     # 'handle_httpstatus_list': [302],
                                     'release_set': release_set,
                                     'language': response.meta.get('language'),
                                     'release_set_language': release_set.language
                                 })

    @staticmethod
    def get_parsed_release_sets(response: Response, is_promo_crawl: bool = False) -> list[CardReleaseSet]:
        release_sets: list[CardReleaseSet] = []

        language: OPTcgLanguage = response.meta.get("language")
        base_url = f"{urlparse(response.url).scheme}://{urlparse(response.url).netloc}"

        # index must match the right table, as each table has different date format
        date_formats = ["%b %y" if is_promo_crawl else "%d %b %y"]
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
                    meta_format = get_meta_format_by_datetime(release_datetime, region=MetaFormatRegion.WEST)
                else:
                    release_datetime = None
                    meta_format = None
                # ignore sets with japanese suffix or future release
                # if row_data["Name"].get_text(strip=True)[-2:] == "JP" or (
                #         release_datetime and (release_datetime > datetime.now())):
                #     continue
                is_jp_set = row_data["Name"].get_text(strip=True)[-2:] == "JP"
                release_set_name = row_data["Name"].get_text(strip=True).strip("JP")
                id = LimitlessPricesSpider.get_release_set_id(release_set_name, code, release_datetime)
                release_sets.append(CardReleaseSet(
                    id=id,
                    language=OPTcgLanguage.JP if is_jp_set else language,
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

    def parse_price_page(self, response):
        release_set: CardReleaseSet = response.meta.get("release_set")
        language = response.meta.get("language")
        release_set_language = response.meta.get("release_set_language")

        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the table with the class 'data-table striped highlight card-list'
        table = soup.find('table', class_='data-table')

        # Extract the table headers
        headers = [header.get_text(strip=True) for header in table.find_all('th')]
        decimal_seperator = "."
        count_comma = len(
            [price_eur.text for price_eur in table.find_all("a", class_="card-price eur") if "," in price_eur.text])
        count_dot = len(
            [price_eur.text for price_eur in table.find_all("a", class_="card-price eur") if "." in price_eur.text])
        if count_comma > count_dot:
            decimal_seperator = ","

        # Extract the table rows
        card_ids_not_yet_crawled: dict[str, list[str]] = {}  # key: card_id, value: aa versions
        def add_card_id_aa_version(card_id, aa_version):
            if card_id not in card_ids_not_yet_crawled:
                card_ids_not_yet_crawled[card_id] = [aa_version]
            else:
                card_ids_not_yet_crawled[card_id].append(aa_version)

        rows: list[LimitlessPriceRow] = []
        try:
            for row in table.find_all('tr')[1:]:  # Skip the header row
                cells = row.find_all('td')
                row_data = {header: cell.get_text(strip=True) for header, cell in zip(headers, cells)}
                card_url = cells[headers.index("Card")].find("a").get("href")
                if row_data["Card"] not in card_url:
                    raise ValueError(f"url id {card_url}does not match card id {row_data['Card']}")
                aa_version = parse_qs(urlparse(card_url).query).get("v", 0)
                if type(aa_version) == list:
                    aa_version = int(aa_version[0])
                card_id = row_data["Card"]
                card_id_language = self.get_id_language(card_id, release_set_language)
                # (not in bq yet) or (card_id in bq but not aa version)
                card_missing = (card_id_language not in self.bq_card_ids) or (aa_version not in self.bq_card_ids[card_id_language])

                marketplace_missing = True
                # ignore marketplace for jp cards as they are not listed on target page
                if card_id_language.endswith(f"_{OPTcgLanguage.JP}"):
                    marketplace_missing = False
                if card_id_language in self.bq_marketplace_urls:
                     if aa_version in self.bq_marketplace_urls[card_id_language]:
                         marketplace_missing = False

                if card_missing or marketplace_missing:
                    add_card_id_aa_version(card_id_language, aa_version)

                rows.append(LimitlessPriceRow(
                    card_id=card_id,
                    name=row_data["Rarity"],
                    aa_version=aa_version,
                    language=OPTcgLanguage.EN, # prices are always for western markets on limitless
                    card_category=row_data["Category"],
                    rarity=row_data["Rarity"],
                    price_usd=None if row_data["USD"].strip() in ["-", ""] else self.extract_price_usd(row_data["USD"]),
                    price_eur=None if row_data["EUR"].strip() in ["-", ""] else self.extract_price_euro(row_data["EUR"], decimal_seperator=decimal_seperator)
                ))
        except Exception as e:
            logging.error(f"Could not extract card price row {str(e)}")

        # price information to big query
        for row in rows:
            yield row

        total_cards_to_crawl = sum(len(aa_versions) for aa_versions in card_ids_not_yet_crawled.values())
        self.release_set_it_to_cards_info[release_set.id] = ReleaseSetCardsInfo(total_cards_to_crawl=total_cards_to_crawl, cards=[])
        for card_id_language, aa_versions in card_ids_not_yet_crawled.items():
            card_id, set_language = "_".join(card_id_language.split("_")[:-1]), card_id_language.split("_")[-1]
            limitless_url = f"https://onepiece.limitlesstcg.com/cards/{language}/{card_id}?v=0"
            yield scrapy.Request(url=limitless_url,
                                 callback=self.parse_card_page,
                                 errback=self.errback_httpbin,
                                 dont_filter=True, # enforce callback be called, even if same url ist requested multiple times
                                 meta={
                                     'release_set': release_set,
                                     'language': language,
                                     'release_set_language': release_set_language,
                                     'card_id': card_id,
                                     'aa_versions': aa_versions,
                                 })

    def parse_card_page(self, response):
        release_set: CardReleaseSet = response.meta.get("release_set")
        aa_versions: list[int] = response.meta.get("aa_versions")
        language: OPTcgLanguage = response.meta.get("language")
        release_set_language: OPTcgLanguage = response.meta.get("release_set_language")
        if release_set_language == OPTcgLanguage.JP:
            pass
        card_id: str = response.meta.get("card_id")

        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract marketplace URLs
        marketplace_urls: list[CardMarketplaceUrl] = extract_marketplace_urls(soup, card_id, release_set_language, aa_versions)

        self.release_set_it_to_cards_info[release_set.id].marketplace_urls.extend(marketplace_urls)

        # extract text data
        cards: list[Card] = []
        for aa_version in aa_versions:
            try:
                base_card: BaseCard = limitless_soup2base_card(card_id, release_set_language, soup, aa_version=aa_version)
                base_card.release_set_id = release_set.id
                cards.append(base_card2bq_card(base_card, soup))
            except Exception as e:
                logging.error(f"Could not extract card information from limitless {str(e)}")

        self.release_set_it_to_cards_info[release_set.id].cards.extend(cards)

        if self.release_set_it_to_cards_info[release_set.id].is_ready_for_bq_load():
            yield CardsItem(
                cards=self.release_set_it_to_cards_info[release_set.id].cards,
                marketplace_urls=self.release_set_it_to_cards_info[release_set.id].marketplace_urls,
            )

    def errback_httpbin(self, failure):
        # log all failures
        self.logger.error(repr(failure))

    def closed(self, reason):
        sum_price_updates = sum(count for card in self.price_count.values() for count in card.values())
        sum_card_updates = sum(count for card in self.card_count.values() for count in card.values())
        logging.info(f"Finished spider with {sum_price_updates} price updates and {sum_card_updates} card updates")
