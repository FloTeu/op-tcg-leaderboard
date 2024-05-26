import pandera as pa
import pandas as pd
from datetime import datetime, date
from enum import IntEnum, Enum, StrEnum
from types import UnionType, GenericAlias, NoneType
from typing import get_origin, get_args

from google.cloud import bigquery
from pydantic import BaseModel
from pydantic.fields import FieldInfo

from op_tcg.backend.models.bq_enums import BQFieldType, BQFieldMode


def pydantic_type_to_pandera_type(field_info) -> pa.Column:
    pydantic_type = pydantic_field_annotation_to_type(field_info)
    nullable = False
    if isinstance(field_info.annotation, UnionType) and any(
            arg == NoneType for arg in get_args(field_info.annotation)):
        nullable = True
    elif field_info.is_required():
        nullable = False
    is_int = any([issubclass(pydantic_type, type_) for type_ in [int, IntEnum]])
    is_float = any([issubclass(pydantic_type, type_) for type_ in [float]])
    if pydantic_type == bool:
        return pa.Column(pa.Bool, nullable=nullable)
    elif is_float or (is_int and nullable):
        # nullable int pandas columns do not exist
        return pa.Column(pa.Float, nullable=nullable)
    elif is_int:
        return pa.Column(pa.Int, nullable=nullable)
    elif any([issubclass(pydantic_type, type_) for type_ in [str, Enum, StrEnum]]):
        return pa.Column(pa.String, nullable=nullable)
    elif pydantic_type == datetime:
        # Use a custom check to allow timezone-aware datetime columns
        return pa.Column(pd.DatetimeTZDtype(tz="UTC"), nullable=nullable)
    # Add more mappings as necessary
    # Note: You may need to handle more complex types or custom types
    else:
        raise ValueError(f"Unsupported Pydantic type: {pydantic_type}")

def create_pandera_schema_from_pydantic(pydantic_class: type[BaseModel]) -> pa.DataFrameSchema:
    schema_fields = {}
    for field_name, field_model in pydantic_class.__fields__.items():
        pandera_column = pydantic_type_to_pandera_type(field_model)
        schema_fields[field_name] = pandera_column
    return pa.DataFrameSchema(schema_fields)


def pydantic_field_annotation_to_type(field_info: FieldInfo):
    """Handles union type annotation and returns first typing"""
    field_type = field_info.annotation
    if isinstance(field_type, UnionType):
        # Assume first type of union typing is the necessary one for BQ
        field_type = field_type.__args__[0]

    if isinstance(field_type, GenericAlias) and not get_origin(field_type) == dict:
        # Assumption: Every field_type which is a GenericAlias (and not dict), is a list
        field_type = field_type.__args__[0]
    return field_type


def pydantic_model_to_bq_types(model: type[BaseModel]) -> dict[str, bigquery.SchemaField]:
    field_name2bq_types = {}
    for field_name, field_info in model.__fields__.items():
        field_type = pydantic_field_annotation_to_type(field_info)
        # get field type
        field_name2bq_types[field_name] = get_bq_field_type(field_type)
    return field_name2bq_types


def get_bq_field_type(field_type) -> bigquery.SchemaField:
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
    return bq_type


def field_info_is_list(field_info: FieldInfo) -> bool:
    # Assumption: Every field_type which is a GenericAlias (and not dict), is a list
    return isinstance(field_info.annotation, GenericAlias) and not get_origin(field_info.annotation) == dict


def pydantic_model_to_bq_schema(model: type[BaseModel]) -> list[bigquery.SchemaField]:
    """ Function to convert Pydantic model to BigQuery schema"""
    schemata = []
    field_name2bq_types = pydantic_model_to_bq_types(model)
    fields = model.__fields__
    # but timestamp to end of schema
    if "create_timestamp" in fields:
        field_info_create_timestamp = fields["create_timestamp"]
        fields.pop('create_timestamp', None)
        fields["create_timestamp"] = field_info_create_timestamp

    for field_name, field_info in fields.items():
        bq_type = field_name2bq_types[field_name]
        is_list = field_info_is_list(field_info)

        # get mode
        mode = BQFieldMode.NULLABLE  # Default BigQuery mode
        if is_list:
            mode = BQFieldMode.REPEATED
        elif isinstance(field_info.annotation, UnionType) and any(arg == NoneType for arg in get_args(field_info.annotation)):
            mode = BQFieldMode.NULLABLE
        elif field_info.is_required():
            mode = BQFieldMode.REQUIRED
        # Add more type conversions as needed
        schemata.append(bigquery.SchemaField(field_name, bq_type, description=field_info.description, mode=mode))
    return schemata
