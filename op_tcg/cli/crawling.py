from pathlib import Path

import click
from scrapy.crawler import CrawlerProcess
from op_tcg.backend.crawling.spiders.limitless_matches import LimitlessMatchesSpider
from op_tcg.backend.etl.extract import get_leader_ids
from op_tcg.backend.models.input import MetaFormat


@click.group("crawl", help="Crawling functionality")
def crawling_group() -> None:
    """
    Define a click group for the crawling section
    """
    pass


@click.group("limitless", help="Limitless Crawling functionality")
def limitless_group() -> None:
    """
    Define a click group for the crawling limitless section
    """
    pass

crawling_group.add_command(limitless_group)

@limitless_group.command()
@click.option("--meta-formats", "-m", multiple=True)
@click.option("--leader_ids", "-l", multiple=True)
@click.option("--use_all_leader_ids", is_flag=True, show_default=True, default=False)
@click.option("--data-dir", type=click.Path(), default=None)
def matches(
    meta_formats: list[MetaFormat] | None = None,
    leader_ids: list[str] | None = None,
    use_all_leader_ids: bool = False,
    data_dir: Path | None = None
) -> None:
    """
    Starts a limitless crawler

    data_dir: directory with op_tcg.models.input.LimitlessLeaderMetaMatches files, if None OP01-001 is used
    """
    process = CrawlerProcess({
        'ITEM_PIPELINES': {'op_tcg.backend.crawling.pipelines.MatchesPipeline': 1},  # Hooking in our custom pipline above
    })
    if meta_formats:
        # ensure enum format
        meta_formats = [MetaFormat(meta_format) for meta_format in meta_formats]
    if use_all_leader_ids:
        leader_ids = ['ST02-001', 'OP03-040', 'OP04-019', 'OP04-040', 'ST03-001', 'OP03-022', 'P-047', 'OP06-001', 'ST05-001',
                   'ST09-001', 'ST01-001', 'OP05-098', 'ST08-001', 'OP02-072', 'OP02-093', 'OP03-077', 'OP04-039',
                   'OP03-001', 'OP03-076', 'ST13-003', 'OP03-021', 'OP01-091', 'OP02-071', 'OP06-042', 'ST10-001',
                   'OP02-001', 'OP05-041', 'ST10-003', 'OP04-058', 'OP01-001', 'OP01-060', 'OP02-049', 'ST13-002',
                   'OP01-003', 'OP06-080', 'OP01-002', 'OP01-061', 'OP06-022', 'OP01-062', 'OP05-002', 'ST13-001',
                   'OP06-021', 'OP01-031', 'ST11-001', 'OP02-026', 'ST12-001', 'OP03-099', 'OP03-058', 'ST10-002',
                   'OP05-001', 'OP05-060', 'ST07-001', 'OP04-020', 'OP04-001', 'OP06-020', 'OP05-022', 'ST04-001',
                   'OP02-025', 'OP02-002', 'EB01-040', 'EB01-021', 'EB01-001']
    elif data_dir:
        # extract leader ids from already crawled files
        leader_ids = get_leader_ids(data_dir=data_dir)
    process.crawl(LimitlessMatchesSpider, meta_formats=meta_formats, leader_ids=leader_ids)
    process.start() # the script will block here until the crawling is finished


if __name__ == "__main__":
    matches()
