import logging

import op_tcg
import json
from pathlib import Path

from op_tcg.backend.etl.extract import crawl_limitless_card
from op_tcg.backend.etl.load import bq_insert_rows
from op_tcg.backend.models.cards import LimitlessCardData, CardPrice, CardCurrency
from op_tcg.backend.models.input import LimitlessLeaderMetaDoc
from op_tcg.backend.models.bq_classes import BQTableBaseModel
from op_tcg.backend.crawling.items import TournamentItem, LimitlessPriceRow
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

        return item

class CardPipeline:

    def process_item(self, item: TournamentItem, spider):
        """
        Crawls all card data which is not yet available in big query and gcp
        """
        if isinstance(item, TournamentItem):
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
                bq_insert_rows([json.loads(bq_card.model_dump_json()) for bq_card in card_data.cards], table=spider.card_table, client=spider.bq_client)
                bq_insert_rows([json.loads(bq_card_price.model_dump_json()) for bq_card_price in card_data.card_prices], table=spider.card_price_table, client=spider.bq_client)
                # mark card id as crawled
                spider.already_crawled_card_ids.append(card_id)

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
            card_price_usd = get_card_price(item, CardCurrency.US_DOLLAR)
            card_price_eur = get_card_price(item, CardCurrency.EURO)

            upload_data = [json.loads(card_price_usd.model_dump_json()), json.loads(card_price_eur.model_dump_json())]

            # update price count
            if item.card_id not in spider.price_count:
                spider.price_count[item.card_id] = {}
            if item.aa_version in spider.price_count[item.card_id]:
                logging.warning(f"Price information of {item.card_id} {item.aa_version} was already uploaded")
            else:
                spider.price_count[item.card_id][item.aa_version] = 1
            bq_insert_rows(upload_data, table=spider.price_table, client=spider.bq_client)
        return item