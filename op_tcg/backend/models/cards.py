from datetime import datetime, date
from enum import StrEnum

from pydantic import Field, BaseModel

from op_tcg.backend.models.base import EnumBase
from op_tcg.backend.models.bq_classes import BQTableBaseModel
from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.backend.models.common import DataSource
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.utils.color_fns import average_hex_colors


class OPTcgColor(EnumBase, StrEnum):
    RED="Red"
    GREEN="Green"
    BLUE="Blue"
    PURPLE="Purple"
    BLACK="Black"
    YELLOW="Yellow"

    def to_hex_color(self) -> str:
        if self == self.RED:
            return "#c0392b"
        elif self == self.GREEN:
            return "#27ae60"
        elif self == self.BLUE:
            return "#2980b9"
        elif self == self.PURPLE:
            return "#8e44ad"
        elif self == self.BLACK:
            return "#0b1214"
        elif self == self.YELLOW:
            return "#f1c40f"


class OPTcgAttribute(EnumBase, StrEnum):
    SLASH="Slash"
    STRIKE="Strike"
    SPECIAL="Special"
    WISDOM="Wisdom"
    RANGED="Ranged"

class OPTcgTournamentStatus(EnumBase, StrEnum):
    BANNED="banned"
    LEGAL="legal"


class OPTcgLanguage(StrEnum):
    EN="en"
    JP="jp"

class OPTcgCardCatagory(EnumBase, StrEnum):
    LEADER="Leader"
    CHARACTER="Character"
    EVENT="Event"
    STAGE="Stage"

class OPTcgCardRarity(StrEnum):
    COMMON="Common"
    UNCOMMON="Uncommon"
    RARE="Rare"
    SUPER_RARE="Super Rare"
    SECRET_RARE="Secret Rare"
    LEADER="Leader"
    PROMO="Promo"


class OPTcgAbility(EnumBase, StrEnum):
    RUSH = "Rush"
    BLOCKER = "Blocker"
    BANISH = "Banish"
    TRIGGER = "Trigger"


class OPTcgCardSetType(EnumBase, StrEnum):
    BOOSTER = "Booster Packs"
    STARTER_DECK = "Starter Decks"
    PROMO = "Promotional Products"


class CardCurrency(EnumBase, StrEnum):
    EURO="eur"
    US_DOLLAR="usd"

class BaseCard(BaseModel):
    """attributes which all card have in common"""
    id: str = Field(description="The op tcg id e.g. OP03-099", primary_key=True)
    language: OPTcgLanguage = Field(default=OPTcgLanguage.EN, description="Language of the text data in this instance", primary_key=True)
    aa_version: int = Field(description="Alt art version of design, 0 is the original design, 1 the first alt art etc.", primary_key=True)
    name: str = Field(description="The op tcg name e.g. Charlotte Katakuri")
    image_url: str = Field(description="Public accessible url to standard image of the card")
    colors: list[OPTcgColor] = Field(description="Colors of the card")
    ability: str = Field(description="Ability of the leader")
    tournament_status: OPTcgTournamentStatus | None = Field(description="Whether the card is banned for tournaments")
    types: list[str] = Field(description="List of fractions of the card, e.g. Straw Hat Crew")
    rarity: OPTcgCardRarity = Field(description="Rarity of the card, e.g. Common")
    card_category: OPTcgCardCatagory = Field(description="Category of card e.g. 'character'")
    release_set_id: str = Field(description="Id of the release set e.g. 'OP07_24'")


    def to_hex_color(self) -> str:
        hex_colors: list[str] = []
        for color in self.colors:
            hex_colors.append(color.to_hex_color())
        return average_hex_colors(hex_colors)


class Card(BaseCard, BQTableBaseModel):
    _dataset_id: str = BQDataset.CARDS
    attributes: list[OPTcgAttribute] = Field(description="Attributes of the leader or character card, e.g. Slash")
    power: int | None = Field(description="Power of leader or character card")
    cost: int | None = Field(description="Costs to summon the non-leader card e.g. 4")
    counter: int | None = Field(description="Counter value of a character card e.g. +2000")
    life: int | None = Field(description="Life of leader card e.g. 4")


class CardPrice(BQTableBaseModel):
    _dataset_id: str = BQDataset.CARDS
    card_id: str = Field(description="The op tcg card id e.g. OP03-099", primary_key=True)
    language: OPTcgLanguage = Field(default=OPTcgLanguage.EN, description="Language of the text data in this instance", primary_key=True)
    aa_version: int = Field(description="Alt art version of design, 0 is the original design, 1 the first alt art etc.", primary_key=True)
    price: float = Field(description="Price of the card at the related timestamp, e.g. 4.39")
    currency: CardCurrency = Field(description="Currency of the price, e.g. 'usd'")
    create_timestamp: datetime = Field(default_factory=datetime.now, description="Creation timestamp when the insert in BQ happened", primary_key=True)

class LatestCardPrice(Card):
    latest_eur_price: float | None = Field(description="Latest price of the card in euro")
    latest_usd_price: float | None = Field(description="Latest price of the card in us dollar")

class LimitlessCardData(BaseModel):
    cards: list[Card]
    card_prices: list[CardPrice]


class CardPopularity(BQTableBaseModel):
    _dataset_id: str = BQDataset.CARDS
    card_id: str = Field(description="The op tcg card id e.g. OP03-099", primary_key=True)
    meta_format: MetaFormat | str = Field(description="Meta in which tournament happened, e.g. OP06")
    color: OPTcgColor = Field(description="Color of the card")
    popularity: float = Field(description="Value between 0 and 1. Its 0 if the card was not played in any decklist and 1 if the card was played in 100% of decklists with an equal color type")

class CardReleaseSet(BQTableBaseModel):
    _dataset_id: str = BQDataset.CARDS
    id: str = Field(description="release_set id, can be either code or some other unique id", primary_key=True)
    language: OPTcgLanguage = Field(description="Language of the set", primary_key=True)
    name: str = Field(description="Name of the release set, e.g. '500 Years in the Future'")
    meta_format: MetaFormat | None = Field(description="Meta in which set was released. None if release date is not known, e.g. Prize Cards")
    release_date: date | None = Field(description="Date when the set as published in the language marked")
    card_count: int = Field(description="Number of card in set")
    code: str | None = Field(description="Identifier code of the set, e.g. 'OP07")
    type: OPTcgCardSetType | None = Field(description="Typ of release set, e.g. 'booster'")
    url: str = Field(description="Url with all card and price information")
    source: DataSource = Field(description="Source of url")

class ExtendedCardData(LatestCardPrice, CardReleaseSet):
    pass

    def get_searchable_string(self):
        return ' '.join(str(value) for value in self.model_dump().values())

