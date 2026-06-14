import logging
import re
import os
from contextlib import suppress
from datetime import datetime, timedelta
from dateutil import parser

import scrapy
import bs4
from bs4 import BeautifulSoup

from op_tcg.backend.crawling.items import OpTopDecksItem
from op_tcg.backend.etl.load import get_or_create_table
from google.cloud import bigquery

from op_tcg.backend.models.common import DataSource
from op_tcg.backend.models.decklists import OpTopDeckDecklistExtended, Decklist, OpTopDeckDecklist
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion, meta_format2side_meta_format
from op_tcg.backend.models.tournaments import TournamentRecord, Tournament, TournamentStanding
from op_tcg.backend.utils.database import create_decklist_id


class OPTopDeckDecklistSpider(scrapy.Spider):
    name = "op_top_decks_decklists"

    meta_formats: list[MetaFormat]

    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
        'COOKIES_ENABLED': True,
        'DOWNLOADER_MIDDLEWARES': {
            # Runs just before the built-in RetryMiddleware (550) so 202s are
            # caught here with exponential back-off before any other retry logic.
            'op_tcg.backend.crawling.middlewares.Retry202Middleware': 540,
        },
    }

    def __init__(self, *args, delete_existing: bool = False, **kwargs):
        logging.info("OPTopDeckDecklistSpider: initializing Class")
        super().__init__(*args, **kwargs)
        self.bq_add_data_stats: dict[str, int] = {}
        self.delete_existing = delete_existing

    def delete_bq_tournament_standings(self) -> int:
        """Deletes tournament_standing rows for OP Top Decks tournaments in the selected meta formats."""
        meta_format_values = ", ".join(f"'{mf.value}'" for mf in self.meta_formats)
        ts_id = self.tournament_standing_table.full_table_id.replace(":", ".")
        t_id = self.tournament_table.full_table_id.replace(":", ".")
        delete_sql = f"""
        DELETE FROM `{ts_id}`
        WHERE tournament_id IN (
          SELECT id FROM `{t_id}`
          WHERE source = '{DataSource.OP_TOP_DECKS}'
          AND meta_format IN ({meta_format_values})
        )
        """
        query_job = self.bq_client.query(delete_sql)
        query_job.result()
        deleted = query_job.num_dml_affected_rows or 0
        self.logger.info("Deleted %d tournament_standing rows for meta formats %s", deleted, meta_format_values)
        return deleted

    def get_bq_op_top_deck_decklists(self) -> list[OpTopDeckDecklistExtended]:
        """Returns list of OPTopDeckDecklistExtended stored in bq"""
        bq_decklists: list[OpTopDeckDecklistExtended] = []
        for card_row in self.bq_client.query(
                f"SELECT * FROM `{self.op_top_deck_table.full_table_id.replace(':', '.')}` as t1 "
                f"LEFT JOIN `{self.decklist_table.full_table_id.replace(':', '.')}` as t2 on t1.decklist_id = t2.id").result():
            bq_decklists.append(OpTopDeckDecklistExtended(**dict(card_row)))
        return bq_decklists

    def get_bq_decklist_ids(self) -> list[str]:
        """Returns list of decklist ids stored in bq"""
        decklist_ids: list[str] = []
        for card_row in self.bq_client.query(
                f"SELECT id FROM `{self.decklist_table.full_table_id.replace(':', '.')}`").result():
            decklist_ids.append(dict(card_row)["id"])
        return decklist_ids

    def get_bq_tournament_ids(self) -> list[str]:
        """Returns list of tournament ids stored in bq"""
        tournament_ids: list[str] = []
        for card_row in self.bq_client.query(
                f"SELECT id FROM `{self.tournament_table.full_table_id.replace(':', '.')}` where source = '{DataSource.OP_TOP_DECKS}'").result():
            tournament_ids.append(dict(card_row)["id"])
        return tournament_ids

    def get_bq_tournament_standing_ids(self) -> list[str]:
        """Returns list of tournament_standing ids stored in bq"""
        tournament_standing_ids: list[str] = []
        for card_row in self.bq_client.query(
                f"""SELECT t1.* FROM `{self.tournament_standing_table.full_table_id.replace(':', '.')}` as t1
                LEFT JOIN `{self.tournament_table.full_table_id.replace(':', '.')}` as t2 on t1.tournament_id = t2.id
                where t2.source = '{DataSource.OP_TOP_DECKS}'""").result():
            tournament_standing_ids.append(self.tournament_standing_to_id(TournamentStanding(**dict(card_row))))
        return tournament_standing_ids

    def op_top_deck_decklist_to_id(self, d: OpTopDeckDecklistExtended | OpTopDeckDecklist) -> str:
        return f"{d.tournament_id}_{d.decklist_id}_{d.author}"

    def tournament_standing_to_id(self, ts: TournamentStanding) -> str:
        return f"{ts.tournament_id}_{ts.decklist_id}_{ts.player_id}"

    async def start(self):
        logging.info("OPTopDeckDecklistSpider: initializing BQ client")
        self.bq_client = bigquery.Client(location="europe-west1")
        self.decklist_table = get_or_create_table(Decklist, client=self.bq_client)
        self.op_top_deck_table = get_or_create_table(OpTopDeckDecklist, client=self.bq_client)
        self.tournament_table = get_or_create_table(Tournament, client=self.bq_client)
        self.tournament_standing_table = get_or_create_table(TournamentStanding, client=self.bq_client)

        if self.delete_existing:
            self.delete_bq_tournament_standings()

        self.tournament_ids_crawled = self.get_bq_tournament_ids()
        self.tournament_standing_ids_crawled = self.get_bq_tournament_standing_ids()
        self.decklist_ids_crawled = self.get_bq_decklist_ids()
        self.bq_decklists = self.get_bq_op_top_deck_decklists()
        self.decklists_crawled = [self.op_top_deck_decklist_to_id(d) for d in self.bq_decklists]
        self.bq_add_data_stats = {
            self.decklist_table.table_id: 0,
            self.op_top_deck_table.table_id: 0,
            self.tournament_table.table_id: 0,
            self.tournament_standing_table.table_id: 0
        }

        start_url = "https://onepiecetopdecks.com/deck-list/"
        logging.info(f"OPTopDeckDecklistSpider: starting crawl with meta_formats={self.meta_formats}")

        # Route through a residential proxy to bypass Sucuri WAF IP-reputation blocking.
        # GCP data-center IPs receive a JS-challenge 202 that cannot be solved without a browser.
        # A residential/non-flagged proxy IP passes through unchallenged.
        # Configure via SCRAPER_PROXY env var (e.g. "http://host:port").
        self.proxy_url = os.environ.get("SCRAPER_PROXY")
        #self.proxy_url = self.proxy_url.replace("p.webshare.io:80", "38.154.203.95:5863")
        logging.info(f"OPTopDeckDecklistSpider: starting crawl, proxy={self.proxy_url}")

        yield scrapy.Request(
            url=start_url,
            callback=self.parse_decklist_landingpage,
            meta={'proxy': self.proxy_url},
        )

    @staticmethod
    def is_meta_in_url(meta_format: MetaFormat, url: str, region: MetaFormatRegion | None = None) -> bool:
        matches = []
        for mf in [meta_format, meta_format2side_meta_format(meta_format, region=region)]:
            if mf is None:
                continue
            # Extract the prefix and number using slicing
            prefix = mf[:2]  # Assuming 'OP'
            number = mf[2:]  # Assuming the number part

            # Generate variations
            variations = [
                f"{prefix.upper()}{number}",  # OP08
                f"{prefix.lower()}{number}",  # op08
                f"{prefix.upper()}-{number}",  # OP-08
                f"{prefix.lower()}-{number}",  # op-08
                f"{prefix.upper()} {number}",  # OP 08
                f"{prefix.lower()} {number}",  # op 08
            ]
            matches.append(any(variation in url for variation in variations))

        return any(matches)

    def parse_decklist_landingpage(self, response):
        """Extracts all meta format and country meta format urls for further steps"""
        self.logger.info(
            f"parse_decklist_landingpage: status={response.status} "
            f"body_length={len(response.body)} "
            f"body_preview={response.text[:500]!r}"
        )
        # extract all urls
        urls = response.xpath('//a/@href').getall()
        # drop urls
        urls_to_crawl: dict[MetaFormatRegion, list[tuple[MetaFormat, str]]] = {cmf: [] for cmf in
                                                                               MetaFormatRegion.to_list()}
        self.logger.info(f"Parsed decklist landingpage with {len(urls_to_crawl)} urls to crawl")

        for url in urls:
            if "deck-list" not in url:
                continue
            matching_meta_format = None
            region = None
            if any(w in url.lower() for w in ["japan", "jp-"]):
                region = MetaFormatRegion.ASIA
            elif any(w in url.lower() for w in ["english", "en-"]):
                region = MetaFormatRegion.WEST
            for meta in self.meta_formats:
                if self.is_meta_in_url(meta, url, region):
                    matching_meta_format = meta
                    self.logger.info("url %s matched to meta format %s and region %s", url, meta, region)
                    # stop at first meta format found
                    break
            if matching_meta_format is None:
                self.logger.info("url %s does not match any meta format", url)
                continue

            if region is None:
                self.logger.error(f"url {url} could not be matched to any of {MetaFormatRegion.to_list()}")
            else:
                urls_to_crawl[region].append((matching_meta_format, url))

        for meta_format_region, meta_format_and_urls in urls_to_crawl.items():
            for meta_format, url in meta_format_and_urls:
                yield scrapy.Request(url=url,
                                     callback=self.parse_decklist_meta_page,
                                     errback=self.errback_httpbin,
                                     meta={
                                         'meta_format_region': meta_format_region,
                                         'meta_format': meta_format,
                                         'proxy': self.proxy_url,
                                     })

    def parse_decklist_meta_page(self, response):
        meta_format = response.meta["meta_format"]
        meta_format_region = response.meta["meta_format_region"]
        table_html = response.xpath("//table").get()
        table_url = response.request.url

        yield self.parse_html_table(table_html, table_url, meta_format, meta_format_region)

    def parse_html_table(self, table_html: str, table_url: str, meta_format: MetaFormat,
                         meta_format_region: MetaFormatRegion) -> OpTopDecksItem:
        soup = BeautifulSoup(table_html, 'html.parser')
        header_cells = soup.select('thead th')

        def _index_of_header_name(header_name: str, default: int = 0) -> int:
            for i, header_cell in enumerate(header_cells):
                if header_name.lower() in header_cell.text.lower():
                    return i
            return default

        rows = soup.select('tbody tr')

        decklists: list[Decklist] = []
        op_top_deck_decklists: list[OpTopDeckDecklist] = []
        tournaments: list[Tournament] = []
        tournament_standings: list[TournamentStanding] = []

        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 11:
                continue  # Skip rows that do not have enough cells

            decklist_data = self.parse_decklist_data(cells[_index_of_header_name("deck composition", 0)])
            decklist_id = create_decklist_id(decklist_data)
            leader_id = next(iter(decklist_data))
            source_link = table_url + cells[_index_of_header_name("details", 1)].find('a')['href']
            tournament_datetime = self.parse_tournament_datetime(cells[_index_of_header_name("date", 5)])
            country = cells[_index_of_header_name("country", 6)].text.strip()
            author = cells[_index_of_header_name("author", 7)].text.strip()
            placing_text = cells[_index_of_header_name("placement", 8)].text.strip()
            placing = self.parse_placing_text(placing_text)
            tournament = cells[_index_of_header_name("tournament", 9)].text.strip()
            record = None
            # remove record from tournament
            if '(' in tournament and ')' in tournament:
                record = self.parse_record_from_tournament_text(tournament)
                tournament = tournament.split("(")[0]
            host = cells[_index_of_header_name("host", 10)].text.strip()
            num_players = None
            if '(' in host:
                with suppress(ValueError):
                    num_players = int(host.split('(')[-1].split(')')[0].strip("+"))
                host = host.split("(")[0]

            tournament_name = f"{host} {tournament}"
            tournament_id = f"{host.replace(' ', '_')}_{tournament.replace(' ', '_')}_{country}_{tournament_datetime.date()}"

            tournaments.append(Tournament(
                id=tournament_id,
                name=tournament_name,
                num_players=num_players,
                decklists=True,
                is_public=None,
                is_online=None,
                phases=[],
                meta_format=meta_format,
                meta_format_region=meta_format_region,
                official=True,
                source=DataSource.OP_TOP_DECKS,
                tournament_timestamp=tournament_datetime
            ))

            tournament_standings.append(
                TournamentStanding(
                    tournament_id=tournament_id,
                    player_id=author,
                    decklist_id=decklist_id,
                    name=author,
                    country=None,
                    placing=placing,
                    record=record,
                    leader_id=leader_id,
                    decklist=None,
                    drop=None
                ))

            decklists.append(Decklist(
                id=decklist_id,
                leader_id=leader_id,
                decklist=decklist_data,
            ))

            op_top_deck_decklists.append(OpTopDeckDecklist(
                _dataset_id='MATCHES',
                decklist_id=decklist_id,
                tournament_id=tournament_id,
                author=author,
                host=host,
                placing_text=placing_text,
                decklist_source=source_link,
                country=country
            ))

        return OpTopDecksItem(
            decklists=decklists,
            op_top_deck_decklists=op_top_deck_decklists,
            tournaments=tournaments,
            tournament_standings=tournament_standings
        )

    def parse_decklist_data(self, table_cell: bs4.element.Tag) -> dict[str, int]:
        decklist_data = {}
        pattern = r'(\d)(n.*)'
        for card in table_cell.text.strip().split('a'):
            raw_card_count_and_id = card.strip()
            match = re.match(pattern, raw_card_count_and_id)
            if match:
                number_of_cards = match.group(1)  # First digit before 'n'
                card_id_value = match.group(2)  # Everything after the first 'n' incl. n
                decklist_data[card_id_value[1:]] = int(number_of_cards)
        return decklist_data

    def parse_tournament_datetime(self, cell: bs4.element.Tag) -> datetime:
        # Use dateutil.parser to parse the date string
        parsed_date = parser.parse(cell.text.strip())
        return parsed_date + timedelta(minutes=1)

    def parse_placing_text(self, placing_text) -> int | None:
        """
        Transforms placing text into an integer placing number.

        Parameters:
        placing_text (str): The placing text to be parsed.

        Returns:
        int or None: The integer placing number or None if not valid.
        """
        placing_text = placing_text.strip().lower()  # Normalize the input

        parts = placing_text.split()
        if not parts:
            return None

        first_part = parts[0]

        # Ordinal format: "1st Place", "1st (8-0)", "2nd Place", etc.
        # Require at least one more token after the ordinal so bare "1st" returns None.
        if first_part[:-2].isdigit() and len(parts) > 1:
            return int(first_part[:-2])

        # Short top format: "T4", "T4 (4-1)", "T8", etc.
        if first_part.startswith('t') and first_part[1:].isdigit():
            return int(first_part[1:])

        # Long top format: "Top-8", "Top-16", etc.
        if 'top' in placing_text:
            top_parts = placing_text.split('-')
            if len(top_parts) > 1 and top_parts[1].isdigit():
                return int(top_parts[1])

        return None  # Return None if no valid placing found

    def parse_record_from_tournament_text(self, tournament: str) -> TournamentRecord | None:
        if '(' in tournament and ')' in tournament:
            try:
                record_info = tournament.split('(')[-1].split(')')[0].split('-')
                ties = 0
                if len(record_info) == 2:
                    wins, losses = map(int, record_info)
                elif len(record_info) == 3:
                    wins, ties, losses = map(int, record_info)
                else:
                    return None
                return TournamentRecord(wins=wins, losses=losses, ties=ties)
            except Exception as e:
                self.logger.error(str(e))
                return None
        else:
            return None

    def errback_httpbin(self, failure):
        url = failure.value.response.url if hasattr(failure.value, 'response') else str(failure.value)
        self.logger.error(f"errback called for {url}: {repr(failure)}")

    def closed(self, reason):
        logging.info(f"Finished spider with {self.bq_add_data_stats} new data in Big Query")
