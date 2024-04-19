import datetime
import random
from datetime import timedelta, datetime

import pandas as pd
from pydantic import BaseModel

from op_tcg.backend.elo import calculate_new_elo
from op_tcg.backend.models.input import LimitlessLeaderMetaMatches, LimitlessMatch, MetaFormat, AllMetaLeaderMatches
from op_tcg.backend.models.matches import BQMatches, BQMatch, MatchResult, BQLeaderElo


class TransformMatch(BaseModel):
    leader_id: str
    opponent_id: str
    result: MatchResult

class BQMatchCreator:

    def __init__(self, all_local_matches: AllMetaLeaderMatches):
        self.meta_leader_matches: dict[MetaFormat, dict[str, list[LimitlessMatch]]] = {}
        for doc in all_local_matches.documents:
            if doc.meta_format not in self.meta_leader_matches:
                self.meta_leader_matches[doc.meta_format] = {}
            self.meta_leader_matches[doc.meta_format][doc.leader_id] = doc.matches
        self.bq_matches: list[BQMatch] = []
        # starts with earliest meta and ends with latest
        self.all_metas = sorted(list(self.meta_leader_matches.keys()))

    @staticmethod
    def limitless_matches2transform_matches(leader_id: str, limitless_matches: list[LimitlessMatch]) -> list[TransformMatch]:
        transform_matches: list[TransformMatch] = []
        for limitless_match in limitless_matches:
            for _ in range(limitless_match.score_win):
                transform_matches.append(TransformMatch(leader_id=leader_id, opponent_id=limitless_match.leader_id, result=MatchResult.WIN))
            for _ in range(limitless_match.score_lose):
                transform_matches.append(TransformMatch(leader_id=leader_id, opponent_id=limitless_match.leader_id, result=MatchResult.LOSE))
            for _ in range(limitless_match.score_draw):
                transform_matches.append(TransformMatch(leader_id=leader_id, opponent_id=limitless_match.leader_id, result=MatchResult.DRAW))


    def transform2BQMatches(self) -> BQMatches:
        for meta_format in self.all_metas:
            leader_matches: dict[str, list[LimitlessMatch]] = self.meta_leader_matches[meta_format]
            for leader_id, limitless_matches in leader_matches.items():
                transform_matches = self.limitless_matches2transform_matches(leader_id, limitless_matches)

        pass



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

