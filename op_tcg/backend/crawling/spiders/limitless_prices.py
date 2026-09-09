import hashlib
import logging
from datetime import datetime

import scrapy
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

from scrapy.http import Response

from op_tcg.backend.crawling.items import ReleaseSetItem, CardsItem, CardPricesItem
from op_tcg.backend.etl.extract import extract_card_prices, limitless_soup2base_card, \
    base_card2bq_card, extract_marketplace_urls
from op_tcg.backend.etl.load import get_or_create_table
from op_tcg.backend.models.cards import CardPrice, Card, OPTcgLanguage, CardReleaseSet, OPTcgCardSetType, \
    CardMarketplaceUrl
from google.cloud import bigquery

from op_tcg.backend.models.common import DataSource
from op_tcg.backend.models.input import get_meta_format_by_datetime, MetaFormat, meta_format2release_datetime, \
    MetaFormatRegion


class LimitlessPricesSpider(scrapy.Spider):
    name = "limitless_prices"

    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
        'COOKIES_ENABLED': True,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.price_count: dict[str, dict[int, int]] = {}  # dict[card id, dict[aa_version, count]]
        self.card_count: dict[str, dict[int, int]] = {}  # dict[card id, dict[aa_version, count]]

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

    async def start(self):
        self.bq_client = bigquery.Client(location="europe-west1")
        self.card_table = get_or_create_table(Card, client=self.bq_client)
        self.price_table = get_or_create_table(CardPrice, client=self.bq_client)
        self.release_set_table = get_or_create_table(CardReleaseSet, client=self.bq_client)
        self.marketplace_url_table = get_or_create_table(CardMarketplaceUrl, client=self.bq_client)

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
            yield scrapy.Request(url=f"{release_set.url}?display=full&sort=id&show=all&unique=prints",
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
                raw_release_set_name = row_data["Name"].get_text(strip=True)
                is_jp_set = raw_release_set_name[-2:] == "JP"
                release_set_name = raw_release_set_name.removesuffix("JP").strip() if is_jp_set else raw_release_set_name
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
    def _block_aa_version(card_block) -> int:
        """The aa_version a card-page-main block represents, from its own '?v=N' link."""
        name_link = card_block.find('span', class_='card-text-name').find('a')
        if name_link and name_link.get('href'):
            v = parse_qs(urlparse(name_link['href']).query).get('v')
            if v:
                return int(v[0])
        return 0

    def parse_price_page(self, response):
        """
        Parses a release set's full card view (``display=full``). Each card gets its own
        ``div.card-page-main`` block containing both its legality/attributes (``card-profile``)
        and its full print/price history (``card-prints-versions``) - the same markup a single
        card's own page uses. This means every card's data (including legality) is refreshed on
        every crawl, not just the first time a card is seen.

        ``unique=prints`` gives a card one block per print *that this release set introduced* -
        a card can have other aa_versions belonging to a different (e.g. later) release, which
        show up in the embedded prints-versions table for price context but must NOT be attributed
        to this release_set or re-emitted here, otherwise they'd get their release_set_id and price
        history overwritten/duplicated by every release page that happens to reference the card.
        """
        release_set: CardReleaseSet = response.meta.get("release_set")
        release_set_language = response.meta.get("release_set_language")

        soup = BeautifulSoup(response.text, 'html.parser')

        cards: list[Card] = []
        marketplace_urls: list[CardMarketplaceUrl] = []
        prices: list[CardPrice] = []

        # group blocks by card id; multiple blocks per id means multiple aa_versions
        # were introduced by this release set (e.g. a leader plus its alt art)
        card_id2blocks: dict[str, list] = {}
        for card_block in soup.find_all('div', class_='card-page-main'):
            id_span = card_block.find('span', class_='card-text-id')
            if id_span is None:
                continue
            card_id2blocks.setdefault(id_span.text.strip(), []).append(card_block)

        for card_id, blocks in card_id2blocks.items():
            own_aa_versions = [self._block_aa_version(block) for block in blocks]
            representative_block = blocks[0]
            try:
                all_prices = extract_card_prices(card_id, release_set_language, representative_block)
                prices.extend(price for price in all_prices if price.aa_version in own_aa_versions)

                for aa_version in own_aa_versions:
                    base_card = limitless_soup2base_card(card_id, release_set_language, representative_block,
                                                          aa_version=aa_version)
                    base_card.release_set_id = release_set.id
                    cards.append(base_card2bq_card(base_card, representative_block))

                marketplace_urls.extend(extract_marketplace_urls(representative_block, card_id, release_set_language,
                                                                  own_aa_versions))
            except Exception as e:
                logging.error(f"Could not extract card information from limitless for {card_id}: {str(e)}")

        if cards:
            yield CardsItem(cards=cards, marketplace_urls=marketplace_urls)
        if prices:
            yield CardPricesItem(prices=prices)

    def errback_httpbin(self, failure):
        # log all failures
        self.logger.error(repr(failure))

    def closed(self, reason):
        sum_price_updates = sum(count for card in self.price_count.values() for count in card.values())
        sum_card_updates = sum(count for card in self.card_count.values() for count in card.values())
        logging.info(f"Finished spider with {sum_price_updates} price updates and {sum_card_updates} card updates")
