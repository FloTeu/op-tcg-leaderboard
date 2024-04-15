import os
import click
from typing import Any

from scrapy.crawler import CrawlerProcess
from op_tcg.crawling.matches.matches.spiders.limitless import LimitlessSpider

@click.group("crawl", help="Crawling functionality")
def crawling_group() -> None:
    """
    Define a click group for the crawling section
    """
    pass


@crawling_group.command()
def limitless(
) -> None:
    """
    Starts a limitless crawler
    """

    process = CrawlerProcess({})
    process.crawl(LimitlessSpider)
    process.start() # the script will block here until the crawling is finished



if __name__ == "__main__":
    limitless()
