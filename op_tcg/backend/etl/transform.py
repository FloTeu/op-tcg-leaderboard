import copy
import json
import logging
import random
from datetime import timedelta, datetime
from uuid import uuid4

from op_tcg.backend.models.input import LimitlessMatch, MetaFormat, AllLeaderMetaDocs, meta_format2release_datetime
from op_tcg.backend.models.matches import BQMatches, Match, MatchResult
from op_tcg.backend.models.common import DataSource
from op_tcg.backend.models.cards import OPTcgLanguage, OPTcgMarketplace
from op_tcg.backend.models.cardnexus import CardNexusCatalogProduct, CardNexusPriceSnapshot, CardNexusProductMapping
from op_tcg.backend.models.transform import Transform2BQMatch

logger = logging.getLogger(__name__)


class BQMatchCreator:

    def __init__(self, all_local_matches: AllLeaderMetaDocs, official: bool):
        self.meta_leader_matches: dict[MetaFormat, dict[str, list[LimitlessMatch]]] = {}
        self.meta_leader_ids: dict[MetaFormat, str] = {}
        for doc in all_local_matches.documents:
            if doc.meta_format not in self.meta_leader_matches:
                self.meta_leader_matches[doc.meta_format] = {}
            self.meta_leader_matches[doc.meta_format][doc.leader_id] = doc.matches
        self.bq_matches: list[Match] = []
        # starts with earliest meta and ends with latest
        self.all_metas = sorted(list(self.meta_leader_matches.keys()))
        for meta_format in self.all_metas:
            self.meta_leader_ids[meta_format] = list(self.meta_leader_matches[meta_format].keys())
        self.official = official

        # remove matches with not yet existent leader_ids
        for meta_format, leader_id2limitless_matches in self.meta_leader_matches.items():
            for leader_id, limitless_matches in leader_id2limitless_matches.items():
                self.meta_leader_matches[meta_format][leader_id] = [match for match in limitless_matches if
                                                                    match.leader_id in self.meta_leader_ids[
                                                                        meta_format]]

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
                    Transform2BQMatch(id=uuid4().hex, is_reverse=False, leader_id=leader_id,
                                      opponent_id=limitless_match.leader_id, result=result))
        return transform_matches

    def transform_matches2bq_matches(self, transform_matches: list[Transform2BQMatch], meta_format: MetaFormat) -> list[
        Match]:
        bq_matches: list[Match] = []
        match_timestamp_inc = 0
        start_date = meta_format2release_datetime(meta_format)
        for i, transform_match in enumerate(transform_matches):
            match_timestamp = start_date + timedelta(minutes=match_timestamp_inc)
            bq_matches.append(Match(
                id=transform_match.id,
                leader_id=transform_match.leader_id,
                opponent_id=transform_match.opponent_id,
                result=transform_match.result,
                meta_format=meta_format,
                official=self.official,
                is_reverse=transform_match.is_reverse,
                source=DataSource.LIMITLESS,
                match_timestamp=match_timestamp
            ))
            # after reverse match, we incremente timestamp
            if transform_match.is_reverse:
                match_timestamp_inc += 1
        return bq_matches

    def transform2BQMatches(self) -> BQMatches:
        bq_matches: list[Match] = []
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


def meta_format2approximate_datetime(meta_format: MetaFormat) -> datetime:
    # expect tournaments starting half a month after release of new set
    return meta_format2release_datetime(meta_format) + timedelta(days=15)


def opposite_result(result: MatchResult) -> MatchResult:
    if result == MatchResult.WIN:
        return MatchResult.LOSE
    elif result == MatchResult.LOSE:
        return MatchResult.WIN
    return MatchResult.DRAW


def pick_random_match(matches: list[Transform2BQMatch], leader_id: str,
                      exclude_result: MatchResult = None) -> Transform2BQMatch:
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

    def add_to_result_list(match_to_add: Transform2BQMatch, matches: list[Transform2BQMatch]) -> list[
        Transform2BQMatch]:
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

            chosen_match = pick_random_match(match_pool, chosen_leader_id,
                                             exclude_result=last_results[chosen_leader_id])
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
                if first_found_reverse_match == None:
                    raise ValueError("Could not find a reverse match")

                # modify id of reverse match
                first_found_reverse_match.id = chosen_match.id
                first_found_reverse_match.is_reverse = True
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


def parse_catalog_product(product: dict, feed_checksum: str) -> CardNexusCatalogProduct:
    """Parse one raw CardNexus catalog feed record.

    Only `id` is required; every other field is read defensively since the feed
    schema is still evolving. Raises KeyError if `id` is missing so the caller can
    skip the record — a record without a stable id can't be stored or matched.
    """
    product_id = product["id"]
    expansion_id = product.get("expansionId")
    return CardNexusCatalogProduct(
        product_id=str(product_id),
        print_number=product.get("printNumber"),
        name=product.get("name"),
        expansion_id=None if expansion_id is None else str(expansion_id),
        expansion_slug=product.get("expansionSlug"),
        feed_checksum=feed_checksum,
        raw_json=json.dumps(product, default=str),
    )


def match_catalog_product_to_card(product_id: str, print_number: str | None,
                                  cards_by_id: dict[str, list[tuple[OPTcgLanguage, int]]]) -> CardNexusProductMapping:
    """Match a CardNexus product to our own Card table via print_number == Card.id.

    `cards_by_id` maps Card.id -> list of (language, aa_version) of every existing
    Card row sharing that id. CardNexus does not expose language/aa_version
    directly, so if more than one (language, aa_version) shares the same id, the
    match is kept but marked ambiguous rather than guessed.
    """
    if not print_number:
        return CardNexusProductMapping(product_id=product_id, matched=False, match_method="no_print_number")

    candidates = cards_by_id.get(print_number, [])
    if len(candidates) == 0:
        return CardNexusProductMapping(product_id=product_id, matched=False, match_method="no_match")
    if len(candidates) > 1:
        return CardNexusProductMapping(product_id=product_id, matched=False, match_method="ambiguous_print_number")

    language, aa_version = candidates[0]
    return CardNexusProductMapping(
        product_id=product_id,
        card_id=print_number,
        language=language,
        aa_version=aa_version,
        matched=True,
        match_method="print_number_unique",
    )


def _extract_price_block_fields(marketplace: str, block: dict) -> dict:
    """Extract low/mid/high/market_value/currency from a marketplace price block.

    The 'cardnexus' marketplace block has a different shape (low is a
    {amount, currency} object, no mid/high/marketValue) than cardmarket/tcgplayer.
    """
    if marketplace == OPTcgMarketplace.CARD_NEXUS.value:
        low_obj = block.get("low") or {}
        return {
            "currency": low_obj.get("currency"),
            "low": low_obj.get("amount"),
            "mid": None,
            "high": None,
            "market_value": None,
        }
    return {
        "currency": block.get("currency"),
        "low": block.get("low"),
        "mid": block.get("mid"),
        "high": block.get("high"),
        "market_value": block.get("marketValue"),
    }


def flatten_price_snapshot(product_id: str, prices_response: dict) -> list[CardNexusPriceSnapshot]:
    """Flatten a raw /products/{id}/prices response into one row per finish/marketplace.

    Unknown marketplace keys are logged and skipped rather than raising, since the
    CardNexus API may add new pricing sources without notice.
    """
    snapshots: list[CardNexusPriceSnapshot] = []
    prices_by_finish = prices_response.get("pricesByFinish") or {}
    for finish, marketplaces in prices_by_finish.items():
        if not isinstance(marketplaces, dict):
            continue
        for marketplace, block in marketplaces.items():
            if not block:
                continue
            try:
                marketplace_enum = OPTcgMarketplace(marketplace)
            except ValueError:
                logger.warning("Unknown CardNexus marketplace '%s' for product %s — skipping", marketplace, product_id)
                continue
            snapshots.append(CardNexusPriceSnapshot(
                product_id=product_id,
                finish=finish,
                marketplace=marketplace_enum,
                raw_json=json.dumps(block, default=str),
                **_extract_price_block_fields(marketplace, block),
            ))
    return snapshots
