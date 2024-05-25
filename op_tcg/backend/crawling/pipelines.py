import op_tcg
import json
from pathlib import Path

from op_tcg.backend.etl.load import bq_insert_rows, get_or_create_table
from op_tcg.backend.models.input import LimitlessLeaderMetaDoc
from op_tcg.backend.models.bq_classes import BQTableBaseModel
from op_tcg.backend.crawling.items import TournamentItem
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