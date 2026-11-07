import logging
from pathlib import Path

from google.api_core.exceptions import NotFound
from google.cloud import bigquery

from op_tcg.backend.etl.load import get_or_create_table
from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.backend.models.cardnexus import CardNexusPrice, CardNexusCardProductMapping, CardNexusSealedProduct

logger = logging.getLogger(__name__)

SQL_VIEWS_DIR = Path(__file__).parent / "sql" / "views"

# Views whose SQL lives in SQL_VIEWS_DIR as "<dataset>.<view>.sql".
# Order matters: CREATE VIEW validates referenced views at creation time, so dependencies come first.
# Table references inside the SQL are dataset-relative (e.g. `matches.match`) and resolve to the client's project.
MANAGED_VIEWS: list[tuple[BQDataset, str]] = [
    (BQDataset.LEADERS, "leader"),
    (BQDataset.MATCHES, "leader_win_rate"),
    (BQDataset.MATCHES, "leader_win_rate_aggregated"),
    (BQDataset.MATCHES, "tournament_extended"),
    (BQDataset.LEADERS, "tournament_winner"),
    (BQDataset.LEADERS, "leader_extended"),
    (BQDataset.CARDS, "latest_card_price"),
    (BQDataset.CARDS, "card_popularity"),
]


def _normalize_view_sql(sql: str) -> str:
    return sql.strip().rstrip(";").strip()


def load_view_sql(dataset: BQDataset, view_name: str) -> str:
    return _normalize_view_sql((SQL_VIEWS_DIR / f"{dataset}.{view_name}.sql").read_text())


def ensure_managed_views(client: bigquery.Client, dry_run: bool = False) -> list[str]:
    """(Re-)creates all MANAGED_VIEWS whose BigQuery definition differs from the SQL file in the repo.

    Unchanged views are skipped, so no query job is started for them. With dry_run=True nothing is
    changed and the returned ids show which views have drifted from the repo (e.g. edited in the console).

    Returns the ids of views that were (or, with dry_run, would be) created or replaced.
    """
    changed_view_ids: list[str] = []
    for dataset, view_name in MANAGED_VIEWS:
        view_id = f"{client.project}.{dataset}.{view_name}"
        sql = load_view_sql(dataset, view_name)
        try:
            current_sql = _normalize_view_sql(client.get_table(view_id).view_query or "")
        except NotFound:
            current_sql = None
        if current_sql == sql:
            continue
        changed_view_ids.append(view_id)
        if dry_run:
            logger.info("View %s differs from repo SQL", view_id)
            continue
        client.query(f"CREATE OR REPLACE VIEW `{view_id}` AS\n{sql}").result()
        logger.info("Ensured view %s", view_id)
    return changed_view_ids


def ensure_cardnexus_price_view(client: bigquery.Client) -> None:
    """(Re-)creates the cards.card_nexus_price_view, joining the unified price
    history table with the product mapping into a shape aligned with our own
    card/price columns (card_id, language, aa_version, date, ..., source).

    Exposes the full daily history (not just the latest row) — consumers wanting
    "current price" only can filter/QUALIFY on MAX(date) themselves.

    Idempotent — safe to call on every catalog sync. Ensures the tables it
    references exist first, since CREATE VIEW validates them at creation time.
    """
    history_table = get_or_create_table(CardNexusPrice, client=client)
    mapping_table = get_or_create_table(CardNexusCardProductMapping, client=client)

    view_id = f"{client.project}.{BQDataset.CARDS}.card_nexus_price_view"
    query = f"""
    CREATE OR REPLACE VIEW `{view_id}` AS
    SELECT
        m.card_id,
        m.language,
        m.aa_version,
        h.marketplace,
        h.finish,
        h.date,
        h.currency,
        h.low,
        h.mid,
        h.high,
        h.market_value,
        'cardnexus' AS source
    FROM `{history_table.project}.{history_table.dataset_id}.{history_table.table_id}` h
    JOIN `{mapping_table.project}.{mapping_table.dataset_id}.{mapping_table.table_id}` m
        ON h.product_id = m.product_id
    WHERE m.matched
    """
    client.query(query).result()
    logger.info("Ensured view %s", view_id)


def ensure_cardnexus_sealed_views(client: bigquery.Client) -> None:
    """(Re-)creates forward-looking views over CardNexus's own sealed-product catalog
    (booster boxes, cases, starter decks, etc), reshaped into columns resembling our
    existing SealedProduct/SealedProductPrice tables.

    These are NOT wired into the app yet. Matching against our existing cardmarket-
    scraped SealedProduct table is handled separately by CardNexusSealedProductMapping
    (see op_tcg.backend.etl.transform.resolve_sealed_product_mapping_by_cardmarket_id) —
    these views expose CardNexus's own catalog standalone, not joined to that mapping.

    The views themselves live in BQDataset.SEALED (not CARDS) — alongside
    CardNexusSealedProductMapping, even though the underlying CardNexusSealedProduct
    raw table they read from lives in CARDNEXUS_RAW, same as the card side.

    Idempotent — safe to call on every catalog sync. Ensures the tables it
    references exist first, since CREATE VIEW validates them at creation time.
    """
    product_table = get_or_create_table(CardNexusSealedProduct, client=client)
    history_table = get_or_create_table(CardNexusPrice, client=client)
    product_table_id = f"{product_table.project}.{product_table.dataset_id}.{product_table.table_id}"
    history_table_id = f"{history_table.project}.{history_table.dataset_id}.{history_table.table_id}"

    product_view_id = f"{client.project}.{BQDataset.SEALED}.card_nexus_sealed_product_view"
    client.query(f"""
    CREATE OR REPLACE VIEW `{product_view_id}` AS
    SELECT
        product_id,
        name,
        product_category,
        expansion_id,
        expansion_slug,
        image_url,
        create_timestamp
    FROM `{product_table_id}`
    """).result()

    price_view_id = f"{client.project}.{BQDataset.SEALED}.card_nexus_sealed_price_view"
    client.query(f"""
    CREATE OR REPLACE VIEW `{price_view_id}` AS
    SELECT
        p.product_id,
        p.name,
        p.product_category,
        h.marketplace,
        h.finish,
        h.date,
        h.currency,
        h.low,
        h.mid,
        h.high,
        h.market_value,
        'cardnexus' AS source
    FROM `{history_table_id}` h
    JOIN `{product_table_id}` p
        ON h.product_id = p.product_id
    """).result()
    logger.info("Ensured views %s and %s", product_view_id, price_view_id)
