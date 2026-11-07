from pathlib import Path

import click
from google.cloud import bigquery

from op_tcg.backend.etl.views import ensure_managed_views
from op_tcg.backend.etl.classes import LocalMatchesToBigQueryEtlJob, EloUpdateToBigQueryEtlJob, \
    CardImageUpdateToGCPEtlJob, CardNexusCatalogSyncEtlJob, CardNexusPriceUpdateEtlJob, CardNexusPriceHistoryEtlJob
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.utils.notify import notify_job_result


@click.group("etl", help="Crawling functionality")
def etl_group() -> None:
    """
    Define a click group for the crawling section
    """
    pass


@etl_group.command()
@click.argument("data-dir", type=click.Path(), default=None)
@click.option("--meta-formats", "-m", multiple=True)
def upload_matches(
    data_dir: Path,
    meta_formats: tuple[MetaFormat]
) -> None:
    """
    Starts a job which pushes the local matches file to bigquery.
    Caution: As we dont now which row got an update, the all rows in a meta format will be overwritten

    data_dir: Directory with op_tcg.models.input.LimitlessLeaderMetaMatches files
    meta_formats: Tuple of relevant meta format which should be used for the data update. If None provided, all meta formats are used.
    """

    etl_job = LocalMatchesToBigQueryEtlJob(data_dir=data_dir, meta_formats=list(meta_formats))
    etl_job.run()

@etl_group.command()
@click.option("--meta-formats", "-m", multiple=True)
@click.option("--file-path", "-f", type=click.Path(), default=None)
def calculate_leader_elo(
        meta_formats: tuple[MetaFormat],
        file_path: Path=None
) -> None:
    """
    Starts a job which calculates all elo rating for all leaders and all meta format and pushes result to BQ.

    file_path: Optional file path to matches.csv containing rows matching the BQ Schema BQMatch
    meta_formats: Tuple of relevant meta format which should be used for the data update. If None provided, all meta formats are used.

    """

    assert not (file_path is None and meta_formats is None), "Content of file is not filtered by meta format. Either provide a file only or select some meta formats"
    meta_formats = meta_formats or MetaFormat.to_list()
    etl_job = EloUpdateToBigQueryEtlJob(meta_formats=meta_formats, matches_csv_file_path=file_path)
    etl_job.run()

@etl_group.command()
@click.option("--meta-formats", "-m", multiple=True)
@click.option("--file-path", "-f", type=click.Path(), default=None)
def update_card_images(
        meta_formats: tuple[MetaFormat],
        file_path: Path=None
) -> None:
    """
    Starts a job which downloads all card images which do no exist yet in gcp storage.

    """

    assert not (file_path is None and meta_formats is None), "Content of file is not filtered by meta format. Either provide a file only or select some meta formats"
    meta_formats = list(meta_formats)
    etl_job = CardImageUpdateToGCPEtlJob(meta_formats=meta_formats)
    etl_job.run()


@etl_group.command("ensure-views")
@click.option("--dry-run", is_flag=True, default=False,
              help="Only list views whose BigQuery definition differs from the repo SQL, without changing them.")
def ensure_views(dry_run: bool) -> None:
    """
    (Re-)creates the BigQuery views defined in op_tcg/backend/etl/sql/views whose definition differs from the repo.
    """
    changed_view_ids = ensure_managed_views(bigquery.Client(location="europe-west1"), dry_run=dry_run)
    action = "Differs from repo" if dry_run else "Created/replaced"
    for view_id in changed_view_ids:
        click.echo(f"{action}: {view_id}")
    if not changed_view_ids:
        click.echo("All views match the repo SQL")


@etl_group.group("cardnexus", help="ETL jobs for CardNexus catalog/price data")
def cardnexus_group() -> None:
    pass


@cardnexus_group.command("sync-catalog")
@click.option("--game-id", default="onepiece", help="CardNexus game id for the catalog feed")
@click.option("--force", is_flag=True, default=False,
             help="Bypass the feed-checksum skip and re-run the full sync/matching even if "
                  "CardNexus's catalog feed hasn't changed since the last run. Use this to "
                  "rebuild tables/mappings that were wiped or moved on our side, since the "
                  "checksum only tracks CardNexus's upstream feed, not our own data.")
def cardnexus_sync_catalog(game_id: str, force: bool) -> None:
    """
    Syncs the CardNexus catalog feed into BigQuery (raw + product_id -> card_id mapping)
    and (re)creates the cards.card_nexus_price_view. Skips the feed download entirely if
    unchanged since the last run (via the feed checksum), unless --force is passed.
    """
    job_name = "cardnexus-sync-catalog"
    try:
        card_products, card_mappings, sealed_products, sealed_mappings = \
            CardNexusCatalogSyncEtlJob(game_id=game_id, force=force).run()
    except Exception as e:
        notify_job_result(job_name, success=False, summary="", error=str(e))
        raise
    if not (card_products or sealed_products):
        summary = "Feed checksum unchanged, sync skipped"
    else:
        card_matched = sum(1 for m in card_mappings if m.matched)
        sealed_matched = sum(1 for m in sealed_mappings if m.matched)
        summary = (
            f"{len(card_products)} cards ({card_matched}/{len(card_mappings)} card/language rows matched), "
            f"{len(sealed_products)} sealed ({sealed_matched}/{len(sealed_mappings)} matched)"
        )
    notify_job_result(job_name, success=True, summary=summary)


def _run_cardnexus_price_job(job_name: str, etl_job: CardNexusPriceUpdateEtlJob) -> None:
    try:
        rows = etl_job.run()
    except Exception as e:
        notify_job_result(job_name, success=False, summary="", error=str(e))
        raise
    _notify_price_job_result(job_name, etl_job, len(rows))


def _notify_price_job_result(job_name: str, etl_job: CardNexusPriceUpdateEtlJob | CardNexusPriceHistoryEtlJob,
                             row_count: int) -> None:
    requested, failed = etl_job.requested_count, etl_job.failed_count
    summary = f"{row_count} price rows from {requested - failed}/{requested} products"
    if failed:
        summary += f", {failed} failed"
    # Per-product errors are swallowed by the job, so a run where every request failed
    # (e.g. bad API key, sustained 429s) would otherwise look like a success.
    notify_job_result(job_name, success=not (requested and failed == requested), summary=summary)


@cardnexus_group.command("update-prices")
@click.option("--max-requests", "-n", type=int, default=500,
             help="Max CardNexus API calls to spend this run. Stay under 600/hour across "
                  "scheduled invocations, since /prices is rate-limited at 600 requests/hour.")
@click.option("--sealed-only", is_flag=True, default=False,
             help="Only update prices for sealed products (booster boxes, cases, decks, ...), "
                  "skipping cards entirely.")
def cardnexus_update_prices(max_requests: int, sealed_only: bool) -> None:
    """
    Pulls current prices for CardNexus products already matched to our cards, prioritizing
    never-priced products and then the ones priced longest ago. Run 'sync-catalog' first.
    """
    _run_cardnexus_price_job(
        "cardnexus-update-prices",
        CardNexusPriceUpdateEtlJob(max_requests=max_requests, sealed_only=sealed_only),
    )


@cardnexus_group.command("update-price-history")
@click.option("--min-days", type=int, default=30,
             help="Only backfill products with fewer than this many dates recorded. Products "
                  "already backfilled no longer qualify, so re-running resumes where it stopped.")
@click.option("--batch-size", type=int, default=100,
             help="Products fetched per batch before upserting to BigQuery. An interruption "
                  "loses at most one batch (~50 min at the 120 requests/hour history limit).")
@click.option("--max-requests", "-n", type=int, default=None,
             help="Cap on CardNexus API calls for this run (default: all qualifying products).")
@click.option("--days", type=int, default=365,
             help="Days of history to request per product (CardNexus caps a single request at 365).")
@click.option("--sealed-only", is_flag=True, default=False,
             help="Only backfill history for sealed products (booster boxes, cases, decks, ...), "
                  "skipping cards entirely.")
def cardnexus_update_price_history(min_days: int, batch_size: int, max_requests: int | None,
                                   days: int, sealed_only: bool) -> None:
    """
    One-off local backfill of historical daily prices (up to yesterday) into the same table
    'update-prices' keeps current. Paced at CardNexus's 120 requests/hour history limit, so a
    full catalog takes ~2 days — keep the machine awake (e.g. `caffeinate -i optcg ...`).
    Run 'sync-catalog' first.
    """
    job_name = "cardnexus-update-price-history"
    etl_job = CardNexusPriceHistoryEtlJob(max_requests=max_requests, days=days, sealed_only=sealed_only,
                                          min_history_days=min_days)
    try:
        row_count = etl_job.run_in_batches(batch_size=batch_size)
    except Exception as e:
        notify_job_result(job_name, success=False, summary="", error=str(e))
        raise
    _notify_price_job_result(job_name, etl_job, row_count)

if __name__ == "__main__":
    upload_matches()
