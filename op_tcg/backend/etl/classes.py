from typing import List
from op_tcg.backend.etl.base import AbstractETLJob, E, T
from op_tcg.backend.etl.transform import limitless_matches2bq_matches
from op_tcg.backend.models.input import AllMetaLeaderMatches
from op_tcg.backend.models.matches import BQMatches, BQMatch
from op_tcg.backend.etl.extract import read_json_files
from pathlib import Path
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()


class LocalMatchesToBigQueryEtlJob(AbstractETLJob[AllMetaLeaderMatches, BQMatches]):
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.bq_client = bigquery.Client()

    def validate(self, extracted_data: AllMetaLeaderMatches) -> bool:
        return True

    def extract(self) -> AllMetaLeaderMatches:
        return read_json_files(self.data_dir)

    def transform(self, all_local_matches: AllMetaLeaderMatches) -> BQMatches:
        bq_matches: list[BQMatch] = []
        for match_doc in all_local_matches.documents:
            meta_leader_bq_matches: list[BQMatch] = limitless_matches2bq_matches(match_doc)
            bq_matches.extend(meta_leader_bq_matches)
        return BQMatches(matches=bq_matches)

    def load(self, transformed_data: BQMatches) -> None:
        dataset = self.bq_client.get_dataset("matches")
        table_ref = dataset.table("matches")
        df = transformed_data.to_dataframe()
        self.bq_client.load_table_from_dataframe(df, table_ref)