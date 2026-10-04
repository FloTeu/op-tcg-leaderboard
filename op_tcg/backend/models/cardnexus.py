from datetime import date as date_type, datetime

from pydantic import Field

from op_tcg.backend.models.bq_classes import BQTableBaseModel
from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.backend.models.cards import OPTcgLanguage, OPTcgMarketplace


class CardNexusCardProduct(BQTableBaseModel):
    """Raw catalog feed record for a card (CardNexus's `productType: "card"`) from
    the CardNexus 'onepiece' catalog feed.

    Only a handful of convenience columns are extracted; `raw_json` keeps the
    full record verbatim since the CardNexus API is still under active
    development and its schema is expected to change.
    """
    _dataset_id: str = BQDataset.CARDNEXUS_RAW

    product_id: str = Field(description="CardNexus stable product id (their 'id' field)", primary_key=True)
    print_number: str | None = Field(default=None, description="CardNexus printNumber, expected to align with our card id format e.g. OP03-099")
    name: str | None = Field(default=None, description="Product name from the catalog feed")
    expansion_id: str | None = Field(default=None, description="CardNexus expansion id")
    expansion_slug: str | None = Field(default=None, description="CardNexus expansion slug")
    feed_checksum: str = Field(description="Checksum of the catalog feed this record was parsed from, used for change detection")
    raw_json: str = Field(description="Full raw catalog record as JSON, preserved in case of upstream schema changes")


class CardNexusSealedProduct(BQTableBaseModel):
    """Raw catalog feed record for a non-card CardNexus product (booster boxes,
    cases, starter decks, promo bundles, etc — CardNexus's `productType: "sealed"`).

    Kept separate from CardNexusCardProduct. See CardNexusSealedProductMapping for
    how these are reconciled against our own cardmarket-scraped SealedProduct table.

    Lives in BQDataset.CARDNEXUS_RAW alongside CardNexusCardProduct — it's raw CardNexus
    catalog data, same as the card side. CardNexusSealedProductMapping (the match result)
    lives in BQDataset.SEALED instead, alongside the rest of the sealed-product data.
    """
    _dataset_id: str = BQDataset.CARDNEXUS_RAW

    product_id: str = Field(description="CardNexus stable product id (their 'id' field)", primary_key=True)
    name: str | None = Field(default=None, description="Product name from the catalog feed")
    expansion_id: str | None = Field(default=None, description="CardNexus expansion id")
    expansion_slug: str | None = Field(default=None, description="CardNexus expansion slug")
    product_category: str | None = Field(default=None, description="CardNexus product category, e.g. 'booster_box'")
    image_url: str | None = Field(default=None, description="Product image URL")
    feed_checksum: str = Field(description="Checksum of the catalog feed this record was parsed from, used for change detection")
    raw_json: str = Field(description="Full raw catalog record as JSON, preserved in case of upstream schema changes")


class CardNexusPrice(BQTableBaseModel):
    """Unified daily price table for a CardNexus product/marketplace/finish.

    One row per (product_id, marketplace, finish, date) — upserted, not appended.
    Populated by two ETL jobs writing into the same table: CardNexusPriceHistoryEtlJob
    backfills past dates from /products/{id}/prices/history; CardNexusPriceUpdateEtlJob
    upserts today's row from /products/{id}/prices (the current-price endpoint),
    keeping the table current going forward from wherever the historical backfill
    left off. Repeated same-day snapshot pulls overwrite today's row rather than
    accumulating duplicates.

    Common fields (low/mid/high/market_value/currency) are flattened for convenience;
    `raw_json` keeps the full source block/record verbatim since the nested
    by-condition/by-region data (and the schema in general) is still evolving upstream.

    Replaces the old append-only, timestamp-keyed CardNexusPriceSnapshot table.
    """
    _dataset_id: str = BQDataset.CARDNEXUS_RAW

    product_id: str = Field(description="CardNexus product id, FK to CardNexusCardProduct.product_id or CardNexusSealedProduct.product_id", primary_key=True)
    marketplace: OPTcgMarketplace = Field(description="Pricing source reported for this block: cardmarket, tcgplayer, or cardnexus", primary_key=True)
    finish: str = Field(description="Card finish reported by CardNexus, e.g. 'Standard' or 'Foil'", primary_key=True)
    date: date_type = Field(description="Calendar date this price applies to", primary_key=True)
    currency: str | None = Field(default=None, description="Currency code reported for this marketplace block")
    low: float | None = Field(default=None, description="Lowest price reported for this marketplace block")
    mid: float | None = Field(default=None, description="Mid price reported for this marketplace block")
    high: float | None = Field(default=None, description="High price reported for this marketplace block")
    market_value: float | None = Field(default=None, description="Market value price reported for this marketplace block")
    raw_json: str = Field(description="Full raw block/record this row was derived from, preserved verbatim since the CardNexus API is still under active development")


class CardNexusCardProductMapping(BQTableBaseModel):
    """Maps a CardNexus product id + language to our own card id/language/aa_version.

    CardNexus has a single product id covering all of its languages, while our Card
    table has one row per (id, language, aa_version) — so one CardNexus product can
    map to more than one of our rows (e.g. one for EN, one for JP), hence the PK is
    (product_id, language) rather than product_id alone.

    Re-derived on every catalog sync by matching on the numeric TCGplayer product id:
    CardNexus lists it per product (`externalIds.tcgplayer`), and our own
    CardMarketplaceUrl rows embed the same id in their scraped TCGplayer affiliate
    link — see op_tcg.backend.etl.transform.resolve_product_mapping_by_tcgplayer_id.
    The id is already unique per exact (card_id, language, aa_version) print, so this
    resolves card identity and aa_version/variant disambiguation in a single exact-match
    step rather than guessing from expansion/variant metadata.

    tcgplayer_id/cardmarket_id are carried along from the same CardNexus catalog record
    (not derived from the match itself) so a direct Cardmarket/TCGplayer product link can
    be built straight from this table without re-parsing the raw catalog feed.
    """
    _dataset_id: str = BQDataset.CARDS

    product_id: str = Field(description="CardNexus product id", primary_key=True)
    language: OPTcgLanguage = Field(description="Our language this row resolves to (CardNexus itself is not split by language)", primary_key=True)
    card_id: str | None = Field(default=None, description="Matched op tcg card id, None if unmatched")
    aa_version: int | None = Field(default=None, description="Matched card aa_version, None if unmatched")
    tcgplayer_id: str | None = Field(default=None, description="CardNexus-listed TCGplayer product id for the finish that produced this match (or the first listed, if unmatched)")
    cardmarket_id: str | None = Field(default=None, description="CardNexus-listed Cardmarket product id for the same finish, for building direct Cardmarket product links")
    matched: bool = Field(description="Whether a confident match to our Card table was found")
    match_method: str = Field(description="How the match was derived, e.g. 'tcgplayer_id', 'no_external_id', 'no_match'")


class CardNexusSealedProductMapping(BQTableBaseModel):
    """Maps a CardNexus sealed product id to our own cardmarket-scraped SealedProduct.

    Sealed products have no print_number to match on (unlike cards), so matching uses
    the numeric Cardmarket product id instead — the one id both catalogs share for
    sealed products. CardNexus lists it explicitly (`externalIds.cardmarket`); our own
    SealedProduct table doesn't store it directly, but Cardmarket's own CDN embeds it as
    the filename of SealedProduct.image_url (e.g. `.../577919/577919.jpg`), so it's
    recovered from there — see op_tcg.backend.etl.transform.extract_cardmarket_id_from_image_url
    and resolve_sealed_product_mapping_by_cardmarket_id.

    One row per CardNexus product id (unlike CardNexusCardProductMapping, not split by
    language) since CardNexus's sealed catalog bundles all print languages under a
    single external id rather than listing one per language.

    Lives in BQDataset.SEALED, not CARDS or CARDNEXUS_RAW — this is the match *result*
    against our own sealed-product data, destined to join the SealedProduct/
    SealedProductPrice tables once those move here too.
    """
    _dataset_id: str = BQDataset.SEALED

    product_id: str = Field(description="CardNexus product id", primary_key=True)
    sealed_product_id: str | None = Field(default=None, description="Matched op tcg SealedProduct.id, None if unmatched")
    language: OPTcgLanguage | None = Field(default=None, description="Language of the matched SealedProduct row, None if unmatched")
    tcgplayer_id: str | None = Field(default=None, description="CardNexus-listed TCGplayer product id, carried along for convenience")
    cardmarket_id: str | None = Field(default=None, description="CardNexus-listed Cardmarket product id used for matching")
    matched: bool = Field(description="Whether a confident match to our SealedProduct table was found")
    match_method: str = Field(description="How the match was derived, e.g. 'cardmarket_id', 'no_external_id', 'no_match'")
