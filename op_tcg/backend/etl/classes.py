import json
import logging
import sys
import tempfile
import time

import pandas as pd
import requests
from google.api_core.exceptions import NotFound

from op_tcg.backend.elo import EloCreator
from op_tcg.backend.etl.base import AbstractETLJob, E, T
from op_tcg.backend.etl.load import get_or_create_table, bq_insert_rows, bq_upsert_rows, upload2gcp_storage
from op_tcg.backend.etl.transform import BQMatchCreator, parse_card_product, parse_sealed_product, \
    compute_expansion_release_set_matches, resolve_product_language_mapping, flatten_price_snapshot
from op_tcg.backend.etl.views import ensure_cardnexus_price_view, ensure_cardnexus_sealed_views
from op_tcg.backend.crawling.cardnexus_client import CardNexusClient
from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.backend.models.input import AllLeaderMetaDocs, MetaFormat, LimitlessLeaderMetaDoc
from op_tcg.backend.models.matches import BQMatches, Match
from op_tcg.backend.models.leader import LeaderElo
from op_tcg.backend.models.cards import Card, OPTcgLanguage
from op_tcg.backend.models.cardnexus import CardNexusCardProduct, CardNexusPriceSnapshot, CardNexusProductMapping, \
    CardNexusExpansionMapping, CardNexusSealedProduct
from op_tcg.backend.etl.extract import read_json_files
from pathlib import Path
from google.cloud import bigquery, storage
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
_logger = logging.getLogger("etl_classes")

class LocalMatchesToBigQueryEtlJob(AbstractETLJob[AllLeaderMetaDocs, BQMatches]):
    def __init__(self, data_dir: Path, meta_formats: list[MetaFormat] | None = None, official: bool=True):
        self.data_dir = data_dir
        self.meta_formats = meta_formats
        self.bq_client = bigquery.Client()
        self.official = official

    def validate(self, extracted_data: AllLeaderMetaDocs) -> bool:
        return True

    def extract(self) -> AllLeaderMetaDocs:
        all_matches: AllLeaderMetaDocs = read_json_files(self.data_dir)
        # include only the relevant meta formats
        if self.meta_formats:
            filtered_docs: list[LimitlessLeaderMetaDoc] = []
            for doc in all_matches.documents:
                if doc.meta_format in self.meta_formats:
                    filtered_docs.append(doc)
            all_matches.documents = filtered_docs
        meta_formats_in_data = list(set([doc.meta_format for doc in all_matches.documents]))
        assert all(require_meta_format in meta_formats_in_data for require_meta_format in self.meta_formats), "Not all required meta formats exist in the source data"
        return all_matches

    def transform(self, all_local_matches: AllLeaderMetaDocs) -> BQMatches:
        bq_match_creator = BQMatchCreator(all_local_matches, official=self.official)
        return bq_match_creator.transform2BQMatches()

    def load(self, transformed_data: BQMatches) -> None:
        table = get_or_create_table(model=Match, dataset_id=BQDataset.MATCHES, client=self.bq_client)
        df = transformed_data.to_dataframe()
        official_condition = "NOT official" if self.official else "official"
        if len(df) > 0:
            # delete existing official data in selected meta by only keeping other meta formats
            self.bq_client.query(f"""
            CREATE OR REPLACE TABLE {table.dataset_id}.{table.table_id} AS
            SELECT *
            FROM {table.dataset_id}.{table.table_id}
            WHERE (meta_format not in ('{"','".join(self.meta_formats)}')) OR {official_condition};
            """)
        # upload data of meta_formats to BQ
        self.bq_client.load_table_from_dataframe(df, table)
        _logger.info(f"Loading to BQ table {table.dataset_id}.{table.table_id} succeeded")


class EloUpdateToBigQueryEtlJob(AbstractETLJob[BQMatches, list[LeaderElo]]):
    def __init__(self, meta_formats: list[MetaFormat], matches_csv_file_path: Path | str | None = None):
        self.bq_client = bigquery.Client(location="europe-west1")
        self.meta_formats = meta_formats
        self.in_meta_format = "('" + "','".join(self.meta_formats) + "')"
        self.matches_csv_file_path = matches_csv_file_path

    def validate(self, extracted_data: AllLeaderMetaDocs) -> bool:
        return True

    def extract(self) -> BQMatches:
        if self.matches_csv_file_path:
            df = pd.read_csv(self.matches_csv_file_path)
        else:
            query = f"SELECT * FROM {BQDataset.MATCHES}.{Match.__tablename__} WHERE meta_format in {self.in_meta_format}"
            _logger.info(f"Query BQ with '{query}'")
            df = self.bq_client.query_and_wait(query).to_dataframe()
            _logger.info(f"Extracted {len(df)} rows from bq {BQDataset.MATCHES}.{Match.__tablename__}")
        matches: list[Match] = []
        for i, df_row in df.iterrows():
            matches.append(Match(**df_row.to_dict()))
        return BQMatches(matches=matches)


    def transform(self, all_matches: BQMatches) -> list[LeaderElo]:
        df_all_matches = all_matches.to_dataframe()
        elo_ratings: list[LeaderElo] = []
        def calculate_all_elo_ratings(df_matches):
            meta_format = df_matches.meta_format.unique().tolist()
            for only_official in [True, False]:
                _logger.info(f"Calculate Elo for meta {meta_format} and only_official {only_official}")
                try:
                    if only_official:
                        elo_creator = EloCreator(df_matches.query("official"), only_official=True)
                    else:
                        elo_creator = EloCreator(df_matches, only_official=False)
                except IndexError as e:
                    logging.error(f"Elo creation failed for {self.meta_formats} and only_official {only_official}")
                    continue
                elo_creator.calculate_elo_ratings()
                elo_ratings.extend(elo_creator.to_bq_leader_elos())
        if len(df_all_matches) > 0:
            df_all_matches.groupby("meta_format").apply(calculate_all_elo_ratings)
        return elo_ratings

    def load(self, transformed_data: list[LeaderElo]) -> None:
        # ensure bq table exists
        table = get_or_create_table(LeaderElo)
        leader_ids_to_update = list(set([d.leader_id for d in transformed_data]))
        in_leader_ids_to_update = "('" + "','".join(leader_ids_to_update) + "')"

        # delete all rows of meta
        self.bq_client.query(
            f"DELETE FROM `{table.full_table_id.split(':')[1]}` WHERE meta_format in {self.in_meta_format} and leader_id in {in_leader_ids_to_update};").result()
        # insert all new rows
        rows_to_insert = [json.loads(bq_leader_elo.model_dump_json()) for bq_leader_elo in transformed_data]
        bq_insert_rows(rows_to_insert, table=table, client=self.bq_client)
        _logger.info(f"Loading {len(transformed_data)} rows with meta {self.meta_formats} succeeded")


class CardImageUpdateToGCPEtlJob(AbstractETLJob[list[Card], list[Card]]):
    def __init__(self, meta_formats: list[MetaFormat] | None = None):
        self.bq_client = bigquery.Client(location="europe-west1")
        self.storage_client = storage.Client()
        self.bucket = f"{self.bq_client.project}-public"
        self.meta_formats = meta_formats or []
        self.in_meta_format_where_statement = "release_meta in ('" + "','".join(self.meta_formats) + "')"

    def validate(self, extracted_data: AllLeaderMetaDocs) -> bool:
        return True

    def extract(self) -> list[Card]:
        query = f'SELECT * FROM {BQDataset.CARDS}.{Card.__tablename__} WHERE image_url NOT LIKE "%googleapis%" '
        if self.meta_formats:
            query += f"and {self.in_meta_format_where_statement}"
        _logger.info(f"Query BQ with '{query}'")
        df = self.bq_client.query_and_wait(query).to_dataframe()
        _logger.info(f"Extracted {len(df)} rows from bq {BQDataset.CARDS}.{Card.__tablename__}")
        cards: list[Card] = []
        for i, df_row in df.iterrows():
            cards.append(Card(**df_row.to_dict()))
        return cards


    @staticmethod
    def _download_with_retry(url: str, max_retries: int = 3) -> bytes:
        """Download image with exponential backoff on connection errors."""
        delay = 5
        last_exc: Exception = RuntimeError(f"max_retries must be >= 1, got {max_retries}")
        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                return response.content
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                last_exc = e
                if attempt == max_retries - 1:
                    break
                _logger.warning(f"Connection error on attempt {attempt + 1}/{max_retries} for {url}: {e}. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
        raise last_exc

    def transform(self, cards: list[Card]) -> list[Card]:
        total = len(cards)
        _logger.info(f"transform: starting image upload for {total} card(s)")
        successful: list[Card] = []
        failed_count = 0
        for i, card in enumerate(cards):
            try:
                with tempfile.NamedTemporaryFile() as tmp:
                    img_data = self._download_with_retry(card.image_url)
                    tmp.write(img_data)
                    file_type = card.image_url.split('.')[-1]
                    image_url_path = f"card/images/{card.language.upper()}/{card.aa_version}/{card.id}.{file_type}"
                    upload2gcp_storage(path_to_file=tmp.name,
                                       bucket=self.bucket,
                                       blob_name=image_url_path,
                                       content_type=f"image/{file_type}",
                                       client=self.storage_client)
                    card.image_url = f"https://storage.googleapis.com/{self.bucket}/{image_url_path}"
                    successful.append(card)
                processed = i + 1
                if processed % 100 == 0:
                    _logger.info(f"transform: processed {processed}/{total} images ({failed_count} failed so far)")
                # Brief pause to avoid rate limiting
                time.sleep(0.5)
            except Exception as e:
                failed_count += 1
                _logger.error(f"Failed to process card {card.id} ({card.language}, aa_version={card.aa_version}): {e}")

        _logger.info(f"transform: finished — {len(successful)}/{total} succeeded, {failed_count} failed")
        return successful

    def load(self, cards: list[Card]) -> None:
        if len(cards) > 0:
            _logger.info(f"load: inserting {len(cards)} card(s) into BigQuery")
            # create tmp table
            card_table = get_or_create_table(Card, table_id=Card.__tablename__)
            # ensure table is new
            self.bq_client.delete_table(f"{Card.get_dataset_id()}.{Card.__tablename__}_tmp", not_found_ok=True)  # Make an API request.
            card_tmp_table = get_or_create_table(Card, table_id=f"{Card.__tablename__}_tmp")
            seen_keys: set[tuple] = set()
            rows_to_insert = []
            for card in cards:
                key = (card.id, card.language, card.aa_version)
                if key in seen_keys:
                    _logger.warning(f"load: skipping duplicate card {key}")
                    continue
                seen_keys.add(key)
                rows_to_insert.append(json.loads(card.model_dump_json()))

            # Retry insert until the freshly-created table is reachable by the
            # streaming API (propagation can take several seconds after create_table).
            max_wait = 60
            poll_interval = 5
            elapsed = 0
            while True:
                try:
                    bq_insert_rows(rows_to_insert, table=card_tmp_table, client=self.bq_client)
                    _logger.info(f"load: successfully inserted {len(rows_to_insert)} rows into {card_tmp_table.table_id}")
                    break
                except NotFound:
                    if elapsed >= max_wait:
                        raise
                    _logger.warning(
                        f"load: table {card_tmp_table.table_id} not yet available "
                        f"(elapsed {elapsed}s), retrying in {poll_interval}s..."
                    )
                    time.sleep(poll_interval)
                    elapsed += poll_interval

            # update rows
            try:
                self.bq_client.query(f"""
                MERGE `{card_table.full_table_id.replace(':', '.')}` AS target
                USING `{card_tmp_table.full_table_id.replace(':', '.')}` AS source
                ON target.id = source.id
                AND target.language = source.language
                AND target.aa_version = source.aa_version
                WHEN MATCHED THEN
                  UPDATE SET
                    target.image_url = source.image_url
                """).result()
                _logger.info(f"load: MERGE updated image_url for {len(cards)} card(s) in {card_table.table_id}")
            except Exception as e:
                _logger.error(f"load: MERGE query failed: {e}")

            # delete tmp table
            self.bq_client.delete_table(f"{card_tmp_table.full_table_id.replace(':', '.')}", not_found_ok=True)


class CardNexusCatalogSyncEtlJob(AbstractETLJob[dict, tuple]):
    """Syncs the CardNexus 'onepiece' catalog feed into BigQuery and (re)derives the
    product_id/language -> card_id/aa_version mapping used by CardNexusPriceUpdateEtlJob.

    Matching is two-stage: (1) CardNexus expansionIds are matched to our release_set_ids
    by comparing card id set composition (Jaccard similarity — see
    compute_expansion_release_set_matches), not by name/slug; (2) within a resolved
    release_set, CardNexus's `variant` field disambiguates a base print from its
    alternate-art parallel where both exist (see resolve_product_language_mapping).

    Skips the (expensive) feed download/parse entirely if the feed checksum hasn't
    changed since the last successful sync.
    """

    def __init__(self, game_id: str = "onepiece", cardnexus_client: CardNexusClient | None = None):
        self.bq_client = bigquery.Client(location="europe-west1")
        self.game_id = game_id
        self.cardnexus_client = cardnexus_client or CardNexusClient()

    def validate(self, extracted_data: dict) -> bool:
        return True

    def _get_last_checksum(self) -> str | None:
        try:
            query = (
                f"SELECT feed_checksum FROM {CardNexusCardProduct.get_dataset_id()}."
                f"{CardNexusCardProduct.__tablename__} ORDER BY create_timestamp DESC LIMIT 1"
            )
            df = self.bq_client.query_and_wait(query).to_dataframe()
            return df.iloc[0]["feed_checksum"] if len(df) > 0 else None
        except Exception as e:
            _logger.warning(f"Could not read last CardNexus feed checksum (likely first run): {e}")
            return None

    def extract(self) -> dict:
        feed_meta = self.cardnexus_client.get_catalog_feed_meta(self.game_id)
        feed_meta["last_checksum"] = self._get_last_checksum()
        return feed_meta

    def transform(self, feed_meta: dict) -> tuple[list[CardNexusCardProduct], list[CardNexusExpansionMapping],
                                                  list[CardNexusProductMapping], list[CardNexusSealedProduct]]:
        checksum = feed_meta.get("checksum") or ""
        if checksum and checksum == feed_meta.get("last_checksum"):
            _logger.info("CardNexus catalog feed checksum unchanged — skipping catalog sync")
            return [], [], [], []

        card_raw_products: list[dict] = []
        card_products: list[CardNexusCardProduct] = []
        sealed_products: list[CardNexusSealedProduct] = []
        skipped = 0
        unknown_product_types = 0
        for raw_product in self.cardnexus_client.iter_catalog_products(self.game_id):
            product_type = raw_product.get("productType")
            try:
                if product_type == "card":
                    card_raw_products.append(raw_product)
                    card_products.append(parse_card_product(raw_product, feed_checksum=checksum))
                elif product_type == "sealed":
                    sealed_products.append(parse_sealed_product(raw_product, feed_checksum=checksum))
                else:
                    unknown_product_types += 1
            except (KeyError, TypeError) as e:
                skipped += 1
                _logger.warning(f"Skipping malformed CardNexus catalog product record: {e}")
        if skipped:
            _logger.warning(f"Skipped {skipped} malformed CardNexus catalog product record(s)")
        if unknown_product_types:
            _logger.warning(f"Skipped {unknown_product_types} catalog record(s) with unrecognized productType")

        # Group CardNexus card ids by expansionId, for the release-set Jaccard match
        expansion_to_card_ids: dict[str, set[str]] = {}
        for raw_product in card_raw_products:
            expansion_id = raw_product.get("expansionId")
            print_number = raw_product.get("printNumber")
            if expansion_id is None or not print_number:
                continue
            expansion_to_card_ids.setdefault(str(expansion_id), set()).add(print_number)

        cards_df = self.bq_client.query_and_wait(
            f"SELECT id, language, aa_version, release_set_id FROM {BQDataset.CARDS}.{Card.__tablename__}"
        ).to_dataframe()
        release_set_to_card_ids: dict[str, set[str]] = {}
        candidates_lookup: dict[tuple[str, str, OPTcgLanguage], list[int]] = {}
        for _, row in cards_df.iterrows():
            release_set_to_card_ids.setdefault(row["release_set_id"], set()).add(row["id"])
            key = (row["id"], row["release_set_id"], OPTcgLanguage(row["language"]))
            candidates_lookup.setdefault(key, []).append(int(row["aa_version"]))

        best_matches = compute_expansion_release_set_matches(expansion_to_card_ids, release_set_to_card_ids)
        expansion_to_release_set = {expansion_id: release_set_id for expansion_id, (release_set_id, _) in best_matches.items()}
        expansion_mappings = [
            CardNexusExpansionMapping(
                expansion_id=expansion_id,
                release_set_id=best_matches[expansion_id][0] if expansion_id in best_matches else None,
                jaccard_score=best_matches[expansion_id][1] if expansion_id in best_matches else None,
                matched=expansion_id in best_matches,
            )
            for expansion_id in expansion_to_card_ids
        ]
        _logger.info(
            f"CardNexus release matching: {len(best_matches)}/{len(expansion_to_card_ids)} expansions matched to a release_set_id"
        )

        product_mappings: list[CardNexusProductMapping] = []
        for raw_product in card_raw_products:
            product_mappings.extend(resolve_product_language_mapping(raw_product, expansion_to_release_set, candidates_lookup))
        matched_count = sum(1 for m in product_mappings if m.matched)
        _logger.info(
            f"CardNexus catalog sync: {len(card_products)} cards, {len(sealed_products)} sealed products, "
            f"{len(product_mappings)} product/language rows, {matched_count} matched, "
            f"{len(product_mappings) - matched_count} unmatched/ambiguous"
        )
        return card_products, expansion_mappings, product_mappings, sealed_products

    def load(self, transformed_data: tuple[list[CardNexusCardProduct], list[CardNexusExpansionMapping],
                                           list[CardNexusProductMapping], list[CardNexusSealedProduct]]) -> None:
        card_products, expansion_mappings, product_mappings, sealed_products = transformed_data
        if card_products:
            bq_upsert_rows(card_products, client=self.bq_client)
        if expansion_mappings:
            bq_upsert_rows(expansion_mappings, client=self.bq_client)
        if product_mappings:
            bq_upsert_rows(product_mappings, client=self.bq_client)
        if sealed_products:
            bq_upsert_rows(sealed_products, client=self.bq_client)
        # Ensure raw tables exist even on a skipped/empty run, then (re)create the views
        get_or_create_table(CardNexusCardProduct, client=self.bq_client)
        get_or_create_table(CardNexusExpansionMapping, client=self.bq_client)
        get_or_create_table(CardNexusProductMapping, client=self.bq_client)
        get_or_create_table(CardNexusSealedProduct, client=self.bq_client)
        ensure_cardnexus_price_view(self.bq_client)
        ensure_cardnexus_sealed_views(self.bq_client)


class CardNexusPriceUpdateEtlJob(AbstractETLJob[list, list]):
    """Pulls current prices for already-matched CardNexus card products and all
    known sealed products, prioritizing never-priced products and then the ones
    priced longest ago.

    Sealed products aren't gated on a match (there's no mapping/matching step for
    them — see CardNexusSealedProduct) so every known sealed product is eligible.

    Bounded by max_requests per run so repeated scheduled invocations stay within
    CardNexus's 600/hour current-prices rate limit while eventually covering the
    full catalog. Run CardNexusCatalogSyncEtlJob first to populate the candidate tables.
    """

    def __init__(self, max_requests: int = 500, sealed_only: bool = False, cardnexus_client: CardNexusClient | None = None):
        self.bq_client = bigquery.Client(location="europe-west1")
        self.max_requests = max_requests
        self.sealed_only = sealed_only
        self.cardnexus_client = cardnexus_client or CardNexusClient()

    def validate(self, extracted_data: list) -> bool:
        return True

    def extract(self) -> list[str]:
        mapping_table = f"{CardNexusProductMapping.get_dataset_id()}.{CardNexusProductMapping.__tablename__}"
        sealed_table = f"{CardNexusSealedProduct.get_dataset_id()}.{CardNexusSealedProduct.__tablename__}"
        snapshot_table = f"{CardNexusPriceSnapshot.get_dataset_id()}.{CardNexusPriceSnapshot.__tablename__}"
        if self.sealed_only:
            candidates_cte = f"SELECT product_id FROM `{sealed_table}`"
        else:
            candidates_cte = f"""
            SELECT product_id FROM `{mapping_table}` WHERE matched
            UNION DISTINCT
            SELECT product_id FROM `{sealed_table}`
            """
        query = f"""
        SELECT c.product_id
        FROM ({candidates_cte}) c
        LEFT JOIN (
            SELECT product_id, MAX(create_timestamp) AS last_priced
            FROM `{snapshot_table}`
            GROUP BY product_id
        ) s ON c.product_id = s.product_id
        ORDER BY s.last_priced IS NULL DESC, s.last_priced ASC
        LIMIT {self.max_requests}
        """
        try:
            df = self.bq_client.query_and_wait(query).to_dataframe()
            return df["product_id"].tolist()
        except Exception as e:
            _logger.warning(f"Prioritized candidate query failed (likely first run): {e}")
        try:
            df = self.bq_client.query_and_wait(
                f"SELECT product_id FROM ({candidates_cte}) LIMIT {self.max_requests}"
            ).to_dataframe()
            return df["product_id"].tolist()
        except Exception as e:
            _logger.error(f"Could not find any CardNexus products to price — run sync-catalog first: {e}")
            return []

    def transform(self, product_ids: list[str]) -> list[CardNexusPriceSnapshot]:
        snapshots: list[CardNexusPriceSnapshot] = []
        failed = 0
        for product_id in product_ids:
            try:
                prices_response = self.cardnexus_client.get_current_prices(product_id)
                snapshots.extend(flatten_price_snapshot(product_id, prices_response))
            except Exception as e:
                failed += 1
                _logger.error(f"Failed to fetch/parse CardNexus prices for product {product_id}: {e}")
        _logger.info(
            f"CardNexus price update: {len(product_ids)} products requested, {failed} failed, "
            f"{len(snapshots)} price rows produced"
        )
        return snapshots

    def load(self, snapshots: list[CardNexusPriceSnapshot]) -> None:
        if not snapshots:
            return
        table = get_or_create_table(CardNexusPriceSnapshot, client=self.bq_client)
        rows_to_insert = [json.loads(s.model_dump_json()) for s in snapshots]
        bq_insert_rows(rows_to_insert, table=table, client=self.bq_client)
        _logger.info(f"Inserted {len(snapshots)} CardNexus price snapshot rows")