from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fasthtml.common import to_xml

from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion, SideMetaFormat
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.backend.models.matches import MatchResult
from op_tcg.frontend.api.models import LeaderboardFilter
from op_tcg.frontend.pages.home import create_period_toggle
from op_tcg.frontend.utils import side_meta_format as smf
from op_tcg.frontend.utils.leader_data import get_template_leader

RELEASE = datetime(2026, 10, 30)
BEFORE = datetime(2026, 10, 20, tzinfo=timezone.utc)
AFTER = datetime(2026, 11, 2, tzinfo=timezone.utc)


def _leader(lid: str, only_official: bool | None = True, **stats) -> LeaderExtended:
    return LeaderExtended(**{
        **get_template_leader().model_dump(), "id": lid, "release_meta_format": MetaFormat.OP17,
        "meta_format": MetaFormat.OP17, "meta_format_region": MetaFormatRegion.ALL, "only_official": only_official,
        "tournament_wins": 0, "win_rate": None, "total_matches": None, "elo": None, "d_score": None, **stats,
    })


def _match_rows(game_id: str, leader: str, opponent: str, result: MatchResult, timestamp: datetime,
                tournament_id: str | None, official=True):
    common = {"id": game_id, "official": official, "meta_format": "OP17", "match_timestamp": timestamp,
              "tournament_id": tournament_id}
    return [{**common, "leader_id": leader, "opponent_id": opponent, "result": int(result)},
            {**common, "leader_id": opponent, "opponent_id": leader, "result": 2 - int(result)}]


def _tournament(tid: str, placings: dict, timestamp: datetime, official=True, region=MetaFormatRegion.WEST):
    return SimpleNamespace(id=tid, leader_ids_placings=placings, tournament_timestamp=timestamp, official=official,
                           meta_format_region=region)


@pytest.fixture
def data(monkeypatch):
    smf._side_meta_format_leader_extended.cache.clear()
    smf._matches_and_elo.cache.clear()
    smf.get_side_meta_format_tournament_ids.cache.clear()
    matches = [
        *_match_rows("old", "A", "B", MatchResult.WIN, BEFORE, "t_old"),
        *_match_rows("g1", "A", "B", MatchResult.LOSE, AFTER, "t_after"),
        *_match_rows("g2", "A", "B", MatchResult.DRAW, AFTER, "t_after"),
        *_match_rows("g3", "A", "C", MatchResult.WIN, BEFORE, "t_early_cards"),
        *_match_rows("free", "C", "B", MatchResult.WIN, AFTER, None),
        *_match_rows("unofficial", "C", "B", MatchResult.WIN, AFTER, "t_unofficial", official=False),
    ]
    tournaments = [
        _tournament("t_old", {"A": [1, 3]}, BEFORE),
        _tournament("t_early_cards", {"B": [1]}, BEFORE),
        _tournament("t_early_leader", {"EB05-010": [1]}, BEFORE),
        _tournament("t_asia_early", {"C": [1]}, BEFORE, region=MetaFormatRegion.ASIA),
        _tournament("t_after", {"B": [1], "A": [2]}, AFTER),
        _tournament("t_unofficial", {"C": [1]}, AFTER, official=False),
        _tournament("t_asia", {"C": [1]}, AFTER, region=MetaFormatRegion.ASIA),
    ]
    decklists = [
        SimpleNamespace(tournament_id="t_old", meta_format=MetaFormat.OP17, decklist={"OP17-010": 4}),
        SimpleNamespace(tournament_id="t_early_cards", meta_format=MetaFormat.OP17, decklist={"EB05-020": 2}),
        SimpleNamespace(tournament_id="other_meta", meta_format=MetaFormat.OP16, decklist={"EB05-020": 2}),
    ]
    base_leaders = [_leader("A", win_rate=0.9, elo=1500), _leader("A", only_official=False), _leader("B"),
                    _leader("C", only_official=None)]
    monkeypatch.setattr(smf, "get_meta_format_match_rows", lambda mf: matches)
    monkeypatch.setattr(smf, "get_all_tournament_extened_data", lambda meta_formats: tournaments)
    monkeypatch.setattr(smf, "get_all_tournament_decklist_data", lambda: decklists)
    monkeypatch.setattr(smf, "get_leader_extended", lambda meta_formats, meta_format_region: base_leaders)


def _get(region=MetaFormatRegion.ALL, only_official=True) -> dict[str, LeaderExtended]:
    leaders = smf.get_side_meta_format_leader_extended(MetaFormat.OP17, SideMetaFormat.EB05, region, only_official)
    return {l.id: l for l in leaders}


def test_tournaments_after_release_or_with_early_side_meta_format_usage(data):
    assert smf.get_side_meta_format_tournament_ids(MetaFormat.OP17, SideMetaFormat.EB05) == {
        "t_early_cards", "t_early_leader", "t_after", "t_unofficial", "t_asia"}


def test_tournaments_use_release_date_of_their_region(data, monkeypatch):
    asia_release = datetime(2026, 10, 10)
    monkeypatch.setattr(smf, "side_meta_format2release_datetime",
                        lambda sf, region: asia_release if region == MetaFormatRegion.ASIA else RELEASE)
    tournament_ids = smf.get_side_meta_format_tournament_ids(MetaFormat.OP17, SideMetaFormat.EB05)
    assert "t_asia_early" in tournament_ids
    assert "t_old" not in tournament_ids


def test_stats_only_use_side_meta_format_tournaments(data):
    leaders = _get()
    assert set(leaders) == {"A", "B", "C"}
    # draw is ignored, t_old is excluded, the early t_early_cards counts
    assert (leaders["A"].win_rate, leaders["A"].total_matches) == (0.5, 2)
    # match without tournament after the release counts
    assert (leaders["B"].win_rate, leaders["B"].total_matches) == (0.5, 2)
    assert leaders["A"].tournament_wins == 0
    assert leaders["B"].tournament_wins == 2
    # asia tournament counts for region all, unofficial does not
    assert leaders["C"].tournament_wins == 1
    assert all(l.only_official is True for l in leaders.values())


def test_region_and_official_filters(data):
    assert _get(region=MetaFormatRegion.WEST)["C"].tournament_wins == 0
    assert _get(region=MetaFormatRegion.ASIA)["C"].tournament_wins == 1
    unofficial = _get(only_official=False)
    assert unofficial["C"].tournament_wins == 2
    assert unofficial["C"].total_matches == 3


def test_elo_and_d_score_are_recomputed(data):
    leaders = _get()
    # elo is recomputed from matches instead of taken from the full meta format row
    assert leaders["A"].elo != 1500
    assert leaders["B"].d_score == pytest.approx(
        0.1 * 0.5 / 0.5 + 0.3 * 2 / 2 + 0.2 * leaders["B"].elo / max(l.elo for l in leaders.values()) + 0.4 * 2 / 2)


def test_no_release_date_returns_no_leaders(data, monkeypatch):
    monkeypatch.setattr(smf, "side_meta_format2release_datetime", lambda *_: None)
    assert _get() == {}


def test_compute_d_scores_matches_view_formula():
    leaders = [_leader("A", win_rate=0.6, total_matches=100, elo=1100, tournament_wins=2),
               _leader("B", win_rate=0.3, total_matches=50, elo=None, tournament_wins=0),
               _leader("C")]
    d_scores = smf.compute_d_scores(leaders)
    assert d_scores["A"] == pytest.approx(1.0)
    assert d_scores["B"] == pytest.approx(0.1 * 0.5 + 0.3 * 0.5)
    assert d_scores["C"] == 0


@pytest.mark.parametrize("meta_format, side_meta_format, expected", [
    ("OP17", "EB05", SideMetaFormat.EB05),
    ("OP16", "EB05", None),
    ("OP17", "", None),
    ("OP17", ["EB05"], SideMetaFormat.EB05),
])
def test_leaderboard_filter_only_keeps_released_side_meta_format(meta_format, side_meta_format, expected):
    params = LeaderboardFilter(meta_format=meta_format, side_meta_format=side_meta_format)
    assert params.side_meta_format == expected


def test_period_toggle_shows_both_regional_releases_for_region_all():
    html = to_xml(create_period_toggle(MetaFormat.OP10, MetaFormatRegion.ALL, SideMetaFormat.EB02, SideMetaFormat.EB02))
    assert "West" in html and "9 May 2025" in html
    assert "Asia" in html and "25 Jan 2025" in html

    west = to_xml(create_period_toggle(MetaFormat.OP10, MetaFormatRegion.WEST, SideMetaFormat.EB02, SideMetaFormat.EB02))
    assert "9 May 2025" in west and "25 Jan 2025" not in west


def test_period_toggle_hidden_without_released_side_meta_format():
    html = to_xml(create_period_toggle(MetaFormat.OP16, MetaFormatRegion.ALL, None, None))
    assert 'name="side_meta_format"' in html
    assert "hp-period-chip" not in html


def test_period_toggle_marks_selection_and_explains_period():
    html = to_xml(create_period_toggle(MetaFormat.OP17, MetaFormatRegion.ALL, SideMetaFormat.EB05, SideMetaFormat.EB05))
    assert 'value="EB05"' in html
    assert html.count('aria-pressed="true"') == 1
    assert "Since EB05" in html and "All of OP17" in html
    assert "Tournaments since" in html and "30 Oct 2026" in html
    assert "earlier ones where EB05 cards were already played" in html

    unselected = to_xml(create_period_toggle(MetaFormat.OP17, MetaFormatRegion.ALL, SideMetaFormat.EB05, None))
    assert "30 Oct 2026" not in unselected
