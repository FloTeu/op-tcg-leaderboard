import os
import time
import logging
import sys

import pandas as pd

from op_tcg.backend.elo import EloCreator
from op_tcg.backend.etl.base import AbstractETLJob, E, T
from op_tcg.backend.etl.load import get_or_create_table
from op_tcg.backend.etl.transform import BQMatchCreator
from op_tcg.backend.models.bq import BQDataset
from op_tcg.backend.models.input import AllLeaderMetaDocs, MetaFormat, LimitlessLeaderMetaDoc
from op_tcg.backend.models.matches import BQMatches, Match, BQLeaderElos, LeaderElo
from op_tcg.backend.etl.extract import read_json_files
from pathlib import Path
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
_logger = logging.getLogger("etl_classes")

class LocalMatchesToBigQueryEtlJob(AbstractETLJob[AllLeaderMetaDocs, BQMatches]):
    def __init__(self, data_dir: Path, meta_formats: list[MetaFormat] | None = None, official: bool=True):
        self.data_dir = data_dir
        self.meta_formats = meta_formats
        self.bq_client = bigquery.Client()
        self.official = official

    def validate(self, extracted_data: AllLeaderMetaDocs) -> bool:
        return True

    def extract(self) -> AllLeaderMetaDocs:
        all_matches: AllLeaderMetaDocs = read_json_files(self.data_dir)
        # include only the relevant meta formats
        if self.meta_formats:
            filtered_docs: list[LimitlessLeaderMetaDoc] = []
            for doc in all_matches.documents:
                if doc.meta_format in self.meta_formats:
                    filtered_docs.append(doc)
            all_matches.documents = filtered_docs
        meta_formats_in_data = list(set([doc.meta_format for doc in all_matches.documents]))
        assert all(require_meta_format in meta_formats_in_data for require_meta_format in self.meta_formats), "Not all required meta formats exist in the source data"
        return all_matches

    def transform(self, all_local_matches: AllLeaderMetaDocs) -> BQMatches:
        bq_match_creator = BQMatchCreator(all_local_matches, official=self.official)
        return bq_match_creator.transform2BQMatches()

    def load(self, transformed_data: BQMatches) -> None:
        table = get_or_create_table(model=Match, dataset_id=BQDataset.MATCHES, client=self.bq_client)
        df = transformed_data.to_dataframe()
        official_condition = "NOT official" if self.official else "official"
        if len(df) > 0:
            # delete existing official data in selected meta by only keeping other meta formats
            self.bq_client.query(f"""
            CREATE OR REPLACE TABLE {table.dataset_id}.{table.table_id} AS
            SELECT *
            FROM {table.dataset_id}.{table.table_id}
            WHERE (meta_format not in ('{"','".join(self.meta_formats)}')) OR {official_condition};
            """)
        # upload data of meta_formats to BQ
        self.bq_client.load_table_from_dataframe(df, table)
        _logger.info(f"Loading to BQ table {table.dataset_id}.{table.table_id} succeeded")


class EloUpdateToBigQueryEtlJob(AbstractETLJob[BQMatches, BQLeaderElos]):
    def __init__(self, meta_formats: list[MetaFormat], matches_csv_file_path: Path | str | None = None):
        self.bq_client = bigquery.Client()
        self.meta_formats = meta_formats
        self.in_meta_format = "('" + "','".join(self.meta_formats) + "')"
        self.matches_csv_file_path = matches_csv_file_path

    def validate(self, extracted_data: AllLeaderMetaDocs) -> bool:
        return True

    def extract(self) -> BQMatches:
        if self.matches_csv_file_path:
            df = pd.read_csv(self.matches_csv_file_path)
        else:
            query = f"SELECT * FROM {BQDataset.MATCHES}.{Match.__tablename__} WHERE meta_format in {self.in_meta_format}"
            df = self.bq_client.query_and_wait(query).to_dataframe()
            _logger.info(f"Extracted data from bq {BQDataset.MATCHES}.{Match.__tablename__}")
        matches: list[Match] = []
        for i, df_row in df.iterrows():
            matches.append(Match(**df_row.to_dict()))
        return BQMatches(matches=matches)


    def transform(self, all_matches: BQMatches) -> BQLeaderElos:
        df_all_matches = all_matches.to_dataframe()
        elo_ratings: list[LeaderElo] = []
        def calculate_all_elo_ratings(df_matches):
            meta_format = df_matches.meta_format.unique().tolist()
            for only_official in [True, False]:
                _logger.info(f"Calculate Elo for meta {meta_format} and only_official {only_official}")
                if only_official:
                    elo_creator = EloCreator(df_matches.query("official"), only_official=True)
                else:
                    elo_creator = EloCreator(df_matches, only_official=False)
                elo_creator.calculate_elo_ratings()
                elo_ratings.extend(elo_creator.to_bq_leader_elos().elo_ratings)
        df_all_matches.groupby("meta_format").apply(calculate_all_elo_ratings)

        return BQLeaderElos(elo_ratings=elo_ratings)

    def load(self, transformed_data: BQLeaderElos) -> None:
        table_tmp = get_or_create_table(model=LeaderElo, table_id=f"{LeaderElo.__tablename__}_tmp", dataset_id="matches", client=self.bq_client)
        table = get_or_create_table(model=LeaderElo, table_id=LeaderElo.__tablename__, dataset_id="matches", client=self.bq_client)
        df = transformed_data.to_dataframe()
        if len(df) > 0:
            # create tmp table with new data
            self.bq_client.load_table_from_dataframe(df, table_tmp)
            # Insert all uneffected elo from other meta formats
            query_job = self.bq_client.query(f"""
            INSERT INTO {table_tmp.dataset_id}.{table_tmp.table_id}
            SELECT *
            FROM {table.dataset_id}.{table.table_id}
            WHERE meta_format not in {self.in_meta_format};
            """)
            _logger.info(f"Tmp BQ table created {table_tmp.dataset_id}.{table_tmp.table_id}")
            assert query_job.errors is None

            # wait some seconds to be sure data is ready in tmp table
            time.sleep(5)
            # Overwrite existing data with tmp table
            self.bq_client.query(f"""
            CREATE OR REPLACE TABLE {table.dataset_id}.{table.table_id} AS
            SELECT *
            FROM {table_tmp.dataset_id}.{table_tmp.table_id}
            """)
            # delete tmp table
            self.bq_client.delete_table(table_tmp)
            _logger.info(f"Loading to BQ table {table.dataset_id}.{table.table_id} succeeded")

