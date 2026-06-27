import hashlib
from datetime import datetime, date
from enum import StrEnum

from pydantic import Field

from op_tcg.backend.models.bq_classes import BQTableBaseModel
from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.backend.models.cards import OPTcgLanguage, OPTcgMarketplace, CardCurrency
from op_tcg.backend.models.common import DataSource


class SealedProductType(StrEnum):
    BOOSTER_BOX = "Booster Box"
    BOOSTER_CASE = "Booster Case"
    PRECONSTRUCTED_DECK = "Preconstructed Deck"
    PROMO = "Promo Product"


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
    gcs_image_url: str | None = Field(default=None, description="GCS URL of the locally cached product image")
    release_date: date | None = Field(default=None, description="Product release date if available")


def sealed_product_gcs_path(product_id: str, image_url: str) -> str:
    """Compute the GCS blob path for a sealed product image.

    The URL hash is embedded in the filename so that if the source image_url
    changes the path changes too, enabling change detection without a separate field.
    Images are always stored as WebP regardless of the source format.
    """
    url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
    return f"sealed/images/{product_id}_{url_hash}.webp"


class SealedPriceType(StrEnum):
    TREND = "trend"   # 30-day rolling average
    FROM = "from"     # lowest available listing price


class SealedProductOrderBy(StrEnum):
    """Sort order options for sealed product listings."""
    PRICE_DESC = "price_desc"
    PRICE_ASC = "price_asc"
    NAME_ASC = "name_asc"
    NAME_DESC = "name_desc"
    RELEASE_DESC = "release_desc"

    @property
    def label(self) -> str:
        return {
            SealedProductOrderBy.PRICE_DESC: "Price: High to Low",
            SealedProductOrderBy.PRICE_ASC: "Price: Low to High",
            SealedProductOrderBy.NAME_ASC: "Name: A to Z",
            SealedProductOrderBy.NAME_DESC: "Name: Z to A",
            SealedProductOrderBy.RELEASE_DESC: "Newest First",
        }[self]


class SealedProductPrice(BQTableBaseModel):
    """Append-only time-series of sealed product prices. One row per product/price-type per crawl."""
    _dataset_id: str = BQDataset.CARDS

    product_id: str = Field(description="FK to SealedProduct.id", primary_key=True)
    marketplace: OPTcgMarketplace = Field(description="Source marketplace", primary_key=True)
    price_type: SealedPriceType = Field(description="Whether this is a trend or from price", primary_key=True)
    price: float = Field(description="Price in the given currency")
    currency: CardCurrency = Field(description="Currency of the price")
    source: DataSource = Field(default=DataSource.CARDMARKET, description="Data source")