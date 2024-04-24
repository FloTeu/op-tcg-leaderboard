from enum import StrEnum

from sqlmodel import SQLModel, Field
from op_tcg.backend.models.base import EnumBase
from op_tcg.backend.models.input import MetaFormat


class OPTcgColor(EnumBase, StrEnum):
    RED="Red"
    GREEN="Green"
    BLUE="Blue"
    PURPLE="Purple"
    BLACK="Black"
    YELLOW="Yellow"

class OPTcgAttribute(EnumBase, StrEnum):
    SLASH="Slash"
    STRIKE="Strike"
    SPECIAL="Special"
    WISDOM="Wisdom"
    RANGED="Ranged"

class OPTcgLanguage(StrEnum):
    EN="en"
    JP="jp"

class BQLeader(SQLModel, table=True):
    id: str = Field(description="The op tcg leader id e.g. OP03-099", primary_key=True)
    name: str = Field(description="The op tcg leader name e.g. Charlotte Katakuri")
    life: int = Field(description="Life of leader")
    power: int = Field(description="Power of leader")
    release_meta: MetaFormat | None = Field(None, description="The meta format in which the Leader was released")
    avatar_icon_url: str = Field(description="Public accessible url to an avatar icon of the leader")
    image_url: str = Field(description="Public accessible url to standard image")
    image_aa_url: str = Field(description="Public accessible url to alternative artwork image")
    colors: list[str] = Field(description="Colors of the leader")
    attributes: list[OPTcgAttribute] = Field(description="Attributes of the leader, e.g. Slash")
    ability: str = Field(description="Ability of the leader")
    fractions: list[str] = Field(description="List of fractions of the leader, e.g. Straw Hat Crew")
    language: OPTcgLanguage = Field(default=OPTcgLanguage.EN, description="Language of the data in this obect")
