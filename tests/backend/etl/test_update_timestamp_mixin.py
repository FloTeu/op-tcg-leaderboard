from datetime import date

import pytest

from op_tcg.backend.models.cardnexus import (
    CardNexusCardProduct, CardNexusCardProductMapping, CardNexusPrice, CardNexusSealedProduct,
    CardNexusSealedProductMapping,
)
from op_tcg.backend.models.sealed import SealedProduct
from op_tcg.backend.utils.annotations import pydantic_model_to_bq_schema


@pytest.mark.parametrize("model", [
    CardNexusCardProduct, CardNexusSealedProduct, CardNexusPrice,
    CardNexusCardProductMapping, CardNexusSealedProductMapping,
])
def test_cardnexus_tables_end_with_create_and_update_timestamp(model):
    names = [f.name for f in pydantic_model_to_bq_schema(model)]
    assert names[-2:] == ["create_timestamp", "update_timestamp"]


def test_update_timestamp_is_opt_in():
    assert "update_timestamp" not in SealedProduct.model_fields


def test_update_timestamp_defaults_to_write_time():
    row = CardNexusPrice(product_id="p1", marketplace="cardnexus", finish="Standard",
                         date=date(2026, 11, 1), raw_json="{}")
    assert row.update_timestamp is not None
    assert row.model_dump()["update_timestamp"] == row.update_timestamp
