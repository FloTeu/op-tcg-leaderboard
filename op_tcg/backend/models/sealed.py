from datetime import datetime, date
from enum import StrEnum

from pydantic import Field

from op_tcg.backend.models.bq_classes import BQTableBaseModel
from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.backend.models.cards import OPTcgLanguage, OPTcgMarketplace, CardCurrency
from op_tcg.backend.models.common import DataSource


class SealedProductType(StrEnum):
    BOOSTER_BOX = "booster_box"
    BOOSTER_CASE = "booster_case"
    STARTER_DECK = "starter_deck"
    SEALED = "sealed"


class SealedProduct(BQTableBaseModel):
    """Sealed product metadata (booster boxes, cases, starter decks). Upserted on each crawl."""
    _dataset_id: str = BQDataset.CARDS

    id: str = Field(description="Marketplace URL slug, e.g. 'op01-romance-dawn-booster-box'", primary_key=True)
    marketplace: OPTcgMarketplace = Field(description="Source marketplace", primary_key=True)
    name: str = Field(description="Human-readable product name")
    product_type: SealedProductType = Field(description="Type of sealed product")
    language: OPTcgLanguage = Field(description="Language of the product print", primary_key=True)
    url: str = Field(description="Full product URL on the marketplace")
    image_url: str | None = Field(default=None, description="Product image URL from the marketplace")
    release_date: date | None = Field(default=None, description="Product release date if available")


class SealedPriceType(StrEnum):
    TREND = "trend"   # 30-day rolling average
    FROM = "from"     # lowest available listing price


class SealedProductPrice(BQTableBaseModel):
    """Append-only time-series of sealed product prices. One row per product/price-type per crawl."""
    _dataset_id: str = BQDataset.CARDS

    product_id: str = Field(description="FK to SealedProduct.id", primary_key=True)
    marketplace: OPTcgMarketplace = Field(description="Source marketplace", primary_key=True)
    price_type: SealedPriceType = Field(description="Whether this is a trend or from price", primary_key=True)
    price: float = Field(description="Price in the given currency")
    currency: CardCurrency = Field(description="Currency of the price")
    source: DataSource = Field(default=DataSource.CARDMARKET, description="Data source")