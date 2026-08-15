import logging

from google.cloud import bigquery

from op_tcg.backend.etl.load import get_or_create_table
from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.backend.models.cardnexus import CardNexusPriceSnapshot, CardNexusProductMapping

logger = logging.getLogger(__name__)


def ensure_cardnexus_price_view(client: bigquery.Client) -> None:
    """(Re-)creates the cards.card_nexus_price_view, joining raw price snapshots
    with the product mapping into a shape aligned with our own card/price columns
    (card_id, language, aa_version, ..., create_timestamp, source).

    Idempotent — safe to call on every catalog sync. Ensures the tables it
    references exist first, since CREATE VIEW validates them at creation time.
    """
    snapshot_table = get_or_create_table(CardNexusPriceSnapshot, client=client)
    mapping_table = get_or_create_table(CardNexusProductMapping, client=client)

    view_id = f"{client.project}.{BQDataset.CARDS}.card_nexus_price_view"
    query = f"""
    CREATE OR REPLACE VIEW `{view_id}` AS
    SELECT
        m.card_id,
        m.language,
        m.aa_version,
        s.marketplace,
        s.finish,
        s.currency,
        s.low,
        s.mid,
        s.high,
        s.market_value,
        s.create_timestamp,
        'cardnexus' AS source
    FROM `{snapshot_table.project}.{snapshot_table.dataset_id}.{snapshot_table.table_id}` s
    JOIN `{mapping_table.project}.{mapping_table.dataset_id}.{mapping_table.table_id}` m
        ON s.product_id = m.product_id
    WHERE m.matched
    """
    client.query(query).result()
    logger.info("Ensured view %s", view_id)
