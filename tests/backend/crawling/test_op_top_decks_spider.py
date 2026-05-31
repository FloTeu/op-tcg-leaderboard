import pytest

from op_tcg.backend.crawling.spiders.op_top_decks_decklists import OPTopDeckDecklistSpider


@pytest.fixture(scope="module")
def spider():
    return OPTopDeckDecklistSpider()


# (input, expected_output)
_VALID_CASES = [
    ("1st (8-0)", 1),
    ("1st (8-0)", 1),
    ("1st Place", 1),
    ("2nd Place", 2),
    ("3rd Place", 3),
    ("4th Place", 4),
    ("10th Place", 10),
    ("32nd Place", 32),
    # case / whitespace variants
    ("1ST PLACE", 1),
    ("  1st Place  ", 1),
    ("1st place", 1),
    # Top-N format
    ("T4", 4),
    ("T4 (4-1)", 4),
    ("Top-8", 8),
    ("Top-16", 16),
    ("Top-32", 32),
    ("top-4", 4),
    ("TOP-64", 64),
]

_INVALID_CASES = [
    "",
    "Winner",
    "Top",           # 'top' present but no '-N' part
    "Top-",          # dash but no digit
    "Top-eight",     # word, not digit
    "Place",         # 'place' present but no ordinal prefix
    "1st",           # ordinal but no 'place'
    "random text",
    "1st-Place",     # wrong separator — first_part[:-2] is '1s', not a digit
]


@pytest.mark.parametrize("text,expected", _VALID_CASES)
def test_parse_placing_text_valid(spider, text, expected):
    assert spider.parse_placing_text(text) == expected


@pytest.mark.parametrize("text", _INVALID_CASES)
def test_parse_placing_text_invalid(spider, text):
    assert spider.parse_placing_text(text) is None
