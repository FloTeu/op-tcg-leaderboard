from datetime import date
from enum import StrEnum

from pydantic import Field
from op_tcg.backend.models.base import EnumBase
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.backend.models.bq_classes import BQTableBaseModel
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

class OPTcgLanguage(StrEnum):
    EN="en"
    JP="jp"

class Leader(BQTableBaseModel):
    _dataset_id: str = BQDataset.LEADERS
    id: str = Field(description="The op tcg leader id e.g. OP03-099", primary_key=True)
    name: str = Field(description="The op tcg leader name e.g. Charlotte Katakuri")
    life: int = Field(description="Life of leader")
    power: int = Field(description="Power of leader")
    release_meta: MetaFormat | None = Field(None, description="The meta format in which the Leader was released")
    avatar_icon_url: str = Field(description="Public accessible url to an avatar icon of the leader")
    image_url: str = Field(description="Public accessible url to standard image")
    image_aa_url: str = Field(description="Public accessible url to alternative artwork image")
    colors: list[OPTcgColor] = Field(description="Colors of the leader")
    attributes: list[OPTcgAttribute] = Field(description="Attributes of the leader, e.g. Slash")
    ability: str = Field(description="Ability of the leader")
    fractions: list[str] = Field(description="List of fractions of the leader, e.g. Straw Hat Crew")
    language: OPTcgLanguage = Field(default=OPTcgLanguage.EN, description="Language of the data in this obect")


    def to_hex_color(self) -> str:
        hex_colors: list[str] = []
        for color in self.colors:
            hex_colors.append(color.to_hex_color())
        return average_hex_colors(hex_colors)


class LeaderElo(BQTableBaseModel):
    _dataset_id: str = BQDataset.LEADERS
    meta_format: MetaFormat = Field(description="Meta until or in which the elo is calculated", primary_key=True)
    leader_id: str = Field(description="The op tcg leader id e.g. OP03-099", primary_key=True)
    only_official: bool = Field(default=False, description="Whether the matches are only originated from "
                                                           "official tournaments", primary_key=True)
    elo: int = Field(description="Elo rating of leader until a certain time/ meta format")
    start_date: date = Field(description="Date in which the elo calculation started")
    end_date: date = Field(description="Date in which the elo calculation ended")


class TournamentWinner(BQTableBaseModel):
    _dataset_id: str = BQDataset.LEADERS
    meta_format: MetaFormat = Field(description="Meta until or in which the elo is calculated", primary_key=True)
    leader_id: str = Field(description="The op tcg leader id e.g. OP03-099", primary_key=True)
    win_count: int = Field(description="Number of total tournament wins in meta format")
    only_official: bool = Field(default=False, description="Whether the matches are only originated from "
                                                           "official tournaments", primary_key=True)
