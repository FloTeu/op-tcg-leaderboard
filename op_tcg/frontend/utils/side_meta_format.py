"""Leaderboard data of a meta format restricted to the tournaments played with its side meta format (in between set, e.g. EB05).

Mirrors the leaders.leader_extended view (op_tcg/backend/etl/sql/views/leaders.leader_extended.sql), but computes
win rate, tournament wins, elo and d_score only from the side meta format tournaments (see get_side_meta_format_tournament_ids).
Rows keep their main meta_format (e.g. OP17), so all leaderboard components can be reused unchanged.
"""
import threading
from collections import defaultdict

import pandas as pd
from cachetools import TTLCache, cached

from op_tcg.backend.elo import calculate_elo_with_soft_reset
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion, SideMetaFormat, side_meta_format2release_datetime
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.backend.models.matches import MatchResult
from op_tcg.backend.utils.utils import to_naive_utc
from op_tcg.frontend.utils.extract import get_leader_extended, get_meta_format_match_rows, \
    get_all_tournament_extened_data, get_all_tournament_decklist_data

# Same weights as in leaders.leader_extended
D_SCORE_WEIGHTS: dict[str, float] = {"win_rate": 0.1, "total_matches": 0.3, "elo": 0.2, "tournament_wins": 0.4}
# Share of the pre side meta format elo distance to 1000 which is carried over
ELO_CARRY_OVER = 0.5


def compute_d_scores(leaders: list[LeaderExtended]) -> dict[str, float]:
    """Dominance score per leader id: weighted sum of each metric normalized by its max over all given leaders.
    Leaders must belong to the same meta format, region and only_official group."""
    max_values = {metric: max((getattr(l, metric) or 0 for l in leaders), default=0) for metric in D_SCORE_WEIGHTS}
    return {
        l.id: sum(weight * (getattr(l, metric) or 0) / max_values[metric]
                  for metric, weight in D_SCORE_WEIGHTS.items() if max_values[metric])
        for l in leaders
    }


def _win_rates(df_matches: pd.DataFrame) -> dict[str, tuple[float, int]]:
    """Leader id to (win rate, number of matches), ignoring draws as in matches.leader_win_rate."""
    df_decided = df_matches[df_matches.result != MatchResult.DRAW]
    grouped = df_decided.groupby("leader_id").result
    wins = grouped.apply(lambda results: (results == MatchResult.WIN).sum())
    totals = grouped.size()
    return {lid: (wins[lid] / totals[lid], int(totals[lid])) for lid in totals.index}


@cached(cache=TTLCache(maxsize=16, ttl=60 * 60 * 6), condition=threading.Condition())
def get_side_meta_format_tournament_ids(meta_format: MetaFormat, side_meta_format: SideMetaFormat) -> frozenset[str]:
    """Ids of the meta format tournaments (all regions) played with the side meta format: tournaments starting after
    its release in the tournament's region, and earlier ones in which side meta format leaders or cards were already used.
    Other tournaments in the overlapping time are excluded, as they were still played without the new cards."""
    card_prefix = f"{side_meta_format}-"
    tournament_ids_with_cards = {
        d.tournament_id for d in get_all_tournament_decklist_data()
        if d.meta_format == meta_format and any(card_id.startswith(card_prefix) for card_id in d.decklist)
    }
    tournament_ids: set[str] = set()
    for tournament in get_all_tournament_extened_data(meta_formats=[meta_format]):
        release = side_meta_format2release_datetime(side_meta_format, tournament.meta_format_region or MetaFormatRegion.WEST)
        if ((release is not None and to_naive_utc(tournament.tournament_timestamp) >= release)
                or tournament.id in tournament_ids_with_cards
                or any(leader_id.startswith(card_prefix) for leader_id in tournament.leader_ids_placings or {})):
            tournament_ids.add(tournament.id)
    return frozenset(tournament_ids)


def _tournament_wins(meta_format: MetaFormat, tournament_ids: frozenset[str], region: MetaFormatRegion, only_official: bool) -> dict[str, int]:
    """Leader id to number of first placings, as in leaders.tournament_winner."""
    wins: dict[str, int] = defaultdict(int)
    for tournament in get_all_tournament_extened_data(meta_formats=[meta_format]):
        if tournament.id not in tournament_ids:
            continue
        if only_official and not tournament.official:
            continue
        if region != MetaFormatRegion.ALL and tournament.meta_format_region != region:
            continue
        for leader_id, placings in (tournament.leader_ids_placings or {}).items():
            wins[leader_id] += placings.count(1)
    return wins


@cached(cache=TTLCache(maxsize=16, ttl=60 * 60 * 6), condition=threading.Condition())
def _matches_and_elo(meta_format: MetaFormat, side_meta_format: SideMetaFormat, only_official: bool) -> tuple[dict[str, tuple[float, int]], dict[str, int]]:
    """Win rates and soft reset elo of the side meta format matches. Independent of the region, as matches have no region (like the views)."""
    df_matches = pd.DataFrame(get_meta_format_match_rows(meta_format))
    if only_official and not df_matches.empty:
        df_matches = df_matches[df_matches.official]
    if df_matches.empty:
        return {}, {}
    df_matches["match_timestamp"] = pd.to_datetime(df_matches.match_timestamp, utc=True).dt.tz_localize(None)
    # Matches without tournament fall back to the earliest release date
    release = side_meta_format2release_datetime(side_meta_format, MetaFormatRegion.ALL)
    in_side_meta_format = df_matches.tournament_id.isin(get_side_meta_format_tournament_ids(meta_format, side_meta_format)) | (
        df_matches.tournament_id.isna() & (df_matches.match_timestamp >= pd.Timestamp(release)))
    df_after = df_matches[in_side_meta_format]
    win_rates = _win_rates(df_after)
    elos = calculate_elo_with_soft_reset(df_matches[~in_side_meta_format], df_after, carry_over=ELO_CARRY_OVER)
    return win_rates, elos


@cached(cache=TTLCache(maxsize=32, ttl=60 * 60 * 6), condition=threading.Condition())
def _side_meta_format_leader_extended(meta_format: MetaFormat, side_meta_format: SideMetaFormat,
                                      region: MetaFormatRegion, only_official: bool) -> tuple[LeaderExtended, ...]:
    if side_meta_format2release_datetime(side_meta_format, region) is None:
        return ()

    # One base row per leader (static leader data), preferring the row of the requested only_official group
    lid2base: dict[str, LeaderExtended] = {}
    for leader in sorted(get_leader_extended(meta_formats=[meta_format], meta_format_region=region),
                         key=lambda l: l.only_official == only_official):
        if leader.only_official in (only_official, None):
            lid2base[leader.id] = leader

    win_rates, elos = _matches_and_elo(meta_format, side_meta_format, only_official)
    tournament_wins = _tournament_wins(
        meta_format, get_side_meta_format_tournament_ids(meta_format, side_meta_format), region, only_official)
    leaders = [
        leader.model_copy(update={
            "only_official": only_official,
            "win_rate": win_rates[lid][0] if lid in win_rates else None,
            "total_matches": win_rates[lid][1] if lid in win_rates else None,
            "elo": elos.get(lid),
            "tournament_wins": tournament_wins.get(lid, 0),
        })
        for lid, leader in lid2base.items()
    ]
    d_scores = compute_d_scores(leaders)
    return tuple(leader.model_copy(update={"d_score": d_scores[leader.id]}) for leader in leaders)


def get_side_meta_format_leader_extended(meta_format: MetaFormat, side_meta_format: SideMetaFormat,
                                         region: MetaFormatRegion = MetaFormatRegion.ALL,
                                         only_official: bool = True) -> list[LeaderExtended]:
    """LeaderExtended rows of meta_format, computed only from the tournaments played with the side_meta_format."""
    return list(_side_meta_format_leader_extended(meta_format, side_meta_format, region, only_official))
