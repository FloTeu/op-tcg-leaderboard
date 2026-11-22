import pytest

from op_tcg.backend.etl.extract import parse_attributes
from op_tcg.backend.models.cards import OPTcgAttribute


@pytest.mark.parametrize("raw, expected", [
    ("Slash", [OPTcgAttribute.SLASH]),
    ("Slash/Ranged", [OPTcgAttribute.SLASH, OPTcgAttribute.RANGED]),
    ("?", [OPTcgAttribute.UNKNOWN]),
    # untranslated key limitless renders for unset attributes (fullwidth question mark, e.g. OP18-065)
    ("card.attribute.？", [OPTcgAttribute.UNKNOWN]),
])
def test_parse_attributes(raw, expected):
    assert parse_attributes(f"\n  {raw} ") == expected
