from pathlib import Path

import click
from op_tcg.backend.etl.classes import LocalMatchesToBigQueryEtlJob, EloUpdateToBigQueryEtlJob, \
    CardImageUpdateToGCPEtlJob, CardNexusCatalogSyncEtlJob, CardNexusPriceUpdateEtlJob
from op_tcg.backend.models.input import MetaFormat


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


@etl_group.group("cardnexus", help="ETL jobs for CardNexus catalog/price data")
def cardnexus_group() -> None:
    pass


@cardnexus_group.command("sync-catalog")
@click.option("--game-id", default="onepiece", help="CardNexus game id for the catalog feed")
def cardnexus_sync_catalog(game_id: str) -> None:
    """
    Syncs the CardNexus catalog feed into BigQuery (raw + product_id -> card_id mapping)
    and (re)creates the cards.card_nexus_price_view. Skips the feed download entirely if
    unchanged since the last run (via the feed checksum).
    """
    etl_job = CardNexusCatalogSyncEtlJob(game_id=game_id)
    etl_job.run()


@cardnexus_group.command("update-prices")
@click.option("--max-requests", "-n", type=int, default=500,
             help="Max CardNexus API calls to spend this run. Stay under 600/hour across "
                  "scheduled invocations, since /prices is rate-limited at 600 requests/hour.")
def cardnexus_update_prices(max_requests: int) -> None:
    """
    Pulls current prices for CardNexus products already matched to our cards, prioritizing
    never-priced products and then the ones priced longest ago. Run 'sync-catalog' first.
    """
    etl_job = CardNexusPriceUpdateEtlJob(max_requests=max_requests)
    etl_job.run()


if __name__ == "__main__":
    upload_matches()
