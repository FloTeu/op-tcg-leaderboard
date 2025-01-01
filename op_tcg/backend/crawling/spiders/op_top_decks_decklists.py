import hashlib
import logging
from datetime import datetime

import scrapy
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

from op_tcg.backend.crawling.items import ReleaseSetItem
from op_tcg.backend.etl.load import get_or_create_table
from op_tcg.backend.models.cards import  CardReleaseSet
from google.cloud import bigquery

from op_tcg.backend.models.common import DataSource
from op_tcg.backend.models.decklists import OpTopDeckDecklistExtended, Decklist, OpTopDeckDecklist
from op_tcg.backend.models.input import get_meta_format_by_datetime, MetaFormat, meta_format2release_datetime


class OPTopDeckDecklistSpider(scrapy.Spider):
    name = "op_top_decks_decklists"

    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
        'COOKIES_ENABLED': True,
    }

    def get_bq_decklists(self) -> list[OpTopDeckDecklistExtended]:
        """Returns list of OPTopDeckDecklistExtended stored in bq"""
        bq_decklists: list[OpTopDeckDecklistExtended] = []
        for card_row in self.bq_client.query(
                f"SELECT * FROM `{self.op_top_deck_table.full_table_id.replace(':', '.')}` as t1 "
                f"LEFT JOIN `{self.decklist_table.full_table_id.replace(':', '.')}` as t2 on t1.decklist_id = t2.id").result():
            bq_decklists.append(OpTopDeckDecklistExtended(**dict(card_row)))
        return bq_decklists


    def start_requests(self):
        self.bq_client = bigquery.Client(location="europe-west3")
        self.decklist_table = get_or_create_table(Decklist, client=self.bq_client)
        self.op_top_deck_table = get_or_create_table(OpTopDeckDecklist, client=self.bq_client)

        self.bq_decklists = self.get_bq_decklists()


        start_url = "https://onepiecetopdecks.com/deck-list"
        yield scrapy.Request(url=start_url,
                             callback=self.parse_decklist_landingpage,
                             errback=self.errback_httpbin)

    def parse_decklist_landingpage(self, response):
        """Extracts all meta format and country meta format urls for further steps"""
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
                                 callback=self.parse_price_page,
                                 errback=self.errback_httpbin,
                                 meta={
                                     # 'dont_redirect': True,
                                     # 'handle_httpstatus_list': [302],
                                     'release_set': release_set,
                                     'language': response.meta.get('language')
                                 })

    def errback_httpbin(self, failure):
        # log all failures
        self.logger.error(repr(failure))

    def closed(self, reason):
        sum_price_updates = sum(count for card in self.price_count.values() for count in card.values())
        sum_card_updates = sum(count for card in self.card_count.values() for count in card.values())
        logging.info(f"Finished spider with {sum_price_updates} price updates and {sum_card_updates} card updates")
