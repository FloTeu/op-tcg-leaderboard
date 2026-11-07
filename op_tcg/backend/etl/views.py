import logging
from pathlib import Path

from google.api_core.exceptions import NotFound
from google.cloud import bigquery

from op_tcg.backend.models.bq_enums import BQDataset

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
    (BQDataset.CARDS, "card_nexus_price_view"),
    (BQDataset.SEALED, "card_nexus_sealed_product_view"),
    (BQDataset.SEALED, "card_nexus_sealed_price_view"),
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
