import datetime
import random
from datetime import timedelta, datetime

import pandas as pd

from op_tcg.backend.elo import calculate_new_elo
from op_tcg.backend.models.input import LimitlessLeaderMetaMatches, LimitlessMatch, MetaFormat
from op_tcg.backend.models.matches import BQMatches, BQMatch, MatchResult, BQLeaderElo


def randomize_datetime(start_datetime: datetime):
    # Generate a random number of days, hours, and minutes within the range of 10 days
    days = random.randint(-10, 10)
    hours = random.randint(-12, 12)
    minutes = random.randint(-60, 60)

    # Create a timedelta object with the random values
    delta = timedelta(days=days, hours=hours, minutes=minutes)

    # Add the timedelta to the start datetime
    result_datetime = start_datetime + delta

    return result_datetime


def meta_format2release_datetime(meta_format: MetaFormat) -> datetime:
    if meta_format == MetaFormat.OP01:
        return datetime(2022, 12, 2)
    if meta_format == MetaFormat.OP02:
        return datetime(2023, 3, 10)
    if meta_format == MetaFormat.OP03:
        return datetime(2023, 6, 30)
    if meta_format == MetaFormat.OP04:
        return datetime(2023, 9, 22)
    if meta_format == MetaFormat.OP05:
        return datetime(2023, 12, 8)
    if meta_format == MetaFormat.OP06:
        return datetime(2024, 3, 8)


def meta_format2approximate_datetime(meta_format: MetaFormat) -> datetime:
    # expect tournaments starting half a month after release of new set
    return meta_format2release_datetime(meta_format) + timedelta(days=15)

def limitless_matches2bq_matches(limitless_matches: LimitlessLeaderMetaMatches) -> list[BQMatch]:
    meta_format = limitless_matches.meta_format
    matches: list[BQMatch] = []
    for limitless_match in limitless_matches.matches:
        # extracts results
        results: list[MatchResult] = []
        for _ in range(limitless_match.score_win):
            results.append(MatchResult.WIN)
        for _ in range(limitless_match.score_lose):
            results.append(MatchResult.LOSE)
        for _ in range(limitless_match.score_draw):
            results.append(MatchResult.DRAW)
        # transform to bq matches
        for result in results:
            bq_match = BQMatch(
                leader_id=limitless_matches.leader_id,
                opponent_id=limitless_match.leader_id,
                result=result,
                meta_format=meta_format,
                official=True,
                timestamp=randomize_datetime(meta_format2approximate_datetime(meta_format))
            )
            matches.append(bq_match)
    return matches

