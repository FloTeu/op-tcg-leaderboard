import json
import pandera as pa
from abc import ABC, abstractmethod
from datetime import datetime

from google.cloud import bigquery
from pydantic import Field


from op_tcg.backend.etl.load import bq_insert_rows, get_or_create_table, bq_upsert_row
from op_tcg.backend.models.base import SQLTableBaseModel
from op_tcg.backend.utils.annotations import create_pandera_schema_from_pydantic


class BQTableBaseModel(SQLTableBaseModel, ABC):
    class Config:
        underscore_attrs_are_private = True

    _dataset_id: str
    create_timestamp: datetime = Field(default_factory=datetime.now, description="Creation timestamp when the insert in BQ happened")


    @classmethod
    def paSchema(cls):
        return create_pandera_schema_from_pydantic(cls)

    def insert_to_bq(self, client: bigquery.Client | None = None):
        """Adds a new row to BQ"""
        # ensure json serialization without enum objects
        bq_insert_rows([json.loads(self.model_dump_json())],
                       table=get_or_create_table(type(self), client=client), client=client)


    def upsert_to_bq(self, client: bigquery.Client | None = None):
        """Adds a new row to BQ"""
        # ensure json serialization without enum objects
        bq_upsert_row(self, client=client)
