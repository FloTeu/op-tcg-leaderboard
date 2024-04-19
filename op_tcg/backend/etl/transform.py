import copy
import datetime
import random
from datetime import timedelta, datetime
from uuid import uuid4

from op_tcg.backend.models.input import LimitlessLeaderMetaMatches, LimitlessMatch, MetaFormat, AllMetaLeaderMatches
from op_tcg.backend.models.matches import BQMatches, BQMatch, MatchResult
from op_tcg.backend.models.transform import Transform2BQMatch


class BQMatchCreator:

    def __init__(self, all_local_matches: AllMetaLeaderMatches, official: bool):
        self.meta_leader_matches: dict[MetaFormat, dict[str, list[LimitlessMatch]]] = {}
        for doc in all_local_matches.documents:
            if doc.meta_format not in self.meta_leader_matches:
                self.meta_leader_matches[doc.meta_format] = {}
            self.meta_leader_matches[doc.meta_format][doc.leader_id] = doc.matches
        self.bq_matches: list[BQMatch] = []
        # starts with earliest meta and ends with latest
        self.all_metas = sorted(list(self.meta_leader_matches.keys()))
        self.official = official

    @staticmethod
    def limitless_matches2transform_matches(leader_id: str, limitless_matches: list[LimitlessMatch]) -> list[
        Transform2BQMatch]:
        transform_matches: list[Transform2BQMatch] = []
        for limitless_match in limitless_matches:
            # extracts results
            results: list[MatchResult] = []
            for _ in range(limitless_match.score_win):
                results.append(MatchResult.WIN)
            for _ in range(limitless_match.score_lose):
                results.append(MatchResult.LOSE)
            for _ in range(limitless_match.score_draw):
                results.append(MatchResult.DRAW)

            for result in results:
                transform_matches.append(
                    Transform2BQMatch(id=uuid4().hex, leader_id=leader_id, opponent_id=limitless_match.leader_id, result=result))
        return transform_matches

    def transform_matches2bq_matches(self, transform_matches: list[Transform2BQMatch], meta_format: MetaFormat) -> list[BQMatch]:
        bq_matches: list[BQMatch] = []
        match_timestamp_inc = 0
        start_date = meta_format2release_datetime(meta_format)
        for i, transform_match in enumerate(transform_matches):
            timestamp = start_date + timedelta(minutes=match_timestamp_inc)
            bq_matches.append(BQMatch(
                leader_id=transform_match.leader_id,
                opponent_id=transform_match.opponent_id,
                result=transform_match.result,
                meta_format=meta_format,
                official=self.official,
                timestamp=timestamp
            ))
            # after reverse match, we incremente timestamp
            if "reverse_match" in transform_match.id:
                match_timestamp_inc += 1
        return bq_matches


    def transform2BQMatches(self) -> BQMatches:
        bq_matches: list[BQMatch] = []
        for meta_format in self.all_metas:
            print("Transform matches for meta:", meta_format)
            leader_matches: dict[str, list[LimitlessMatch]] = self.meta_leader_matches[meta_format]
            transform_matches: list[Transform2BQMatch] = []
            for leader_id, limitless_matches in leader_matches.items():
                transform_matches.extend(self.limitless_matches2transform_matches(leader_id, limitless_matches))
            sorted_transform_matches = distribute_matches(transform_matches)
            bq_matches.extend(self.transform_matches2bq_matches(sorted_transform_matches, meta_format))
        return BQMatches(matches=bq_matches)



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


def opposite_result(result: MatchResult) -> MatchResult:
    if result == MatchResult.WIN:
        return MatchResult.LOSE
    elif result == MatchResult.LOSE:
        return MatchResult.WIN
    return MatchResult.DRAW


def pick_random_match(matches: list[Transform2BQMatch], leader_id: str, exclude_result: MatchResult = None) -> Transform2BQMatch:
    valid_matches = [match for match in matches if match.leader_id == leader_id and match.result != exclude_result]
    if not valid_matches:
        return None
    chosen_match = random.choice(valid_matches)
    return chosen_match


def distribute_matches(match_pool: list[Transform2BQMatch]) -> list[Transform2BQMatch]:
    """Sorts a list of Transform2BQMatch so that leaders are equally distributed.
        e.g. [Match Leader OP01-001. Match Leader ST13-003, Match Leader OP03-099, ..., Match Leader OP01-001]
    """
    leader_ids = list(set(match.leader_id for match in match_pool))
    result_transform_bq_match = []
    last_results: dict[str, MatchResult | None] = {leader_id: None for leader_id in leader_ids}

    def add_to_result_list(match_to_add: Transform2BQMatch, matches: list[Transform2BQMatch]) -> list[Transform2BQMatch]:
        result_transform_bq_match.append(match_to_add)
        last_results[match_to_add.leader_id] = match_to_add.result
        return [match for match in matches if match.id != match_to_add.id]


    while match_pool:
        # shuffle leader_ids for each iteration
        leader_ids_iteration = copy.deepcopy(leader_ids)
        while len(leader_ids_iteration) > 0:
            # pick a random leader_id
            chosen_leader_id: list[str] = random.choice(leader_ids_iteration)
            if len([match for match in match_pool if match.leader_id == chosen_leader_id]) == 0:
                # leader has no more matches left
                leader_ids_iteration.remove(chosen_leader_id)
                leader_ids.remove(chosen_leader_id)

            chosen_match = pick_random_match(match_pool, chosen_leader_id, exclude_result=last_results[chosen_leader_id])
            if chosen_match:
                match_pool = add_to_result_list(chosen_match, match_pool)
                leader_ids_iteration.remove(chosen_match.leader_id)
                # Find and append the reverse match
                tmp_reverse_match = Transform2BQMatch(
                    id="reverse_match",
                    leader_id=chosen_match.opponent_id,
                    opponent_id=chosen_match.leader_id,
                    result=opposite_result(chosen_match.result)
                )
                first_found_reverse_match = next((match for match in match_pool if
                                                  match.leader_id == tmp_reverse_match.leader_id and
                                                  match.opponent_id == tmp_reverse_match.opponent_id and
                                                  match.result == tmp_reverse_match.result),
                                   None)
                # A reverse match should always exist
                assert first_found_reverse_match != None, "Could not find a reverse match"
                # modify id of reverse match
                first_found_reverse_match.id = f"{first_found_reverse_match.id}_reverse_match"
                match_pool = add_to_result_list(first_found_reverse_match, match_pool)
                try:
                    leader_ids_iteration.remove(chosen_match.opponent_id)
                except ValueError:
                    pass
            else:
                # if no match exist with different result, we switch the result for the next iteration
                if last_results[chosen_leader_id] != MatchResult.DRAW:
                    last_results[chosen_leader_id] = opposite_result(last_results[chosen_leader_id])
                else:
                    last_results[chosen_leader_id] = MatchResult.LOSE

    return result_transform_bq_match

