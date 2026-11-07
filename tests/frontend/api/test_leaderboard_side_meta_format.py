"""
Tests for the in between set (side meta format) period of /api/leaderboard.
"""
import re

import pytest
from fasthtml.common import fast_app
from starlette.testclient import TestClient

from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion, SideMetaFormat
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.frontend.api import models as api_models
from op_tcg.frontend.api.routes import pages
from op_tcg.frontend.utils import api as api_utils
from op_tcg.frontend.utils.leader_data import get_template_leader


def _leader(win_rate: float) -> LeaderExtended:
    return LeaderExtended(**{
        **get_template_leader().model_dump(), "id": "OP17-001", "name": "Test Leader",
        "release_meta_format": MetaFormat.OP17, "meta_format": MetaFormat.OP17,
        "meta_format_region": MetaFormatRegion.ALL, "only_official": True, "tournament_wins": 1,
        "win_rate": win_rate, "total_matches": 10, "elo": 1100, "d_score": 0.5,
    })


@pytest.fixture
def client(monkeypatch):
    released = lambda meta_format, region=MetaFormatRegion.ALL: SideMetaFormat.EB05 if meta_format == MetaFormat.OP17 else None
    monkeypatch.setattr(api_models, "released_side_meta_format", released)
    monkeypatch.setattr(pages, "released_side_meta_format", released)
    monkeypatch.setattr(pages, "get_leader_extended", lambda **_: [_leader(0.111)])
    monkeypatch.setattr(api_utils, "get_side_meta_format_leader_extended", lambda *_: [_leader(0.777)])
    monkeypatch.setattr(pages, "get_leader_average_deck_prices", lambda **_: {})
    monkeypatch.setattr(pages, "get_side_meta_format_tournament_ids", lambda *_: frozenset())

    app, rt = fast_app(pico=False)
    pages.setup_api_routes(rt)
    with TestClient(app) as c:
        yield c


def test_side_meta_format_period_by_default(client):
    html = client.get("/api/leaderboard", params={"meta_format": "OP17"}).text
    assert "77.70%" in html and "11.10%" not in html
    assert "All of OP17" in html and "Since EB05" in html
    assert "30 Oct 2026" in html
    assert re.search(r'<input[^>]*name="side_meta_format" value="EB05"', html)


def test_full_meta_format_on_explicit_selection(client):
    html = client.get("/api/leaderboard", params={"meta_format": "OP17", "side_meta_format": "none"}).text
    assert "11.10%" in html and "77.70%" not in html
    assert re.search(r'<input[^>]*name="side_meta_format" value="none"', html)


def test_side_meta_format_ignored_for_other_meta_format(client):
    html = client.get("/api/leaderboard", params={"meta_format": "OP16", "side_meta_format": "EB05"}).text
    assert "77.70%" not in html
    assert "hp-period-chip" not in html
