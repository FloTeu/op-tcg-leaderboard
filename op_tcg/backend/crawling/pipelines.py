import logging
from typing import Any

from google.cloud import bigquery

import op_tcg
import json
from pathlib import Path

from op_tcg.backend.etl.extract import crawl_limitless_card
from op_tcg.backend.etl.load import bq_insert_rows
from op_tcg.backend.models.cards import LimitlessCardData, CardPrice, CardCurrency, CardReleaseSet
from op_tcg.backend.models.decklists import Decklist
from op_tcg.backend.models.input import LimitlessLeaderMetaDoc
from op_tcg.backend.models.bq_classes import BQTableBaseModel
from op_tcg.backend.crawling.items import TournamentItem, LimitlessPriceRow, ReleaseSetItem, CardsItem, OpTopDecksItem
from op_tcg.backend.models.matches import Match
from op_tcg.backend.models.tournaments import Tournament, TournamentStanding


class MatchesPipeline:
    def process_item(self, item: LimitlessLeaderMetaDoc, spider):
        target_dir = Path(op_tcg.__file__).parent.parent / "data" / "limitless"
        target_dir.mkdir(exist_ok=True, parents=True)
        with open(target_dir / f"{item.leader_id}_{item.meta_format}.json", "w") as fp:
            json.dump(item.model_dump(), fp)
        return item


class TournamentPipeline:

    def get_bq_table(self, bq_table_item: BQTableBaseModel, spider):
        if isinstance(bq_table_item, Match):
            return spider.match_table
        elif isinstance(bq_table_item, Tournament):
            return spider.tournament_table
        elif isinstance(bq_table_item, TournamentStanding):
            return spider.tournament_standing_table
        elif isinstance(bq_table_item, Decklist):
            return spider.decklist_table
        else:
            raise NotImplementedError

    def process_item(self, item: TournamentItem, spider):
        """
        Updates all tournament related data (if exists it will be deleted first)
        """
        if isinstance(item, TournamentItem):
            for bq_row_list in [item.matches, item.tournament_standings]:
                if bq_row_list:
                    bq_table = self.get_bq_table(bq_row_list[0], spider)
                    # delete all rows of tournament
                    spider.bq_client.query(f"DELETE FROM `{bq_table.full_table_id.split(':')[1]}` WHERE tournament_id = '{item.tournament.id}';").result()
                    # insert all new rows
                    rows_to_insert = [json.loads(bq_row.model_dump_json()) for bq_row in bq_row_list]
                    bq_insert_rows(rows_to_insert, table=bq_table, client=spider.bq_client)

            bq_table = self.get_bq_table(item.tournament, spider)
            # delete existing tournament
            spider.bq_client.query(f"DELETE FROM `{bq_table.full_table_id.split(':')[1]}` WHERE id = '{item.tournament.id}';").result()
            # insert all new matches
            bq_insert_rows([json.loads(item.tournament.model_dump_json())], table=bq_table, client=spider.bq_client)


            # upload decklists to BQ
            decklists_to_upload = []
            for decklist in item.decklists:
                # ignore duplicate
                if decklist.id not in spider.decklist_ids_crawled:
                    decklists_to_upload.append(decklist)
                    spider.decklist_ids_crawled.append(decklist.id)
            # insert all new rows
            if decklists_to_upload:
                rows_to_insert = [json.loads(bq_row.model_dump_json()) for bq_row in decklists_to_upload]
                bq_insert_rows(rows_to_insert, table=spider.decklist_table, client=spider.bq_client)

        return item

class CardPipeline:

    def process_tournament_item(self, item: TournamentItem, spider):
        decklist_card_ids = []
        for tournament_standing in item.tournament_standings:
            if tournament_standing.decklist:
                decklist_card_ids.extend(list(tournament_standing.decklist.keys()))
        new_unique_card_ids = set(decklist_card_ids) - set(spider.already_crawled_card_ids)
        for card_id in new_unique_card_ids:
            # Crawl data from limitless
            try:
                card_data: LimitlessCardData = crawl_limitless_card(card_id)
            except Exception as e:
                logging.warning("Card data could not be extracted", str(e))
                continue
            # Upload to big query
            bq_insert_rows([json.loads(bq_card.model_dump_json()) for bq_card in card_data.cards],
                           table=spider.card_table, client=spider.bq_client)
            bq_insert_rows([json.loads(bq_card_price.model_dump_json()) for bq_card_price in card_data.card_prices],
                           table=spider.card_price_table, client=spider.bq_client)
            # mark card id as crawled
            spider.already_crawled_card_ids.append(card_id)

    def process_cards_item(self, item: CardsItem, spider):
        rows_to_insert: list[dict[str, Any]] = []
        for card in item.cards:
            rows_to_insert.append(json.loads(card.model_dump_json()))
            if card.id not in spider.card_count:
                spider.card_count[card.id] = {}
            if card.aa_version not in spider.card_count[card.id]:
                spider.card_count[card.id][card.aa_version] = 1
            else:
                spider.card_count[card.id][card.aa_version] += 1

        bq_insert_rows(rows_to_insert,
                       table=spider.card_table, client=spider.bq_client)


    def process_item(self, item: TournamentItem | CardsItem, spider):
        """
        Crawls all card data which is not yet available in big query and gcp
        """
        if isinstance(item, TournamentItem):
            self.process_tournament_item(item, spider)
        if isinstance(item, CardsItem):
            self.process_cards_item(item, spider)

        return item



class CardPricePipeline:

    def process_item(self, item: LimitlessPriceRow, spider):
        """
        Loads card price data to BigQuery
        """
        def get_card_price(item: LimitlessPriceRow, currency: CardCurrency):
            return CardPrice(
                card_id=item.card_id,
                language=item.language,
                aa_version=item.aa_version,
                price=item.price_usd if currency == CardCurrency.US_DOLLAR else item.price_eur,
                currency=currency
            )

        if isinstance(item, LimitlessPriceRow):
            upload_data = []
            if item.price_usd:
                card_price_usd = get_card_price(item, CardCurrency.US_DOLLAR)
                upload_data.append(json.loads(card_price_usd.model_dump_json()))
            if item.price_eur:
                card_price_eur = get_card_price(item, CardCurrency.EURO)
                upload_data.append(json.loads(card_price_eur.model_dump_json()))

            # update price count
            if item.card_id not in spider.price_count:
                spider.price_count[item.card_id] = {}
            if item.aa_version in spider.price_count[item.card_id]:
                logging.warning(f"Price information of {item.card_id} {item.aa_version} was already uploaded")
            else:
                spider.price_count[item.card_id][item.aa_version] = 1
            bq_insert_rows(upload_data, table=spider.price_table, client=spider.bq_client)
        return item

class CardReleaseSetPipeline:

    def process_item(self, item: ReleaseSetItem, spider):
        """
        Loads card release_set data to BigQuery
        """

        if isinstance(item, ReleaseSetItem):
            bq_insert_rows([json.loads(item.release_set.model_dump_json())], table=spider.release_set_table, client=spider.bq_client)
        return item


class OpTopDeckDecklistPipeline:
    def process_item(self, item: OpTopDecksItem, spider):
        """
        Updates all tournament related data (if exists it will be deleted first)
        """
        def _upload_to_bq(data_to_upload: list[BQTableBaseModel],table: bigquery.Table):
            if data_to_upload:
                rows_to_insert = [json.loads(bq_row.model_dump_json()) for bq_row in data_to_upload]
                bq_insert_rows(rows_to_insert, table=table, client=spider.bq_client)

        if isinstance(item, OpTopDecksItem):
            # upload tournaments to BQ
            tournaments_to_upload = []
            for tournament in item.tournaments:
                # ignore duplicate
                if tournament.id not in spider.tournament_ids_crawled:
                    tournaments_to_upload.append(tournament)
                    spider.tournament_ids_crawled.append(tournament.id)
                    spider.bq_add_data_stats[spider.tournament_table.table_id] += 1
            # insert all new rows
            if tournaments_to_upload:
                _upload_to_bq(tournaments_to_upload, spider.tournament_table)

            # upload decklists to BQ
            decklists_to_upload = []
            for decklist in item.decklists:
                # ignore duplicate
                if decklist.id not in spider.decklist_ids_crawled:
                    decklists_to_upload.append(decklist)
                    spider.decklist_ids_crawled.append(decklist.id)
                    spider.bq_add_data_stats[spider.decklist_table.table_id] += 1
            # insert all new rows
            if decklists_to_upload:
                _upload_to_bq(decklists_to_upload, spider.decklist_table)

            # upload tournament_standings to BQ
            tournament_standings_to_upload = []
            for tournament_standing in item.tournament_standings:
                # ignore duplicate
                if spider.tournament_standing_to_id(tournament_standing) not in spider.tournament_standing_ids_crawled:
                    tournament_standings_to_upload.append(tournament_standing)
                    spider.tournament_standing_ids_crawled.append(spider.tournament_standing_to_id(tournament_standing))
                    spider.bq_add_data_stats[spider.tournament_standing_table.table_id] += 1
            # insert all new rows
            if tournament_standings_to_upload:
                _upload_to_bq(tournament_standings_to_upload, spider.tournament_standing_table)

            # upload op_top_deck_decklists to BQ
            op_top_deck_decklists_to_upload = []
            for decklist in item.op_top_deck_decklists:
                id = spider.op_top_deck_decklist_to_id(decklist)
                # ignore already crawled decklists
                if id not in spider.decklists_crawled:
                    op_top_deck_decklists_to_upload.append(decklist)
                    spider.decklists_crawled.append(id)
                    spider.bq_add_data_stats[spider.op_top_deck_table.table_id] += 1
            # insert all new rows
            if op_top_deck_decklists_to_upload:
                _upload_to_bq(op_top_deck_decklists_to_upload, spider.op_top_deck_table)

        return item