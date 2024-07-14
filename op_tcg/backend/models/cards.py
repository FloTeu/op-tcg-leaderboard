from enum import StrEnum

from pydantic import Field, BaseModel

from op_tcg.backend.models.base import EnumBase
from op_tcg.backend.models.bq_classes import BQTableBaseModel
from op_tcg.backend.models.bq_enums import BQDataset
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

class OPTcgCardCatagory(StrEnum):
    LEADER="Leader"
    CHARACTER="Character"
    EVENT="Event"
    STAGE="Stage"

class BaseCard(BaseModel):
    """attributes which all card have in common"""
    id: str = Field(description="The op tcg id e.g. OP03-099", primary_key=True)
    name: str = Field(description="The op tcg name e.g. Charlotte Katakuri")
    release_meta: MetaFormat | None = Field(None, description="The meta format in which the Leader was released")
    image_url: str = Field(description="Public accessible url to standard image of the card")
    image_aa_urls: list[str] = Field(description="Public accessible url to alternative artwork image")
    colors: list[OPTcgColor] = Field(description="Colors of the leader")
    ability: str = Field(description="Ability of the leader")
    tournament_status: OPTcgTournamentStatus | None = Field(description="Whether the card is banned for tournaments")
    fractions: list[str] = Field(description="List of fractions of the leader, e.g. Straw Hat Crew")
    language: OPTcgLanguage = Field(default=OPTcgLanguage.EN, description="Language of the text data in this instance", primary_key=True)
    card_category: OPTcgCardCatagory = Field(description="Category of card e.g. 'character'")


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

