import logging

import scrapy
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

from op_tcg.backend.crawling.items import LimitlessPriceRow
from op_tcg.backend.etl.load import get_or_create_table
from op_tcg.backend.models.cards import CardPrice, Card, OPTcgLanguage
from google.cloud import bigquery


class LimitlessPricesSpider(scrapy.Spider):
    name = "limitless_prices"

    def get_set_urls(self) -> list[str]:
        """Returns list of urls with price information"""
        urls: list[str] = []
        for card_row in self.bq_client.query(
                f"SELECT DISTINCT(release_set_url) FROM `{self.card_table.full_table_id.replace(':', '.')}`").result():
            if "limitlesstcg" in card_row["release_set_url"]:
                urls.append(card_row["release_set_url"])
        return urls


    def start_requests(self):
        self.bq_client = bigquery.Client(location="europe-west3")
        self.card_table = get_or_create_table(Card, client=self.bq_client)
        self.price_table = get_or_create_table(CardPrice, client=self.bq_client)
        self.price_count: dict[str, dict[int, int]] = {} # dict[card id, dict[aa_version, count]]
        urls = self.get_set_urls()

        for url in urls:
            yield scrapy.Request(url=f"{url}?display=list&sort=id&show=all&unique=prints",
                                 callback=self.parse,
                                 meta = {
                  'dont_redirect': True,
                  'handle_httpstatus_list': [302]
              })


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
        language = OPTcgLanguage.EN
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