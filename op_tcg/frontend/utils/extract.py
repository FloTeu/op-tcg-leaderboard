import logging
import os
from collections import Counter, defaultdict

from cachetools import TTLCache, cached

from op_tcg.backend.etl.load import get_or_create_table, table_exists
from op_tcg.backend.models.bq_classes import BQTableBaseModel
from op_tcg.backend.models.cards import LatestCardPrice, CardPopularity, Card, CardReleaseSet, ExtendedCardData, \
    CardCurrency, CardPrice, OPTcgLanguage, CardMarketplaceUrl
from op_tcg.backend.models.decklists import Decklist
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.leader import Leader, TournamentWinner, LeaderElo, LeaderExtended
from op_tcg.backend.models.matches import Match, LeaderWinRate
from op_tcg.backend.models.tournaments import TournamentStanding, Tournament, TournamentStandingExtended, \
    TournamentDecklist, TournamentExtended
from op_tcg.backend.utils.utils import timeit
from op_tcg.frontend.utils.card_price import get_decklist_price
from op_tcg.frontend.utils.utils import run_bq_query



def get_bq_table_id(table: type[BQTableBaseModel]) -> str:
    # Get project ID from environment variable
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is not set")
    return f'{project_id}.{table.get_dataset_id()}.{table.__tablename__}'

def get_leader_data() -> list[Leader]:
    # Leader data is relatively static - cache for 24 hours
    leader_data_rows = run_bq_query(f"""SELECT * FROM `{get_bq_table_id(Leader)}`""", ttl_hours=24.0)
    bq_leaders = [Leader(**d) for d in leader_data_rows]
    return bq_leaders


def get_leader_win_rate(meta_formats: list[MetaFormat], leader_ids: list[str] | None = None) -> list[LeaderWinRate]:
    bq_win_rates: list[LeaderWinRate] = []
    for meta_format in meta_formats:
        # Win rates update daily - cache for 6 hours (default)
        win_rate_data_rows = run_bq_query(f"""SELECT * FROM `{get_bq_table_id(LeaderWinRate)}` where meta_format = '{meta_format}'""", ttl_hours=24.0)
        bq_win_rates.extend([LeaderWinRate(**d) for d in win_rate_data_rows])

    if leader_ids:
        return [bqwr for bqwr in bq_win_rates if (bqwr.leader_id in leader_ids)]
    else:
        return bq_win_rates

def get_leader_extended(meta_formats: list[MetaFormat] | None = None, leader_ids: list[str] | None = None, meta_format_region: MetaFormatRegion = MetaFormatRegion.ALL, only_official: bool | None = None) -> list[LeaderExtended]:
    # ensure only available meta formats are used per default
    meta_formats = meta_formats or MetaFormat.to_list()
    bq_leader_data: list[LeaderExtended] = []
    # Extended leader data is computed, cache for 6 hours (default)
    leader_data_rows = run_bq_query(
        f"""SELECT * FROM `{get_bq_table_id(LeaderExtended)}`""", ttl_hours=6.0)
    bq_leader_data.extend([LeaderExtended(**d) for d in leader_data_rows])

    # Apply filters
    if leader_ids:
        bq_leader_data = [bql for bql in bq_leader_data if (bql.id in leader_ids)]
    if meta_format_region:
        bq_leader_data = [bql for bql in bq_leader_data if (bql.meta_format_region == meta_format_region)]
    if meta_formats:
        bq_leader_data = [bql for bql in bq_leader_data if (bql.meta_format in meta_formats)]
    if only_official is not None:
        bq_leader_data = [l for l in bq_leader_data if l.only_official == only_official]

    return bq_leader_data


def get_tournament_decklist_data(meta_formats: list[MetaFormat], leader_ids: list[str] | None = None, meta_format_region: MetaFormatRegion = MetaFormatRegion.ALL) -> list[TournamentDecklist]:
    leader_ids = leader_ids or []
    bq_decklists = get_all_tournament_decklist_data()
    if leader_ids:
        bq_decklists = [ts for ts in bq_decklists if ts.leader_id in leader_ids]
    if meta_formats:
        bq_decklists = [ts for ts in bq_decklists if ts.meta_format in meta_formats]
    if meta_format_region != MetaFormatRegion.ALL:
        bq_decklists = [ts for ts in bq_decklists if ts.meta_format_region == meta_format_region]
    return bq_decklists

@cached(cache=TTLCache(maxsize=1024, ttl=60*60*24))
def get_all_tournament_decklist_data() -> list[TournamentDecklist]:
    """Function is cached since data processing is expensive."""
    card_id2card_data = get_card_id_card_data_lookup()
    # cached for each session
    tournament_standing_rows = run_bq_query(f"""
SELECT COALESCE(t1.leader_id,t3.leader_id) as leader_id, t1.tournament_id, COALESCE(t3.decklist, t1.decklist) AS decklist, t1.placing, t1.player_id, t2.meta_format, COALESCE(t2.meta_format_region, 'west') AS meta_format_region , t2.tournament_timestamp 
FROM `{get_bq_table_id(TournamentStanding)}` t1
left join `{get_bq_table_id(Tournament)}` t2 on t1.tournament_id = t2.id
left join `{get_bq_table_id(Decklist)}` t3 on t1.decklist_id = t3.id
where
t1.decklist IS NOT NULL 
OR t3.decklist IS NOT NULL""", ttl_hours=None)
    tournament_decklists: list[TournamentDecklist] = []
    leader_ids = [l.id for l in get_leader_data()]
    seen_decklists = set()
    # To track unique combinations of leader_id, tournament_id, player_id, and placing
    for ts in tournament_standing_rows:
        key = (ts['leader_id'], ts['tournament_id'], ts['player_id'], ts['placing'])
        if key not in seen_decklists:
            tournament_decklist = TournamentDecklist(**ts)
            tournament_decklist.price_usd = get_decklist_price(tournament_decklist.decklist, card_id2card_data, currency=CardCurrency.US_DOLLAR)
            tournament_decklist.price_eur = get_decklist_price(tournament_decklist.decklist, card_id2card_data, currency=CardCurrency.EURO)
            tournament_decklists.append(tournament_decklist)
            seen_decklists.add(key)  # Mark this combination as seen
    return tournament_decklists

@timeit
def get_all_tournament_extened_data(meta_formats: list[MetaFormat] | None = None) -> list[TournamentExtended]:
    tournament_extended_rows = run_bq_query(f"""SELECT * FROM `{get_bq_table_id(TournamentExtended)}` order by tournament_timestamp desc""", ttl_hours=24.0)
    tournaments: list[TournamentExtended] = []
    for te in tournament_extended_rows:
        tournaments.append(TournamentExtended(**te))

    if meta_formats:
        tournaments = [t for t in tournaments if t.meta_format in meta_formats]
    return tournaments


def get_card_data(default_language: OPTcgLanguage = OPTcgLanguage.EN) -> list[LatestCardPrice]:
    # default to english, but if card_id has not english language, the japanese version is used
    latest_card_rows = run_bq_query(
            f"""WITH ranked_cards AS (
                SELECT t0.*, t1.* except(id, name, language, create_timestamp), t1.name as release_set_name,
                       ROW_NUMBER() OVER (PARTITION BY t0.id, t0.aa_version ORDER BY 
                           CASE WHEN t0.language = '{default_language}' THEN 1 ELSE 2 END) as rn
                FROM `{get_bq_table_id(LatestCardPrice)}` t0
                LEFT JOIN `{get_bq_table_id(CardReleaseSet)}` t1 on t0.release_set_id = t1.id and t0.language = t1.language
            ),
            marketplace_urls AS (
              SELECT 
                card_id, 
                language, 
                aa_version,
                MAX(CASE WHEN marketplace = 'cardmarket' THEN url END) as marketplace_url_cardmarket,
                MAX(CASE WHEN marketplace = 'tcgplayer' THEN url END) as marketplace_url_tcg_player
              FROM `{get_bq_table_id(CardMarketplaceUrl)}`
              GROUP BY card_id, language, aa_version
            )
            SELECT rc.* except(rn), mu.marketplace_url_cardmarket, mu.marketplace_url_tcg_player 
            FROM ranked_cards rc
            LEFT JOIN marketplace_urls mu
                ON rc.id = mu.card_id 
                AND rc.language = mu.language 
                AND rc.aa_version = mu.aa_version
            WHERE rc.rn = 1
    """, ttl_hours=24.0)
    return [ExtendedCardData(**d) for d in latest_card_rows]

def get_card_popularity_data() -> list[CardPopularity]:
    # Card popularity is computed daily - cache for 24 hours
    latest_card_rows = run_bq_query(
            f"""SELECT * FROM `{get_bq_table_id(CardPopularity)}`""", ttl_hours=24.0)
    return [CardPopularity(**d) for d in latest_card_rows]

def get_card_popularity_by_meta(card_id: str, until_meta_format: MetaFormat | None = None) -> dict[MetaFormat, float]:
    card_popularity_by_meta: dict[MetaFormat, float] = {}
    card_colors = get_card_id_card_data_lookup().get(card_id).colors
    card_popularities = [cpd for cpd in get_card_popularity_data() if cpd.card_id == card_id]
    for meta_format in MetaFormat.to_list(until_meta_format=until_meta_format):
        card_popularities_in_meta = [cp for cp in card_popularities if cp.meta_format == meta_format and cp.color in card_colors]
        if len(card_popularities_in_meta) > 0:
            # take the maximum popularity if card is played in multi colored decks
            max_popularity = max([cp.popularity for cp in card_popularities_in_meta])
            card_popularity_by_meta[meta_format] = max_popularity
        else:
            card_popularity_by_meta[meta_format] = 0.0
    return card_popularity_by_meta

def get_meta_format_to_num_decklists() -> dict[MetaFormat, int]:
    decklists = get_all_tournament_decklist_data()
    # Use a Counter to count occurrences of each meta_format
    meta_format_counter = Counter(decklist.meta_format for decklist in decklists)
    return dict(meta_format_counter)

def get_card_types() -> list[str]:
    latest_card_rows = run_bq_query(
            f"""SELECT DISTINCT(types) FROM `{get_bq_table_id(Card)}` c, UNNEST(c.types) AS types """, ttl_hours=24.0)
    return [d["types"] for d in latest_card_rows]


def get_card_id_card_data_lookup(aa_version: int = 0, ensure_latest_price_not_null=True, default_language: OPTcgLanguage = OPTcgLanguage.EN) -> dict[str, ExtendedCardData]:
    card_data = get_card_data()
    card_data = [cdata for cdata in card_data if cdata.aa_version == aa_version]
    if ensure_latest_price_not_null:
        for cdata in card_data:
            cdata.ensure_latest_price_not_none()    
    return {card.id: card for card in card_data}

def get_tournament_match_data(tournament_id: str, leader_id: str | None = None) -> list[Match]:
    """Get all matches for a specific tournament, optionally filtered by leader_id
    
    Args:
        tournament_id: The tournament ID to get matches for
        leader_id: Optional leader ID to filter matches for a specific leader
        meta_formats: Optional meta formats to filter by
        
    Returns:
        List of Match objects sorted by round, phase, and timestamp
    """
    base_query = f"""
    SELECT * FROM `{get_bq_table_id(Match)}` 
    WHERE tournament_id = '{tournament_id}'
    ORDER BY tournament_round ASC, tournament_phase ASC, match_timestamp ASC
    """
    
    match_data_rows = run_bq_query(base_query)
    matches = [Match(**d) for d in match_data_rows]
    if leader_id:
        matches = [m for m in matches if m.leader_id == leader_id]
    
    return matches


# --------------- Price overview extraction helpers ---------------
def get_price_change_data(days: int, currency: CardCurrency, min_latest_price: float, max_latest_price: float,
                          page: int, page_size: int, order_dir: str = "DESC", include_alt_art: bool = False, change_metric: str = "absolute") -> list[dict]:
    """Return price changes over a window for cards, ordered by percentage change.

    Args:
        days: Lookback window in days
        currency: EUR or USD
        min_latest_price: minimum latest price filter
        max_latest_price: maximum latest price filter
        limit: number of rows
        order: 'pct_change DESC' or 'pct_change ASC'
    """
    latest_tbl = get_bq_table_id(LatestCardPrice).replace(":", ".")
    history_tbl = get_bq_table_id(CardPrice).replace(":", ".")
    currency_col = 'latest_eur_price' if currency == CardCurrency.EURO else 'latest_usd_price'
    price_currency = CardCurrency.EURO if currency == CardCurrency.EURO else CardCurrency.US_DOLLAR
    aa_filter = "" if include_alt_art else "AND aa_version = 0"
    # max_latest_price is already normalized by pydantic: None means unbounded
    upper_bound = f"AND {currency_col} <= {max_latest_price}" if max_latest_price is not None else ""
    # ORDER BY expression
    order_expr = "IFNULL(abs_change, 0)" if change_metric == "absolute" else "IFNULL(pct_change, 0)"
    order_dir = order_dir if order_dir in ("ASC", "DESC") else "DESC"
    offset = max(0, (page - 1) * page_size)
    fetch_count = page_size + 1  # fetch one extra to detect has_more
    query = f"""
    WITH history_window AS (
      SELECT card_id, language, aa_version, price, create_timestamp,
             ROW_NUMBER() OVER (PARTITION BY card_id, language, aa_version ORDER BY create_timestamp ASC) AS rn
      FROM `{history_tbl}`
      WHERE create_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
        AND currency = '{price_currency}'
        AND language = 'en'
        {aa_filter}
    ),
    base_price AS (
      SELECT card_id, language, aa_version, price AS window_price
      FROM history_window
      WHERE rn = 1
    ),
    latest AS (
      SELECT id AS card_id, language, aa_version, name, image_url, {currency_col} AS latest_price
      FROM `{latest_tbl}`
      WHERE {currency_col} IS NOT NULL
        AND {currency_col} >= {min_latest_price}
        {upper_bound}
        {aa_filter}
    )
    SELECT l.card_id, l.language, l.aa_version, l.name, l.image_url, l.latest_price,
           b.window_price,
           SAFE_DIVIDE(l.latest_price - b.window_price, NULLIF(b.window_price, 0)) AS pct_change,
           (l.latest_price - b.window_price) AS abs_change
    FROM latest l
    LEFT JOIN base_price b
      ON l.card_id = b.card_id AND l.language = b.language AND l.aa_version = b.aa_version
    ORDER BY {order_expr} {order_dir}
    LIMIT {fetch_count}
    OFFSET {offset}
    """
    rows = run_bq_query(query, ttl_hours=24.0)
    return rows


def get_top_current_prices(
    currency: CardCurrency,
    page: int,
    page_size: int,
    min_latest_price: float,
    max_latest_price: float,
    direction: str = "DESC",
    language: str = 'en',
    include_alt_art: bool = False
) -> list[dict]:
    """Return cards by current latest price in the selected currency."""
    latest_tbl = get_bq_table_id(LatestCardPrice).replace(":", ".")
    currency_col = 'latest_eur_price' if currency == CardCurrency.EURO else 'latest_usd_price'
    aa_filter = "" if include_alt_art else "AND aa_version = 0"
    offset = max(0, (page - 1) * page_size)
    fetch_count = page_size + 1
    upper_bound = f"AND {currency_col} <= {max_latest_price}" if max_latest_price is not None else ""
    query = f"""
    SELECT id AS card_id, language, aa_version, name, image_url, {currency_col} AS latest_price,
           NULL AS window_price, NULL AS pct_change, NULL AS abs_change
    FROM `{latest_tbl}`
    WHERE language = '{language}' {aa_filter} AND {currency_col} IS NOT NULL
      AND {currency_col} >= {min_latest_price}
      {upper_bound}
    ORDER BY {currency_col} {direction}
    LIMIT {fetch_count}
    OFFSET {offset}
    """
    return run_bq_query(query, ttl_hours=24.0)


def get_card_price_development_data(card_id: str, days: int = 90, include_alt_art: bool = False, aa_version: int | None = None) -> dict[str, list[dict]]:
    """
    Get historical price development data for a specific card in both EUR and USD.
    
    Args:
        card_id: The card ID to get price history for
        days: Number of days to look back (default: 90)
        include_alt_art: Whether to include alt art versions
        aa_version: Specific alt art version to filter by (optional)

    Returns:
        Dictionary with 'eur' and 'usd' keys containing lists of price data points
    """
    history_tbl = get_bq_table_id(CardPrice).replace(":", ".")

    if aa_version is not None:
        aa_filter = f"AND aa_version = {aa_version}"
    else:
        aa_filter = "" if include_alt_art else "AND aa_version = 0"

    query = f"""
    WITH price_history AS (
      SELECT 
        card_id,
        language,
        aa_version,
        price,
        currency,
        create_timestamp,
        DATE(create_timestamp) as price_date
      FROM `{history_tbl}`
      WHERE card_id = '{card_id}'
        AND create_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
        AND language = 'en'
        {aa_filter}
        AND currency IN ('eur', 'usd')
    ),
    daily_prices AS (
      SELECT 
        card_id,
        currency,
        price_date,
        AVG(price) as avg_price
      FROM price_history
      GROUP BY card_id, currency, price_date
    )
    SELECT 
      currency,
      price_date,
      avg_price as price
    FROM daily_prices
    ORDER BY currency, price_date ASC
    """
    
    rows = run_bq_query(query, ttl_hours=1.0)  # Cache for 1 hour since price data changes frequently
    
    # Organize data by currency
    result = {'eur': [], 'usd': []}
    
    for row in rows:
        currency = row['currency']
        price_date = row['price_date'].isoformat() if hasattr(row['price_date'], 'isoformat') else str(row['price_date'])
        
        result[currency].append({
            'date': price_date,
            'price': float(row['price']) if row['price'] is not None else None
        })
    
    return result

def get_leader_average_deck_prices(meta_format: MetaFormat, region: MetaFormatRegion) -> dict[str, float]:
    """Calculate average deck price in EUR for each leader in the given meta format and region."""
    decklists = get_tournament_decklist_data(meta_formats=[meta_format], meta_format_region=region)
    leader_prices = defaultdict(list)
    for d in decklists:
        if hasattr(d, 'price_eur') and d.price_eur and d.price_eur > 0:
            leader_prices[d.leader_id].append(d.price_eur)

    return {lid: sum(prices)/len(prices) for lid, prices in leader_prices.items()}
