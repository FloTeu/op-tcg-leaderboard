import json
import logging
import os
import click

from pathlib import Path

from google.cloud import bigquery
from scrapy.crawler import CrawlerProcess
from tqdm import tqdm

from op_tcg.backend.crawling.spiders.limitless_matches import LimitlessMatchSpider
from op_tcg.backend.crawling.spiders.limitless_tournaments import LimitlessTournamentSpider
from op_tcg.backend.etl.extract import get_leader_ids, crawl_limitless_card
from op_tcg.backend.etl.load import get_or_create_table, bq_insert_rows
from op_tcg.backend.models.cards import Card, CardPrice, LimitlessCardData
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.tournaments import TournamentStanding


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
        'ITEM_PIPELINES': {'op_tcg.backend.crawling.pipelines.MatchesPipeline': 1},  # Hooking in our custom pipline
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
    process.crawl(LimitlessMatchSpider, meta_formats=meta_formats, leader_ids=leader_ids)
    process.start() # the script will block here until the crawling is finished


@limitless_group.command()
@click.option("--meta-formats", "-m", multiple=True)
@click.option("--num-tournament-limit", default=50)
def tournaments(
    num_tournament_limit: int,
    meta_formats: list[MetaFormat] | None = None,
) -> None:
    """
    Starts a limitless crawler for tournament data
    """
    assert os.environ.get("LIMITLESS_API_TOKEN"), "LIMITLESS_API_TOKEN not set in environment"
    process = CrawlerProcess({
        'ITEM_PIPELINES': {'op_tcg.backend.crawling.pipelines.CardPipeline': 1,
                           'op_tcg.backend.crawling.pipelines.TournamentPipeline': 2},
    })
    if meta_formats:
        # ensure enum format
        meta_formats = [MetaFormat(meta_format) for meta_format in meta_formats]
    process.crawl(LimitlessTournamentSpider, meta_formats=meta_formats, api_token=os.environ.get("LIMITLESS_API_TOKEN"), num_tournament_limit=num_tournament_limit)
    process.start() # the script will block here until the crawling is finished


@limitless_group.command()
def crawl_decklist_cards(
) -> None:
    """
    Crawls all card in existing decklists and pushes result to BQ.
    """

    bq_client = bigquery.Client(location="europe-west3")
    tournament_standing_table = get_or_create_table(TournamentStanding, client=bq_client)
    card_table = get_or_create_table(Card, client=bq_client)
    card_price_table = get_or_create_table(CardPrice, client=bq_client)

    already_crawled_card_ids: list[str] = []
    for card_row in bq_client.query(
            f"SELECT id FROM `{card_table.full_table_id.replace(':', '.')}`").result():
        already_crawled_card_ids.append(card_row["id"])

    decklist_card_ids = []
    for decklist_row in bq_client.query(f"SELECT decklist FROM `{tournament_standing_table.full_table_id.replace(':', '.')}` where decklist is not null").result():
        decklist_card_ids.extend(list(eval(decklist_row["decklist"]).keys()))

    new_unique_card_ids = set(decklist_card_ids) - set(already_crawled_card_ids)

    for card_id in tqdm(new_unique_card_ids):
        # Crawl data from limitless
        try:
            card_data: LimitlessCardData = crawl_limitless_card(card_id)
        except Exception as e:
            logging.warning("Card data could not be extracted", str(e))
            continue
        # Upload to big query
        bq_insert_rows([json.loads(bq_card.model_dump_json()) for bq_card in card_data.cards], table=card_table,
                       client=bq_client)
        bq_insert_rows([json.loads(bq_card_price.model_dump_json()) for bq_card_price in card_data.card_prices],
                       table=card_price_table, client=bq_client)


if __name__ == "__main__":
    matches()
