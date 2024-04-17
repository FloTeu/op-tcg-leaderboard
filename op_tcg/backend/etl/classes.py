from typing import List

import pandas as pd

from op_tcg.backend.elo import EloCreator
from op_tcg.backend.etl.base import AbstractETLJob, E, T
from op_tcg.backend.etl.load import get_or_create_table
from op_tcg.backend.etl.transform import limitless_matches2bq_matches
from op_tcg.backend.models.bq import BQTable, BQDataset
from op_tcg.backend.models.input import AllMetaLeaderMatches, MetaFormat, LimitlessLeaderMetaMatches
from op_tcg.backend.models.matches import BQMatches, BQMatch, BQLeaderElos, BQLeaderElo
from op_tcg.backend.etl.extract import read_json_files
from pathlib import Path
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()


class LocalMatchesToBigQueryEtlJob(AbstractETLJob[AllMetaLeaderMatches, BQMatches]):
    def __init__(self, data_dir: Path, meta_formats: list[MetaFormat] | None = None):
        self.data_dir = data_dir
        self.meta_formats = meta_formats
        self.bq_client = bigquery.Client()

    def validate(self, extracted_data: AllMetaLeaderMatches) -> bool:
        return True

    def extract(self) -> AllMetaLeaderMatches:
        all_matches: AllMetaLeaderMatches = read_json_files(self.data_dir)
        # include only the relevant meta formats
        if self.meta_formats:
            filters_docs: list[LimitlessLeaderMetaMatches] = []
            for doc in all_matches.documents:
                if doc.meta_format in self.meta_formats:
                    filters_docs.append(doc)
            all_matches.documents = filters_docs
        meta_formats_in_data = list(set([doc.meta_format for doc in all_matches.documents]))
        assert all(require_meta_format in meta_formats_in_data for require_meta_format in self.meta_formats), "Not all required meta formats exist in the source data"
        return all_matches

    def transform(self, all_local_matches: AllMetaLeaderMatches) -> BQMatches:
        bq_matches: list[BQMatch] = []
        for match_doc in all_local_matches.documents:
            meta_leader_bq_matches: list[BQMatch] = limitless_matches2bq_matches(match_doc)
            bq_matches.extend(meta_leader_bq_matches)
        return BQMatches(matches=bq_matches)

    def load(self, transformed_data: BQMatches) -> None:
        table = get_or_create_table(table_id=BQTable.MATCHES, dataset_id=BQDataset.MATCHES, model=BQMatch, client=self.bq_client)
        df = transformed_data.to_dataframe()
        if len(df) > 0:
            # delete existing data in selected meta
            self.bq_client.query(f"""
            CREATE OR REPLACE TABLE {table.dataset_id}.{table.table_id} AS
            SELECT *
            FROM {table.dataset_id}.{table.table_id}
            WHERE meta_format not in ('{"','".join(self.meta_formats)}');
            """)
        # upload data of meta_formats to BQ
        self.bq_client.load_table_from_dataframe(df, table)



class EloUpdateToBigQueryEtlJob(AbstractETLJob[BQMatches, BQLeaderElos]):
    def __init__(self, matches_csv_file_path: Path | str | None = None):
        self.bq_client = bigquery.Client()
        self.matches_csv_file_path = matches_csv_file_path

    def validate(self, extracted_data: AllMetaLeaderMatches) -> bool:
        return True

    def extract(self) -> BQMatches:
        if self.matches_csv_file_path:
            df = pd.read_csv(self.matches_csv_file_path)
        else:
            query = f"SELECT * FROM {BQDataset.MATCHES}.{BQTable.MATCHES}"
            df = self.bq_client.query_and_wait(query).to_dataframe()
        matches: list[BQMatch] = []
        for i, df_row in df.iterrows():
            matches.append(BQMatch(**df_row.to_dict()))
        return BQMatches(matches=matches)


    def transform(self, all_matches: BQMatches) -> BQLeaderElos:
        # TODO Add more elo values for different metas
        df_all_matches = all_matches.to_dataframe()
        elo_creator = EloCreator(df_all_matches)
        elo_creator.calculate_elo_ratings()
        return elo_creator.to_bq_leader_elos()

    def load(self, transformed_data: BQLeaderElos) -> None:
        table_tmp = get_or_create_table(table_id=f"{BQTable.LEADER_ELO}_tmp", dataset_id="matches", model=BQLeaderElo, client=self.bq_client)
        table = get_or_create_table(table_id=BQTable.LEADER_ELO, dataset_id="matches", model=BQLeaderElo, client=self.bq_client)
        df = transformed_data.to_dataframe()
        if len(df) > 0:
            # create tmp table with new data
            self.bq_client.load_table_from_dataframe(df, table_tmp)
            # Overwrite existing data with tmp table
            self.bq_client.query(f"""
            CREATE OR REPLACE TABLE {table.dataset_id}.{table.table_id} AS
            SELECT *
            FROM {table_tmp.dataset_id}.{table_tmp.table_id}
            """)
            self.bq_client.delete_table(table_tmp)
