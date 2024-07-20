import json
import logging
import sys
import tempfile

import pandas as pd
import requests

from op_tcg.backend.elo import EloCreator
from op_tcg.backend.etl.base import AbstractETLJob, E, T
from op_tcg.backend.etl.load import get_or_create_table, bq_insert_rows, upload2gcp_storage
from op_tcg.backend.etl.transform import BQMatchCreator
from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.backend.models.input import AllLeaderMetaDocs, MetaFormat, LimitlessLeaderMetaDoc
from op_tcg.backend.models.matches import BQMatches, Match
from op_tcg.backend.models.leader import LeaderElo
from op_tcg.backend.models.cards import Card
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


class EloUpdateToBigQueryEtlJob(AbstractETLJob[BQMatches, list[LeaderElo]]):
    def __init__(self, meta_formats: list[MetaFormat], matches_csv_file_path: Path | str | None = None):
        self.bq_client = bigquery.Client(location="europe-west3")
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
            _logger.info(f"Query BQ with '{query}'")
            df = self.bq_client.query_and_wait(query).to_dataframe()
            _logger.info(f"Extracted {len(df)} rows from bq {BQDataset.MATCHES}.{Match.__tablename__}")
        matches: list[Match] = []
        for i, df_row in df.iterrows():
            matches.append(Match(**df_row.to_dict()))
        return BQMatches(matches=matches)


    def transform(self, all_matches: BQMatches) -> list[LeaderElo]:
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
                elo_ratings.extend(elo_creator.to_bq_leader_elos())
        if len(df_all_matches) > 0:
            df_all_matches.groupby("meta_format").apply(calculate_all_elo_ratings)
        return elo_ratings

    def load(self, transformed_data: list[LeaderElo]) -> None:
        # ensure bq table exists
        table = get_or_create_table(LeaderElo)
        leader_ids_to_update = list(set([d.leader_id for d in transformed_data]))
        in_leader_ids_to_update = "('" + "','".join(leader_ids_to_update) + "')"

        # delete all rows of meta
        self.bq_client.query(
            f"DELETE FROM `{table.full_table_id.split(':')[1]}` WHERE meta_format in {self.in_meta_format} and leader_id in {in_leader_ids_to_update};").result()
        # insert all new rows
        rows_to_insert = [json.loads(bq_leader_elo.model_dump_json()) for bq_leader_elo in transformed_data]
        bq_insert_rows(rows_to_insert, table=table, client=self.bq_client)
        _logger.info(f"Loading {len(transformed_data)} rows with meta {self.meta_formats} succeeded")


class CardImageUpdateToGCPEtlJob(AbstractETLJob[list[Card], list[Card]]):
    def __init__(self, meta_formats: list[MetaFormat] | None = None):
        self.bq_client = bigquery.Client(location="europe-west3")
        self.bucket = f"{self.bq_client.project}-public"
        self.meta_formats = meta_formats or []
        self.in_meta_format_where_statement = "release_meta in ('" + "','".join(self.meta_formats) + "')"

    def validate(self, extracted_data: AllLeaderMetaDocs) -> bool:
        return True

    def extract(self) -> list[Card]:
        query = f'SELECT * FROM {BQDataset.CARDS}.{Card.__tablename__} WHERE image_url NOT LIKE "%googleapis%" '
        if self.meta_formats:
            query += f"and {self.in_meta_format_where_statement}"
        _logger.info(f"Query BQ with '{query}'")
        df = self.bq_client.query_and_wait(query).to_dataframe()
        _logger.info(f"Extracted {len(df)} rows from bq {BQDataset.CARDS}.{Card.__tablename__}")
        cards: list[Card] = []
        for i, df_row in df.iterrows():
            cards.append(Card(**df_row.to_dict()))
        return cards


    def transform(self, cards: list[Card]) -> list[Card]:
        for card in cards:
            with tempfile.NamedTemporaryFile() as tmp:
                img_data = requests.get(card.image_url).content
                tmp.write(img_data)
                file_type = card.image_url.split('.')[-1]
                image_url_path = f"card/images/{card.language.upper()}/{card.aa_version}/{card.id}.{file_type}"
                upload2gcp_storage(path_to_file=tmp.name,
                                   blob_name=image_url_path,
                                   content_type=f"image/{file_type}")
                card.image_url = f"https://storage.googleapis.com/{self.bucket}/{image_url_path}"
        return cards

    def load(self, cards: list[Card]) -> None:
        # ensure bq table exists
        for card in cards:
            card.upsert_to_bq()