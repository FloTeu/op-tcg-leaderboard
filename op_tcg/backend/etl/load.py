import os
from datetime import datetime, date
from enum import IntEnum
from types import UnionType, GenericAlias

from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from pydantic import BaseModel
from op_tcg.backend.models.bq import BQFieldMode, BQFieldType
from op_tcg.backend.models.leader import BQLeader


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
def get_or_create_table(table_id: str, dataset_id: str, model: type[BaseModel], client: bigquery.Client | None = None, location: str = 'europe-west3', project_id: str | None = None) -> bigquery.Table:
    """
    Get a BigQuery table, creating it if it does not exist. Create dataset as well if it does not exist.

    :param table_id: str - The BigQuery table ID.
    :param dataset_id: str - The BigQuery dataset ID.
    :param model: type[BaseModel] - A pydantic class defining the bigquery schema.
    :param client: str - The bigquery client containing project as well.
    :param location: str - The location for the dataset (default is 'europe-west3').
    :param project_id: str - The GCP project ID (default is taken from environment).
    :return: google.cloud.bigquery.dataset.Dataset - The BigQuery dataset reference.
    """
    project_id = project_id if project_id else os.environ.get("GOOGLE_CLOUD_PROJECT")
    client = client if client else bigquery.Client(project=project_id)
    dataset = get_or_create_bq_dataset(dataset_id, client=client, location=location)
    # TODO: check if we can extract the table ref from this object
    table_ref = dataset.table(table_id)
    schema = pydantic_model_to_bq_schema(model)

    try:
        # Try to get the table (will raise NotFound if it does not exist)
        table = client.get_table(table_ref)
        print(f"Table {table_id} already exists.")
    except NotFound:
        # If the table does not exist, create it
        table = bigquery.Table(table_ref, schema=schema)
        table = client.create_table(table)
        print(f"Table {table_id} created.")

    return table




def update_bq_leader_row(bq_leader: BQLeader, table: bigquery.Table, client: bigquery.Client | None = None):
    client = client if client else bigquery.Client()

    table_id = f"{table.project}.{table.dataset_id}.{table.table_id}"  # Replace with your actual project, dataset, and table name

    # Use MERGE to update if the row exists, or insert if it does not
    merge_query = f"""
    MERGE {table_id} T
    USING (SELECT 1) S
    ON T.id = @id
    WHEN MATCHED THEN
        UPDATE SET
            name = @name,
            life = @life,
            power = @power,
            release_meta = @release_meta,
            avatar_icon_url = @avatar_icon_url,
            image_url = @image_url,
            image_aa_url = @image_aa_url,
            colors = @colors,
            attribute = @attribute,
            ability = @ability,
            fractions = @fractions,
            language = @language
    WHEN NOT MATCHED THEN
        INSERT (id, name, life, power, release_meta, avatar_icon_url, image_url, image_aa_url, colors, attribute, ability, fractions, language)
        VALUES (@id, @name, @life, @power, @release_meta, @avatar_icon_url, @image_url, @image_aa_url, @colors, @attribute, @ability, @fractions, @language)
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("id", "STRING", bq_leader.id),
            bigquery.ScalarQueryParameter("name", "STRING", bq_leader.name),
            bigquery.ScalarQueryParameter("life", "INT64", bq_leader.life),
            bigquery.ScalarQueryParameter("power", "INT64", bq_leader.power),
            bigquery.ScalarQueryParameter("release_meta", "STRING", bq_leader.release_meta.value if bq_leader.release_meta else None),
            bigquery.ScalarQueryParameter("avatar_icon_url", "STRING", bq_leader.avatar_icon_url),
            bigquery.ScalarQueryParameter("image_url", "STRING", bq_leader.image_url),
            bigquery.ScalarQueryParameter("image_aa_url", "STRING", bq_leader.image_aa_url),
            bigquery.ArrayQueryParameter("colors", "STRING", bq_leader.colors),
            bigquery.ScalarQueryParameter("attribute", "STRING", bq_leader.attribute.value),
            bigquery.ScalarQueryParameter("ability", "STRING", bq_leader.ability),
            bigquery.ArrayQueryParameter("fractions", "STRING", bq_leader.fractions),
            bigquery.ScalarQueryParameter("language", "STRING", bq_leader.language.value),
        ]
    )

    query_job = client.query(merge_query, job_config=job_config)
    query_job.result()  # Wait for the job to complete

    print("Row updated successfully")

