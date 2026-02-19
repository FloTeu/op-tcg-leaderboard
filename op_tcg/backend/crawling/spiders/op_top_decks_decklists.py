import logging
import re
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
    }

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

    def start_requests(self):
        self.bq_client = bigquery.Client(location="europe-west3")
        self.decklist_table = get_or_create_table(Decklist, client=self.bq_client)
        self.op_top_deck_table = get_or_create_table(OpTopDeckDecklist, client=self.bq_client)
        self.tournament_table = get_or_create_table(Tournament, client=self.bq_client)
        self.tournament_standing_table = get_or_create_table(TournamentStanding, client=self.bq_client)

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

        start_url = "https://onepiecetopdecks.com/deck-list"
        yield scrapy.Request(url=start_url,
                             callback=self.parse_decklist_landingpage,
                             errback=self.errback_httpbin)

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
        # extract all urls
        urls = response.xpath('//a/@href').getall()
        # drop urls
        urls_to_crawl: dict[MetaFormatRegion, list[tuple[MetaFormat, str]]] = {cmf: [] for cmf in
                                                                               MetaFormatRegion.to_list()}
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
                    # stop at first meta format found
                    break
            if matching_meta_format is None:
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
                                         # 'dont_redirect': True,
                                         # 'handle_httpstatus_list': [302],
                                         'meta_format_region': meta_format_region,
                                         'meta_format': meta_format,
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

        if 'place' in placing_text:
            # Extract the number from phrases like '1st Place'
            parts = placing_text.split()
            if len(parts) > 0:
                # Check if the first part is a number (with an ordinal suffix)
                first_part = parts[0]
                if first_part[:-2].isdigit():  # Check if the part before 'st', 'nd', 'rd', 'th' is a digit
                    return int(first_part[:-2])  # Return the integer value
        elif 'top' in placing_text:
            # Extract the number from phrases like 'Top-8'
            parts = placing_text.split('-')
            if len(parts) > 1 and parts[1].isdigit():
                return int(parts[1])  # Return the integer value

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
        # log all failures
        self.logger.error(repr(failure))

    def closed(self, reason):
        logging.info(f"Finished spider with {self.bq_add_data_stats} new data in Big Query")
