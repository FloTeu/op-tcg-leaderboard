import copy
import json
import logging
import random
import re
from datetime import timedelta, datetime, date
from urllib.parse import urlparse, parse_qs, unquote
from uuid import uuid4

from op_tcg.backend.models.input import LimitlessMatch, MetaFormat, AllLeaderMetaDocs, meta_format2release_datetime
from op_tcg.backend.models.matches import BQMatches, Match, MatchResult
from op_tcg.backend.models.common import DataSource
from op_tcg.backend.models.cards import OPTcgLanguage, OPTcgMarketplace
from op_tcg.backend.models.cardnexus import CardNexusCardProduct, CardNexusPrice, CardNexusCardProductMapping, \
    CardNexusSealedProduct, CardNexusSealedProductMapping
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


def parse_card_product(product: dict, feed_checksum: str) -> CardNexusCardProduct:
    """Parse one raw CardNexus catalog feed record for a card.

    Only `id` is required; every other field is read defensively since the feed
    schema is still evolving. Raises KeyError if `id` is missing so the caller can
    skip the record — a record without a stable id can't be stored or matched.
    """
    product_id = product["id"]
    expansion_id = product.get("expansionId")
    return CardNexusCardProduct(
        product_id=str(product_id),
        print_number=product.get("printNumber"),
        name=product.get("name"),
        expansion_id=None if expansion_id is None else str(expansion_id),
        expansion_slug=product.get("expansionSlug"),
        feed_checksum=feed_checksum,
        raw_json=json.dumps(product, default=str),
    )


def parse_sealed_product(product: dict, feed_checksum: str) -> CardNexusSealedProduct:
    """Parse one raw CardNexus catalog feed record for a non-card (sealed) product.

    Unlike cards, sealed products aren't matched against our own tables — CardNexus's
    own catalog fields (name, expansionSlug, productCategory) are kept largely as-is.
    Only `id` is required; raises KeyError if missing so the caller can skip the record.
    """
    product_id = product["id"]
    expansion_id = product.get("expansionId")
    return CardNexusSealedProduct(
        product_id=str(product_id),
        name=product.get("name"),
        expansion_id=None if expansion_id is None else str(expansion_id),
        expansion_slug=product.get("expansionSlug"),
        product_category=product.get("productCategory"),
        image_url=product.get("imageUrl"),
        feed_checksum=feed_checksum,
        raw_json=json.dumps(product, default=str),
    )


# CardNexus language codes -> our tracked OPTcgLanguage. CardNexus lists several
# languages we don't track (fr, ko, zh-cn) on the same product — those are ignored.
CARDNEXUS_LANGUAGE_MAP: dict[str, OPTcgLanguage] = {
    "en": OPTcgLanguage.EN,
    "ja": OPTcgLanguage.JP,
}


_TCGPLAYER_PRODUCT_PATH_RE = re.compile(r"/product/(\d+)")
_TCGPLAYER_LEADING_ID_RE = re.compile(r"^(\d+)")


def extract_tcgplayer_product_id(url: str) -> str | None:
    """Extract the numeric TCGplayer product id from a limitlesstcg TCGplayer
    affiliate link (our own CardMarketplaceUrl.url for marketplace=tcgplayer).

    Two shapes seen in the wild: a full nested TCGplayer url in the `u` query
    param (`...?u=https%3A%2F%2Fwww.tcgplayer.com%2Fproduct%2F544530%2F...`), or
    a short form where `u` is just `<id>-<slug>` (`...?u=685325-eb04-054`).
    """
    u_values = parse_qs(urlparse(url).query).get("u")
    if not u_values:
        return None
    u = unquote(u_values[0])
    match = _TCGPLAYER_PRODUCT_PATH_RE.search(u)
    if match:
        return match.group(1)
    match = _TCGPLAYER_LEADING_ID_RE.match(u)
    return match.group(1) if match else None


def build_tcgplayer_id_lookup(marketplace_urls: list[dict]) -> dict[str, list[tuple[str, OPTcgLanguage, int]]]:
    """Build a TCGplayer product id -> [(card_id, language, aa_version), ...] lookup
    from our own CardMarketplaceUrl rows (marketplace='tcgplayer'), for exact-id
    matching against the CardNexus catalog feed (see resolve_product_mapping_by_tcgplayer_id).

    `marketplace_urls` is a list of {"card_id", "language", "aa_version", "url"} records.
    Rows whose url doesn't yield a parseable TCGplayer id are skipped.
    """
    lookup: dict[str, list[tuple[str, OPTcgLanguage, int]]] = {}
    for row in marketplace_urls:
        tcgplayer_id = extract_tcgplayer_product_id(row["url"])
        if tcgplayer_id is None:
            continue
        lookup.setdefault(tcgplayer_id, []).append(
            (row["card_id"], OPTcgLanguage(row["language"]), int(row["aa_version"]))
        )
    return lookup


def extract_cardnexus_external_ids_by_finish(product: dict, marketplace: str) -> dict[str | None, str]:
    """Pull the numeric product ids CardNexus lists for a catalog record under
    `externalIds.<marketplace>`, keyed by finish (e.g. 'Standard', 'Foil').

    Usually a single entry, but foil/parallel finishes can be split across separate
    marketplace listings, each with their own id.
    """
    entries = (product.get("externalIds") or {}).get(marketplace) or []
    return {entry.get("finish"): str(entry["id"]) for entry in entries if entry.get("id") is not None}


def extract_cardnexus_tcgplayer_ids(product: dict) -> list[str]:
    """Pull the TCGplayer numeric product ids CardNexus lists for a catalog record
    (`externalIds.tcgplayer`). Usually a single id, but all listed ids are tried as
    match candidates in case finishes are split across separate TCGplayer listings.
    """
    return list(extract_cardnexus_external_ids_by_finish(product, "tcgplayer").values())


def resolve_product_mapping_by_tcgplayer_id(
    product: dict,
    tcgplayer_id_to_cards: dict[str, list[tuple[str, OPTcgLanguage, int]]],
) -> list[CardNexusCardProductMapping]:
    """Resolve one CardNexus catalog product to zero or more CardNexusCardProductMapping
    rows by exact TCGplayer product id, rather than guessing from expansion/variant
    metadata (the old Jaccard release-set match + variant-field disambiguation).

    TCGplayer ids are already unique per exact (card_id, language, aa_version) print
    on our side — a card's base print and its alternate-art/manga-art parallels each
    get their own TCGplayer id — so a direct id match resolves card identity, language,
    and aa_version disambiguation in one step, and naturally recovers the correct
    language(s) instead of assuming every language CardNexus lists for a product
    shares the same card_id/aa_version.

    One row is produced per language the product lists that we track (see
    CARDNEXUS_LANGUAGE_MAP) — a product with no recognized language yields no rows.
    Each row also carries the tcgplayer_id/cardmarket_id for its finish (matched off
    the same finish key, falling back to the first listed cardmarket id), so a direct
    Cardmarket/TCGplayer product link can be built straight from the mapping table.
    """
    product_id = str(product.get("id"))
    recognized_languages = [
        CARDNEXUS_LANGUAGE_MAP[lang] for lang in product.get("languages") or [] if lang in CARDNEXUS_LANGUAGE_MAP
    ]
    if not recognized_languages:
        return []

    tcgplayer_by_finish = extract_cardnexus_external_ids_by_finish(product, "tcgplayer")
    cardmarket_by_finish = extract_cardnexus_external_ids_by_finish(product, "cardmarket")
    fallback_cardmarket_id = next(iter(cardmarket_by_finish.values()), None)

    if not tcgplayer_by_finish:
        return [
            CardNexusCardProductMapping(
                product_id=product_id, language=language, matched=False, match_method="no_external_id",
                cardmarket_id=fallback_cardmarket_id,
            )
            for language in recognized_languages
        ]

    seen: set[tuple[OPTcgLanguage, str, int]] = set()
    matches: list[CardNexusCardProductMapping] = []
    for finish, tcgplayer_id in tcgplayer_by_finish.items():
        cardmarket_id = cardmarket_by_finish.get(finish, fallback_cardmarket_id)
        for card_id, language, aa_version in tcgplayer_id_to_cards.get(tcgplayer_id, []):
            if language not in recognized_languages:
                continue
            key = (language, card_id, aa_version)
            if key in seen:
                continue
            seen.add(key)
            matches.append(CardNexusCardProductMapping(
                product_id=product_id, language=language, card_id=card_id, aa_version=aa_version,
                tcgplayer_id=tcgplayer_id, cardmarket_id=cardmarket_id,
                matched=True, match_method="tcgplayer_id",
            ))

    matched_languages = {m.language for m in matches}
    fallback_tcgplayer_id = next(iter(tcgplayer_by_finish.values()), None)
    unmatched = [
        CardNexusCardProductMapping(
            product_id=product_id, language=language, matched=False, match_method="no_match",
            tcgplayer_id=fallback_tcgplayer_id, cardmarket_id=fallback_cardmarket_id,
        )
        for language in recognized_languages if language not in matched_languages
    ]
    return matches + unmatched


_CARDMARKET_IMAGE_ID_RE = re.compile(r"/(\d+)\.\w+$")


def extract_cardmarket_id_from_image_url(image_url: str) -> str | None:
    """Extract the numeric Cardmarket product id from a Cardmarket CDN image url
    (our own SealedProduct.image_url for marketplace=cardmarket).

    Cardmarket's own S3 image paths always end in `<idProduct>.<ext>`
    (e.g. `product-images.s3.cardmarket.com/5/LOB/577919/577919.jpg`).
    """
    match = _CARDMARKET_IMAGE_ID_RE.search(image_url)
    return match.group(1) if match else None


def build_cardmarket_sealed_id_lookup(sealed_products: list[dict]) -> dict[str, list[tuple[str, OPTcgLanguage]]]:
    """Build a Cardmarket product id -> [(sealed_product_id, language), ...] lookup
    from our own SealedProduct rows (marketplace='cardmarket'), for exact-id matching
    against the CardNexus sealed catalog (see resolve_sealed_product_mapping_by_cardmarket_id).

    `sealed_products` is a list of {"id", "language", "image_url"} records. Rows with
    no image_url, or one that doesn't yield a parseable Cardmarket id, are skipped.
    """
    lookup: dict[str, list[tuple[str, OPTcgLanguage]]] = {}
    for row in sealed_products:
        image_url = row.get("image_url")
        if not image_url:
            continue
        cardmarket_id = extract_cardmarket_id_from_image_url(image_url)
        if cardmarket_id is None:
            continue
        lookup.setdefault(cardmarket_id, []).append((row["id"], OPTcgLanguage(row["language"])))
    return lookup


def resolve_sealed_product_mapping_by_cardmarket_id(
    product: dict,
    cardmarket_id_to_sealed: dict[str, list[tuple[str, OPTcgLanguage]]],
) -> CardNexusSealedProductMapping:
    """Resolve one CardNexus sealed catalog product to our own cardmarket-scraped
    SealedProduct table by exact numeric Cardmarket product id — the one id both
    catalogs share for sealed products (unlike cards, sealed products have no
    print_number to match on).

    Only the first listed Cardmarket id/candidate is used: CardNexus bundles all print
    languages of a sealed product under a single external id rather than listing one
    per language, so there's nothing to disambiguate multiple candidates by.
    """
    product_id = str(product.get("id"))
    tcgplayer_ids = extract_cardnexus_tcgplayer_ids(product)
    tcgplayer_id = tcgplayer_ids[0] if tcgplayer_ids else None
    cardmarket_ids = list(extract_cardnexus_external_ids_by_finish(product, "cardmarket").values())
    cardmarket_id = cardmarket_ids[0] if cardmarket_ids else None

    if cardmarket_id is None:
        return CardNexusSealedProductMapping(
            product_id=product_id, tcgplayer_id=tcgplayer_id, matched=False, match_method="no_external_id",
        )

    candidates = cardmarket_id_to_sealed.get(cardmarket_id, [])
    if not candidates:
        return CardNexusSealedProductMapping(
            product_id=product_id, tcgplayer_id=tcgplayer_id, cardmarket_id=cardmarket_id,
            matched=False, match_method="no_match",
        )

    sealed_product_id, language = candidates[0]
    return CardNexusSealedProductMapping(
        product_id=product_id, sealed_product_id=sealed_product_id, language=language,
        tcgplayer_id=tcgplayer_id, cardmarket_id=cardmarket_id,
        matched=True, match_method="cardmarket_id",
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


def flatten_price_snapshot(product_id: str, prices_response: dict, as_of: date | None = None) -> list[CardNexusPrice]:
    """Flatten a raw /products/{id}/prices (current-price) response into one row per
    finish/marketplace, dated `as_of` (defaults to today).

    This is the "keep it current going forward" half of CardNexusPriceHistory: rows
    are upserted by the caller, so repeated same-day pulls overwrite today's row
    rather than accumulating duplicates. Unknown marketplace keys are logged and
    skipped rather than raising, since the CardNexus API may add new pricing
    sources without notice.
    """
    as_of = as_of or date.today()
    rows: list[CardNexusPrice] = []
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
            rows.append(CardNexusPrice(
                product_id=product_id,
                finish=finish,
                marketplace=marketplace_enum,
                date=as_of,
                raw_json=json.dumps(block, default=str),
                **_extract_price_block_fields(marketplace, block),
            ))
    return rows


# CardNexus's /prices/history marketplace values -> the currency that marketplace
# always reports in (per docs). History day-records don't include currency directly.
_HISTORY_MARKETPLACE_CURRENCY: dict[str, str] = {
    "cardmarket": "EUR",
    "tcgplayer": "USD",
}


def flatten_price_history(product_id: str, history_response: dict) -> list[CardNexusPrice]:
    """Flatten a raw /products/{id}/prices/history response into one row per day.

    This is the "backfill past dates" half of CardNexusPriceHistory. Unlike the
    current-price endpoint, history rows are already flat ({date, marketplace,
    finish, low, mid, high, marketValue}) — only cardmarket/tcgplayer are ever
    returned here (no 'cardnexus' marketplace for history, per the API docs).
    """
    rows: list[CardNexusPrice] = []
    for day in history_response.get("data") or []:
        marketplace_raw = day.get("marketplace")
        try:
            marketplace_enum = OPTcgMarketplace(marketplace_raw)
        except ValueError:
            logger.warning("Unknown CardNexus marketplace '%s' for product %s history — skipping", marketplace_raw, product_id)
            continue
        try:
            day_date = datetime.strptime(day["date"], "%Y-%m-%d").date()
        except (KeyError, ValueError) as e:
            logger.warning("Skipping malformed CardNexus history day for product %s: %s", product_id, e)
            continue
        rows.append(CardNexusPrice(
            product_id=product_id,
            marketplace=marketplace_enum,
            finish=day.get("finish") or "Standard",
            date=day_date,
            currency=_HISTORY_MARKETPLACE_CURRENCY.get(marketplace_raw),
            low=day.get("low"),
            mid=day.get("mid"),
            high=day.get("high"),
            market_value=day.get("marketValue"),
            raw_json=json.dumps(day, default=str),
        ))
    return rows
