import os
import base64
import json

from google.cloud import pubsub_v1
from scrapy.crawler import CrawlerProcess

from op_tcg.backend.crawling.spiders.limitless_prices import LimitlessPricesSpider
from op_tcg.backend.crawling.spiders.limitless_tournaments import LimitlessTournamentSpider
from op_tcg.backend.etl.classes import EloUpdateToBigQueryEtlJob, CardImageUpdateToGCPEtlJob
from op_tcg.backend.models.input import MetaFormat


def run_all_etl_elo_update(event, context):
    topic_id = "elo-update-pub-sub"
    print("GOOGLE_CLOUD_PROJECT", os.getenv("GOOGLE_CLOUD_PROJECT"))

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(os.getenv("GOOGLE_CLOUD_PROJECT"), topic_id)

    for meta_format in MetaFormat.to_list():
        # Data must be a bytestring
        data_dict = {"meta_formats": [meta_format]}
        data = json.dumps(data_dict)  # Convert the dictionary to a JSON string
        data = data.encode("utf-8")  # Convert the string to bytes
        # Add two attributes, origin and username, to the message
        future = publisher.publish(
            topic_path, data
        )
        print(future.result())

    return f"Successfully published all messages!"


def run_etl_elo_update(event, context):
    """
    Background Cloud Function to be triggered by Pub/Sub.

    Args:
        event (dict): The dictionary with data specific to this type of event.
                      The `data` field contains the Pub/Sub message data.
        context (google.cloud.functions.Context): Metadata for the event.
    """

    # Decode the Pub/Sub message
    pubsub_message = event['data']
    message_data = base64.b64decode(pubsub_message).decode('utf-8')

    # Convert message data from JSON string to dictionary
    message_dict = json.loads(message_data)

    print(f"Received message: {message_dict}")
    meta_formats = message_dict.get("meta_formats") or MetaFormat.to_list()
    print("Call cloud function with meta_formats", meta_formats, type(meta_formats))

    for meta_format in meta_formats:
        etl_job = EloUpdateToBigQueryEtlJob(meta_formats=[meta_format], matches_csv_file_path=None)
        etl_job.run()
    return f"Success with meta formats {meta_formats}!"

def run_crawl_tournament(event, context):
    """
    Cloud Function triggered by Pub/Sub.
    The function crawls latest limitless tournament data

    Args:
        event (dict): The dictionary with data specific to this type of event.
                      The `data` field contains the Pub/Sub message data.
        context (google.cloud.functions.Context): Metadata for the event.
    """

    # Decode the Pub/Sub message
    pubsub_message = event['data']
    message_data = base64.b64decode(pubsub_message).decode('utf-8')

    # Convert message data from JSON string to dictionary
    message_dict = json.loads(message_data)

    print(f"Received message: {message_dict}")
    meta_formats = message_dict.get("meta_formats", None) or MetaFormat.to_list()
    num_tournament_limit = message_dict.get("num_tournament_limit", 50)
    print("Crawl limitless with meta_formats and num_tournament_limit", meta_formats, num_tournament_limit)

    assert os.environ.get("LIMITLESS_API_TOKEN"), "LIMITLESS_API_TOKEN not set in environment"
    process = CrawlerProcess({
        'ITEM_PIPELINES': {'op_tcg.backend.crawling.pipelines.TournamentPipeline': 1},  # Hooking in our custom pipline
    })
    # ensure enum format
    meta_formats = [MetaFormat(meta_format) for meta_format in meta_formats]
    process.crawl(LimitlessTournamentSpider, meta_formats=meta_formats, api_token=os.environ.get("LIMITLESS_API_TOKEN"), num_tournament_limit=num_tournament_limit)
    process.start() # the script will block here until the crawling is finished

    return f"Successfully ran limitless tournament crawling"


def run_etl_card_image_update(event, context):
    """
    Background Cloud Function to be triggered by Pub/Sub.

    Args:
        event (dict): The dictionary with data specific to this type of event.
                      The `data` field contains the Pub/Sub message data.
        context (google.cloud.functions.Context): Metadata for the event.
    """

    # Decode the Pub/Sub message
    pubsub_message = event['data']
    message_data = base64.b64decode(pubsub_message).decode('utf-8')

    # Convert message data from JSON string to dictionary
    message_dict = json.loads(message_data)

    print(f"Received message: {message_dict}")
    meta_formats = message_dict.get("meta_formats") or []
    print("Call cloud function with meta_formats", meta_formats, type(meta_formats))

    etl_job = CardImageUpdateToGCPEtlJob(meta_formats=meta_formats)
    etl_job.run()
    return f"Success with meta formats {meta_formats}!"


def run_crawl_prices(event, context):
    """
    Background Cloud Function to be triggered by Pub/Sub.

    Args:
        event (dict): The dictionary with data specific to this type of event.
                      The `data` field contains the Pub/Sub message data.
        context (google.cloud.functions.Context): Metadata for the event.
    """
    process = CrawlerProcess({
        'ITEM_PIPELINES': {
                           'op_tcg.backend.crawling.pipelines.CardReleaseSetPipeline': 1,
                           'op_tcg.backend.crawling.pipelines.CardPricePipeline': 2,
                           'op_tcg.backend.crawling.pipelines.CardPipeline': 3,
                           }
    })
    process.crawl(LimitlessPricesSpider)
    process.start() # the script will block here until the crawling is finished

    return f"Success!"