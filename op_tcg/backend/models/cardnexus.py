from datetime import datetime

from pydantic import Field

from op_tcg.backend.models.bq_classes import BQTableBaseModel
from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.backend.models.cards import OPTcgLanguage, OPTcgMarketplace


class CardNexusCatalogProduct(BQTableBaseModel):
    """Raw catalog feed record from the CardNexus 'onepiece' catalog feed.

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


class CardNexusPriceSnapshot(BQTableBaseModel):
    """Append-only raw pull of /products/{id}/prices, one row per marketplace block per finish.

    Common fields (low/mid/high/market_value/currency) are flattened for convenience;
    `raw_json` keeps the full block verbatim since the nested by-condition/by-region
    data (and the schema in general) is still evolving upstream.
    """
    _dataset_id: str = BQDataset.CARDNEXUS_RAW

    product_id: str = Field(description="CardNexus product id, FK to CardNexusCatalogProduct.product_id", primary_key=True)
    finish: str = Field(description="Card finish reported by CardNexus, e.g. 'Standard' or 'Foil'", primary_key=True)
    marketplace: OPTcgMarketplace = Field(description="Pricing source reported for this block: cardmarket, tcgplayer, or cardnexus", primary_key=True)
    create_timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp when this snapshot was pulled", primary_key=True)
    currency: str | None = Field(default=None, description="Currency code reported for this marketplace block")
    low: float | None = Field(default=None, description="Lowest price reported for this marketplace block")
    mid: float | None = Field(default=None, description="Mid price reported for this marketplace block")
    high: float | None = Field(default=None, description="High price reported for this marketplace block")
    market_value: float | None = Field(default=None, description="Market value price reported for this marketplace block")
    raw_json: str = Field(description="Full raw block for this marketplace/finish, preserved verbatim since the CardNexus API is still under active development")


class CardNexusProductMapping(BQTableBaseModel):
    """Maps a CardNexus product id to our own card id/language/aa_version.

    Re-derived on every catalog sync from print_number matching against the existing
    Card table. Ambiguous or unresolved matches are kept (matched=False) rather than
    guessed, since CardNexus does not expose language/aa_version directly.
    """
    _dataset_id: str = BQDataset.CARDS

    product_id: str = Field(description="CardNexus product id", primary_key=True)
    card_id: str | None = Field(default=None, description="Matched op tcg card id, None if unmatched")
    language: OPTcgLanguage | None = Field(default=None, description="Matched card language, None if unmatched or ambiguous")
    aa_version: int | None = Field(default=None, description="Matched card aa_version, None if unmatched or ambiguous")
    matched: bool = Field(description="Whether a confident, unambiguous match to our Card table was found")
    match_method: str = Field(description="How the match was derived, e.g. 'print_number_unique', 'ambiguous_print_number', 'no_match'")
