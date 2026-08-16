import logging

from google.cloud import bigquery

from op_tcg.backend.etl.load import get_or_create_table
from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.backend.models.cardnexus import CardNexusPrice, CardNexusProductMapping, CardNexusSealedProduct

logger = logging.getLogger(__name__)


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
    mapping_table = get_or_create_table(CardNexusProductMapping, client=client)

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

    These are NOT wired into the app yet and are NOT joined against our existing
    cardmarket-scraped SealedProduct table at all — matching sealed products id-for-id
    isn't attempted here. CardNexus's sealed catalog is self-contained (its own ids,
    names, categories) and is exposed standalone as a preview of what could later
    replace the cardmarket scraper as a source, not as a supplement to it.

    Idempotent — safe to call on every catalog sync. Ensures the tables it
    references exist first, since CREATE VIEW validates them at creation time.
    """
    product_table = get_or_create_table(CardNexusSealedProduct, client=client)
    history_table = get_or_create_table(CardNexusPrice, client=client)
    product_table_id = f"{product_table.project}.{product_table.dataset_id}.{product_table.table_id}"
    history_table_id = f"{history_table.project}.{history_table.dataset_id}.{history_table.table_id}"

    product_view_id = f"{client.project}.{BQDataset.CARDS}.card_nexus_sealed_product_view"
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

    price_view_id = f"{client.project}.{BQDataset.CARDS}.card_nexus_sealed_price_view"
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
