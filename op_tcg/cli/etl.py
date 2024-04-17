from pathlib import Path

import click
from op_tcg.backend.etl.classes import LocalMatchesToBigQueryEtlJob
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
    meta_formats: Tuple of relevant meta format which should be used for the data update
    """

    etl_job = LocalMatchesToBigQueryEtlJob(data_dir=data_dir, meta_formats=list(meta_formats))
    etl_job.run()


if __name__ == "__main__":
    upload_matches()
