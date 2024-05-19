import re
from abc import ABC, abstractmethod

from google.cloud import bigquery
from pydantic import BaseModel, validator

from op_tcg.backend.etl.load import bq_add_rows, get_or_create_table
from op_tcg.backend.models.base import SQLTableBaseModel


class BQTableBaseModel(SQLTableBaseModel, ABC):
    class Config:
        underscore_attrs_are_private = True

    _dataset_id: str

    def insert_to_bq(self, client: bigquery.Client | None = None):
        """Adds a new row to BQ"""
        bq_add_rows([self.model_dump()],
                    table=get_or_create_table(type(self), dataset_id=self._dataset_id, client=client))
