import json
import os
import logging
import sys
import uuid
from datetime import datetime, date, timedelta
from typing import Any

from google.cloud import bigquery
from google.cloud import storage
from google.cloud.exceptions import NotFound
from google.cloud.bigquery import QueryJobConfig

from op_tcg.backend.models.base import SQLTableBaseModel
from op_tcg.backend.models.storage import StorageBucket
from op_tcg.backend.utils.annotations import pydantic_model_to_bq_types, pydantic_model_to_bq_schema

_logger = logging.getLogger("load")

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
        _logger.debug(f"Dataset {dataset_id} already exists.")
    except NotFound:
        # If the dataset does not exist, create it
        dataset.location = location
        dataset = client.create_dataset(dataset, timeout=30)
        _logger.info(f"Dataset {dataset_id} created.")

    return dataset


def table_exists(bq_table_model: Any, client: bigquery.Client | None = None) -> bool:
    """
    Check if a BigQuery table exists.

    :param bq_table_model: BQTableBaseModel - The BQ table model instance or class.
    :param client: bigquery.Client - The BigQuery client.
    :return: bool - True if the table exists, False otherwise.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    client = client if client else bigquery.Client(project=project_id)

    dataset_id = bq_table_model.get_dataset_id()
    table_name = bq_table_model.__tablename__
    table_id = f"{client.project}.{dataset_id}.{table_name}"

    try:
        client.get_table(table_id)
        return True
    except NotFound:
        return False


# Function to get or create a BigQuery table
def get_or_create_table(model: type[SQLTableBaseModel], dataset_id: str | None = None, table_id: str | None = None,
                        client: bigquery.Client | None = None, location: str = 'europe-west3',
                        project_id: str | None = None) -> bigquery.Table:
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
    dataset_id = dataset_id or model._dataset_id.default
    project_id = project_id if project_id else os.environ.get("GOOGLE_CLOUD_PROJECT")
    client = client if client else bigquery.Client(project=project_id)
    dataset = get_or_create_bq_dataset(dataset_id, client=client, location=location)
    # TODO: check if we can extract the table ref from this object
    table_id = table_id if table_id else model.__tablename__
    table_ref = dataset.table(table_id)

    try:
        # Try to get the table (will raise NotFound if it does not exist)
        table = client.get_table(table_ref)
        _logger.debug(f"Table {table_id} already exists.")
    except NotFound:
        # If the table does not exist, create it
        schema = pydantic_model_to_bq_schema(model)
        table = bigquery.Table(table_ref, schema=schema)
        table = client.create_table(table)
        _logger.info(f"Table {table_id} created.")

    return table


def ensure_json_serializability(row_to_insert):
    for col_name, col_value in row_to_insert.items():
        if type(col_value) in [date, datetime, dict]:
            row_to_insert[col_name] = str(col_value)
        if type(col_value) in [list]:
            for i, col_value_i in enumerate(col_value):
                if type(col_value_i) == dict:
                    row_to_insert[col_name][i] = str(col_value_i)


def bq_insert_rows(rows_to_insert: list[dict[str, Any]], table: bigquery.Table,
                   client: bigquery.Client | None = None) -> None:
    """Adds a new row to BigQuery"""
    if len(rows_to_insert) == 0:
        _logger.warning(f"Skip bq insert in table {table}, as no rows are provided.")
        return None
    client = client if client else bigquery.Client()
    for row in rows_to_insert:
        ensure_json_serializability(row)
    table_id = f"{table.project}.{table.dataset_id}.{table.table_id}"

    errors = client.insert_rows_json(table_id, rows_to_insert)  # Make an API request.
    if errors == []:
        _logger.debug("New rows have been added.")
    else:
        raise ValueError("Encountered errors while inserting rows: {}".format(errors))


def generate_merge_statement(bq_model: SQLTableBaseModel) -> str:
    """Function to generate MERGE statement for upserting a row"""
    model_dict = json.loads(bq_model.model_dump_json())
    ensure_json_serializability(model_dict)
    # Prepare the columns and corresponding values
    columns = ', '.join(f"`{key}`" for key in model_dict.keys())
    values_placeholders = ', '.join(f"@{key}" for key in model_dict.keys())

    # Prepare the primary keys for the ON clause
    primary_keys = [field for field, value in bq_model.__fields__.items() if
                    value.json_schema_extra and value.json_schema_extra.get('primary_key', False)]
    on_clause = ' AND '.join(f"target.`{pk}` = @{pk}" for pk in primary_keys)

    # Exclude primary keys from the UPDATE SET clause
    update_clause = ', '.join(
        f"target.`{key}` = @{key}" for key in model_dict.keys() if key not in primary_keys)

    # Construct the MERGE statement
    merge_sql = f"""
    MERGE `{bq_model._dataset_id}.{bq_model.__tablename__}` target
    USING (SELECT 1) S
    ON {on_clause}
    WHEN MATCHED THEN
        UPDATE SET {update_clause}
    WHEN NOT MATCHED THEN
        INSERT ({columns}) VALUES ({values_placeholders})
    """
    return merge_sql.strip()

def bq_upsert_row(bq_model: SQLTableBaseModel, client: bigquery.Client | None = None):
    """Either inserts new row if not exists yet, or updates ro in BQ """
    client = client if client else bigquery.Client()

    merge_sql = generate_merge_statement(bq_model)

    # Prepare the query parameters
    model_dict = json.loads(bq_model.model_dump_json())
    ensure_json_serializability(model_dict)
    field_name2bq_field_type: dict[str, bigquery.SchemaField] = pydantic_model_to_bq_types(bq_model)
    query_params = []
    for key, value in model_dict.items():
        if any(isinstance(value, type_) for type_ in [list, tuple, set]):
            query_params.append(bigquery.ArrayQueryParameter(key, field_name2bq_field_type[key], value))
        else:
            query_params.append(bigquery.ScalarQueryParameter(key, field_name2bq_field_type[key], value))

    job_config = QueryJobConfig(query_parameters=query_params)

    query_job = client.query(merge_sql, job_config=job_config)

    try:
        # Run the query and wait for it to complete
        query_job.result()
        _logger.debug("Row upserted successfully.")
    except Exception as e:
        _logger.exception(f"An error occurred: {e}")


def upload2gcp_storage(path_to_file: str, blob_name: str, bucket: str = StorageBucket.PUBLIC_BUCKET, content_type: str | None = None, client: storage.Client | None = None):
    client = client or storage.Client()
    bucket = client.get_bucket(bucket)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(path_to_file, content_type=content_type)

def bq_upsert_rows(rows: list[SQLTableBaseModel], client: bigquery.Client | None = None, table: bigquery.Table | None = None):
    """
    Upserts multiple rows into BigQuery using a temporary table and MERGE statement.
    """
    if not rows:
        return

    client = client or bigquery.Client()
    model_class = type(rows[0])

    # Get target table
    if table:
        target_table = table
    else:
        target_table = get_or_create_table(model_class, client=client)

    target_table_id = f"{target_table.project}.{target_table.dataset_id}.{target_table.table_id}"

    # Create temp table
    dataset_ref = bigquery.DatasetReference(target_table.project, target_table.dataset_id)
    temp_table_ref = dataset_ref.table(f"{target_table.table_id}_temp_{uuid.uuid4().hex}")

    schema = pydantic_model_to_bq_schema(model_class)
    temp_table = bigquery.Table(temp_table_ref, schema=schema)
    temp_table.expires = datetime.now() + timedelta(hours=1)

    try:
        temp_table = client.create_table(temp_table)
    except Exception as e:
        _logger.error(f"Failed to create temp table {temp_table_ref}: {e}")
        return

    try:
        # Insert rows into temp table
        rows_dicts = [json.loads(row.model_dump_json()) for row in rows]
        for row in rows_dicts:
            ensure_json_serializability(row)

        errors = client.insert_rows_json(temp_table, rows_dicts)
        if errors:
             raise ValueError(f"Encountered errors while inserting rows into temp table: {errors}")

        # Generate MERGE statement
        primary_keys = [field for field, value in model_class.model_fields.items() if
                        value.json_schema_extra and value.json_schema_extra.get('primary_key', False)]

        if not primary_keys:
             _logger.warning(f"No primary keys found for {model_class.__name__}, falling back to append-only insert.")
             # Fallback to insert?
             return

        # Columns to update (all except PKs)
        all_columns = list(rows_dicts[0].keys())
        update_columns = [col for col in all_columns if col not in primary_keys]

        on_clause = ' AND '.join(f"target.`{pk}` = source.`{pk}`" for pk in primary_keys)

        if update_columns:
            update_expressions = []
            for col in update_columns:
                # Special handling for image_url column to avoid overwriting updated URLs
                if col == 'image_url':
                    update_expressions.append(f"target.`{col}` = IF(STARTS_WITH(target.`{col}`, 'https://storage.googleapis.com'), target.`{col}`, source.`{col}`)")
                else:
                    update_expressions.append(f"target.`{col}` = source.`{col}`")
            update_clause = ', '.join(update_expressions)
            when_matched = f"WHEN MATCHED THEN UPDATE SET {update_clause}"
        else:
            when_matched = ""

        insert_columns = ', '.join(f"`{col}`" for col in all_columns)
        insert_values = ', '.join(f"source.`{col}`" for col in all_columns)

        merge_sql = f"""
        MERGE `{target_table_id}` target
        USING `{temp_table.project}.{temp_table.dataset_id}.{temp_table.table_id}` source
        ON {on_clause}
        {when_matched}
        WHEN NOT MATCHED THEN
            INSERT ({insert_columns}) VALUES ({insert_values})
        """

        query_job = client.query(merge_sql)
        query_job.result()
        _logger.info(f"Upserted {len(rows)} rows into {target_table_id}")

    except Exception as e:
        _logger.exception(f"An error occurred during upsert: {e}")
    finally:
        # Delete temp table
        client.delete_table(temp_table, not_found_ok=True)
