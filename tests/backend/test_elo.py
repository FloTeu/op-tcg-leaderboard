import pandas as pd

from op_tcg.backend.elo import EloCreator, calculate_elo_with_soft_reset
from op_tcg.backend.models.matches import MatchResult


def _matches(*games: tuple[str, str, str, MatchResult]) -> pd.DataFrame:
    """Each game (timestamp, leader, opponent, result of leader) becomes the match row and its reverse row."""
    rows = []
    for i, (timestamp, leader, opponent, result) in enumerate(games):
        for lid, oid, res in ((leader, opponent, result), (opponent, leader, MatchResult(2 - result))):
            rows.append({"id": f"m{i}", "leader_id": lid, "opponent_id": oid, "result": res, "official": True,
                         "meta_format": "OP17", "match_timestamp": pd.Timestamp(timestamp)})
    return pd.DataFrame(rows)


DF = _matches(
    ("2026-10-01", "A", "B", MatchResult.WIN),
    ("2026-10-02", "A", "C", MatchResult.WIN),
    ("2026-10-03", "B", "C", MatchResult.WIN),
    ("2026-11-01", "C", "A", MatchResult.WIN),
    ("2026-11-02", "C", "B", MatchResult.WIN),
)
RESET = pd.Timestamp("2026-10-30")
BEFORE, AFTER = DF[DF.match_timestamp < RESET], DF[DF.match_timestamp >= RESET]


def _elo(df, **kwargs) -> dict[str, int]:
    creator = EloCreator(df, **kwargs)
    creator.calculate_elo_ratings()
    return creator.leader_id2elo


def test_initial_elo_is_used_as_start_rating():
    assert EloCreator(DF, initial_elo={"A": 1200}).leader_id2elo == {"A": 1200, "B": 1000, "C": 1000}


def test_full_carry_over_equals_elo_of_all_matches():
    assert calculate_elo_with_soft_reset(BEFORE, AFTER, carry_over=1.0) == _elo(DF)


def test_no_carry_over_equals_elo_of_matches_after_reset():
    assert calculate_elo_with_soft_reset(BEFORE, AFTER, carry_over=0.0) == _elo(AFTER)


def test_partial_carry_over_halves_distance_to_1000():
    seed = {lid: int(round(1000 + 0.5 * (elo - 1000))) for lid, elo in _elo(BEFORE).items()}
    assert calculate_elo_with_soft_reset(BEFORE, AFTER) == _elo(AFTER, initial_elo=seed)


def test_no_matches_after_reset_returns_empty():
    assert calculate_elo_with_soft_reset(DF, DF.iloc[0:0]) == {}


def test_no_matches_before_reset_starts_at_1000():
    assert calculate_elo_with_soft_reset(DF.iloc[0:0], AFTER) == _elo(AFTER)
