import os
from datetime import datetime, date
from enum import IntEnum
from types import UnionType, GenericAlias
from typing import Any

from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from pydantic import BaseModel

from op_tcg.backend.models.base import SQLTableBaseModel
from op_tcg.backend.models.bq_enums import BQFieldMode, BQFieldType


def get_or_create_bq_dataset(dataset_id, client: bigquery.Client | None = None, location='europe-west3',
                             project_id: str | None = None) -> bigquery.Dataset:
    """
    Get a BigQuery dataset, creating it if it does not exist.

    :param dataset_id: str - The BigQuery dataset ID.
    :param client: str - The bigquery client containing project as well.
    :param location: str - The location for the dataset (default is 'US').
    :param project_id: str - The GCP project ID (default is taken from environment).
    :return: google.cloud.bigquery.dataset.Dataset - The BigQuery dataset reference.
    """
    project_id = project_id if project_id else os.environ.get("GOOGLE_CLOUD_PROJECT")
    client = client if client else bigquery.Client(project=project_id)
    dataset_ref = bigquery.DatasetReference(client.project, dataset_id)
    dataset = bigquery.Dataset(dataset_ref)

    try:
        # Try to get the dataset (will raise NotFound if it does not exist)
        dataset = client.get_dataset(dataset_id)
        print(f"Dataset {dataset_id} already exists.")
    except NotFound:
        # If the dataset does not exist, create it
        dataset.location = location
        dataset = client.create_dataset(dataset, timeout=30)
        print(f"Dataset {dataset_id} created.")

    return dataset

# Function to convert Pydantic model to BigQuery schema
def pydantic_model_to_bq_schema(model: type[BaseModel]) -> list[bigquery.SchemaField]:
    schemata = []
    for field_name, field_info in model.__fields__.items():
        field_type = field_info.annotation
        is_list = False
        if isinstance(field_type, UnionType):
            # Assume first type of union typing is the necessary one for BQ
            field_type = field_type.__args__[0]

        if isinstance(field_type, GenericAlias):
            # Assumption: Every field_type which is a GenericAlias, is a list
            is_list = True
            field_type = field_type.__args__[0]

        # get field type
        bq_type = BQFieldType.STRING  # Default BigQuery type
        if issubclass(field_type, bool):
            bq_type = BQFieldType.BOOL
        elif issubclass(field_type, int):
            bq_type = BQFieldType.INT64
        elif issubclass(field_type, float):
            bq_type = BQFieldType.FLOAT64
        elif issubclass(field_type, datetime):
            bq_type = BQFieldType.TIMESTAMP
        elif issubclass(field_type, date):
            bq_type = BQFieldType.DATE
        elif issubclass(field_type, IntEnum):
            bq_type = BQFieldType.INT64
        # get mode
        mode = BQFieldMode.NULLABLE # Default BigQuery mode
        if is_list:
            mode = BQFieldMode.REPEATED
        elif field_info.is_required():
            mode = BQFieldMode.REQUIRED
        # Add more type conversions as needed
        schemata.append(bigquery.SchemaField(field_name, bq_type, description=field_info.description, mode=mode))
    return schemata

# Function to get or create a BigQuery table
def get_or_create_table(model: type[SQLTableBaseModel], dataset_id: str, table_id: str | None = None, client: bigquery.Client | None = None, location: str = 'europe-west3', project_id: str | None = None) -> bigquery.Table:
    """
    Get a BigQuery table, creating it if it does not exist. Create dataset as well if it does not exist.

    :param dataset_id: str - The BigQuery dataset ID.
    :param model: type[BaseModel] - A pydantic class defining the bigquery schema
    :param table_id: str - The BigQuery table ID. If not provided its extracted from model
    :param client: str - The bigquery client containing project as well.
    :param location: str - The location for the dataset (default is 'europe-west3').
    :param project_id: str - The GCP project ID (default is taken from environment).
    :return: google.cloud.bigquery.dataset.Dataset - The BigQuery dataset reference.
    """
    project_id = project_id if project_id else os.environ.get("GOOGLE_CLOUD_PROJECT")
    client = client if client else bigquery.Client(project=project_id)
    dataset = get_or_create_bq_dataset(dataset_id, client=client, location=location)
    # TODO: check if we can extract the table ref from this object
    table_id = table_id if table_id else model.__tablename__
    table_ref = dataset.table(table_id)

    try:
        # Try to get the table (will raise NotFound if it does not exist)
        table = client.get_table(table_ref)
        print(f"Table {table_id} already exists.")
    except NotFound:
        # If the table does not exist, create it
        schema = pydantic_model_to_bq_schema(model)
        table = bigquery.Table(table_ref, schema=schema)
        table = client.create_table(table)
        print(f"Table {table_id} created.")

    return table

def bq_add_rows(rows_to_insert: list[dict[str, Any]], table: bigquery.Table, client: bigquery.Client | None = None) -> None:
    """Adds a new row to BigQuery"""
    client = client if client else bigquery.Client()

    # ensure json serializability
    for row in rows_to_insert:
        for col_name, col_value in row.items():
            if type(col_value) in [date, datetime]:
                row[col_name] = str(col_value)
            if type(col_value) in [list]:
                for i, col_value_i in enumerate(col_value):
                    if type(col_value_i) == dict:
                        row[col_name][i] = str(col_value_i)
    table_id = f"{table.project}.{table.dataset_id}.{table.table_id}"

    errors = client.insert_rows_json(table_id, rows_to_insert)  # Make an API request.
    if errors == []:
        print("New rows have been added.")
    else:
        raise ValueError("Encountered errors while inserting rows: {}".format(errors))


