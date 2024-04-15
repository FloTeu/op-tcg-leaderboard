from pathlib import Path

import click
from op_tcg.backend.etl.classes import LocalMatchesToBigQueryEtlJob


@click.group("etl", help="Crawling functionality")
def etl_group() -> None:
    """
    Define a click group for the crawling section
    """
    pass


@etl_group.command()
@click.argument("data-dir", type=click.Path(), default=None)
def upload_matches(
    data_dir: Path
) -> None:
    """
    Starts a job which pushes the local matches file to bigquery

    data_dir: directory with op_tcg.models.input.LimitlessLeaderMetaMatches files
    """

    etl_job = LocalMatchesToBigQueryEtlJob(data_dir=data_dir)
    etl_job.run()


if __name__ == "__main__":
    upload_matches()
