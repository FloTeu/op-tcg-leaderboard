from datetime import datetime

import pytest
from scrapy.http import HtmlResponse

from op_tcg.backend.crawling.spiders.op_top_decks_decklists import OPTopDeckDecklistSpider
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion


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


_EB05_OP18_URL = "https://onepiecetopdecks.com/deck-list/japan-eb05op18-deck-list-heroines-and-the-dominance-of-god/"


@pytest.mark.parametrize("meta_formats", [
    [MetaFormat.OP17, MetaFormat.OP18, MetaFormat.OP19],  # cloud function
    [MetaFormat.OP18, MetaFormat.OP19],  # cli default
])
def test_landingpage_takes_latest_meta_format_of_url(meta_formats):
    spider = OPTopDeckDecklistSpider()
    spider.meta_formats = meta_formats
    spider.proxy_url = None
    response = HtmlResponse(url="https://onepiecetopdecks.com/deck-list/",
                            body=f'<a href="{_EB05_OP18_URL}">x</a>'.encode(), encoding="utf-8")

    requests = list(spider.parse_decklist_landingpage(response))

    assert [r.meta["meta_format"] for r in requests] == [MetaFormat.OP18]


@pytest.mark.parametrize("region", [MetaFormatRegion.ASIA, MetaFormatRegion.WEST])
@pytest.mark.parametrize("tournament_datetime,expected", [
    (datetime(2026, 11, 1, 0, 1), MetaFormat.OP17),  # EB05 weeks before the OP18 release (2026-11-20)
    (datetime(2026, 11, 12, 23, 59), MetaFormat.OP17),
    (datetime(2026, 11, 13, 0, 1), MetaFormat.OP18),  # within the one week pre-release buffer
    (datetime(2026, 11, 20, 0, 1), MetaFormat.OP18),  # release day
    (datetime(2026, 12, 1, 0, 1), MetaFormat.OP18),
])
def test_meta_format_at(region, tournament_datetime, expected):
    assert OPTopDeckDecklistSpider.meta_format_at(MetaFormat.OP18, region, tournament_datetime) == expected


def test_meta_format_at_keeps_first_meta_format():
    assert OPTopDeckDecklistSpider.meta_format_at(MetaFormat.OP01, MetaFormatRegion.WEST, datetime(2000, 1, 1)) == MetaFormat.OP01


def test_parse_html_table_without_deck_composition_header():
    # onepiecetopdecks.com omits the th of the deck composition column, so header positions are shifted by one
    header = "".join(f'<th class="column-{i}">{name}</th>' for i, name in enumerate(
        ["Details", "Deck Color", "Deck Profile", "Deck Name", "Date", "Country", "Author", "Placement",
         "Tournament", "Host"], start=2))
    row = ('<tr class="row-2"><td class="column-1">1nOP13-079a2nOP05-082a4nOP13-086</td>'
           '<td class="column-2"><a href="deckgen?dn=Imu&amp;date=10/25/2026"> <img src="x"/> </a></td>'
           '<td class="column-3">Black</td><td class="column-4">op13imu</td><td class="column-5">Imu</td>'
           '<td class="column-6">10/25/2026</td><td class="column-7">JP</td><td class="column-8">Tatsoo</td>'
           '<td class="column-9">1st (7-1)</td><td class="column-10">3v3</td><td class="column-11">AsuCS</td></tr>')
    table_html = f"<table><thead><tr>{header}</tr></thead><tbody>{row}</tbody></table>"

    item = OPTopDeckDecklistSpider().parse_html_table(table_html, "https://onepiecetopdecks.com/deck-list/x/",
                                                      MetaFormat.OP18, MetaFormatRegion.ASIA)

    op_top_deck_decklist = item.op_top_deck_decklists[0]
    tournament = item.tournaments[0]
    standing = item.tournament_standings[0]
    assert op_top_deck_decklist.decklist_source == "https://onepiecetopdecks.com/deck-list/x/deckgen?dn=Imu&date=10/25/2026"
    assert op_top_deck_decklist.country == "JP"
    assert op_top_deck_decklist.author == "Tatsoo"
    assert op_top_deck_decklist.host == "AsuCS"
    assert tournament.tournament_timestamp.date() == datetime(2026, 10, 25).date()
    assert tournament.meta_format == MetaFormat.OP17
    assert tournament.name == "AsuCS 3v3"
    assert standing.placing == 1
    assert standing.leader_id == "OP13-079"
