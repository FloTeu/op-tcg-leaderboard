import json
from abc import ABC
from datetime import datetime

from google.cloud import bigquery
from pydantic import BaseModel, Field


from op_tcg.backend.etl.load import bq_insert_rows, get_or_create_table, bq_upsert_row
from op_tcg.backend.models.base import SQLTableBaseModel
from op_tcg.backend.utils.annotations import create_pandera_schema_from_pydantic


class UpdateTimestampMixin(BaseModel):
    """Opt-in `update_timestamp` column for upserted BQ tables.

    Rows are built fresh on every write, so the default is the write time; bq_upsert_rows
    overwrites every non-PK column except create_timestamp on MERGE, which makes this the
    time the row was last written while create_timestamp keeps the first insert time.

    Not part of BQTableBaseModel on purpose: existing tables don't get new columns
    automatically, so adding it there would break writes to every table until altered.
    """
    update_timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of the last upsert of this row in BQ")


class BQTableBaseModel(SQLTableBaseModel, ABC):
    _dataset_id: str
    create_timestamp: datetime = Field(default_factory=datetime.now, description="Creation timestamp when the insert in BQ happened")


    @classmethod
    def str2dict(cls, value: str) -> dict:
        try:
            # Attempt to parse the string as a dictionary
            field_dict = eval(value)
            if not isinstance(field_dict, dict):
                raise ValueError("Parsed value is not a dictionary")
            # Optionally, you can add more checks here to ensure the keys and values are correct
            return field_dict
        except Exception as e:
            raise ValueError(f"Invalid decklist string: {e}")

    @classmethod
    def paSchema(cls):
        return create_pandera_schema_from_pydantic(cls)

    @classmethod
    def get_dataset_id(cls):
        return cls._dataset_id.default

    def insert_to_bq(self, client: bigquery.Client | None = None):
        """Adds a new row to BQ"""
        # ensure json serialization without enum objects
        bq_insert_rows([json.loads(self.model_dump_json())],
                       table=get_or_create_table(type(self), client=client), client=client)


    def upsert_to_bq(self, client: bigquery.Client | None = None):
        """Adds a new row to BQ"""
        # ensure json serialization without enum objects
        bq_upsert_row(self, client=client)
