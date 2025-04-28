import datetime
from enum import StrEnum, auto
from datetime import datetime

from pydantic import BaseModel, Field

from op_tcg.backend.models.base import EnumBase


class MetaFormat(EnumBase, StrEnum):
    # Note: must be in the right order for some frontend functionality
    OP01 = "OP01"
    OP02 = "OP02"
    OP03 = "OP03"
    OP04 = "OP04"
    OP05 = "OP05"
    OP06 = "OP06"
    OP07 = "OP07"
    OP08 = "OP08"
    OP09 = "OP09"
    OP10 = "OP10"
    OP11 = "OP11"
    OP12 = "OP12"
    OP13 = "OP13"
    OP14 = "OP14"

    @classmethod
    def to_list(cls, only_after_release: bool = True, until_meta_format: str | None = None) -> list[str]:
        all_meta_formats = list(map(lambda c: c.value, cls))
        if until_meta_format is not None:
            until_meta_format_i = all_meta_formats.index(cls(until_meta_format))
            all_meta_formats = all_meta_formats[:until_meta_format_i+1]
        return_meta_formats = []
        for meta_format in all_meta_formats:
            if not only_after_release:
                return_meta_formats.append(meta_format)
            elif meta_format2release_datetime(meta_format) and (
                    meta_format2release_datetime(meta_format) <= datetime.now()):
                return_meta_formats.append(meta_format)
        return return_meta_formats

    @classmethod
    def latest_meta_format(cls, only_after_release: bool = True) -> "MetaFormat":
        return cls.to_list(only_after_release=only_after_release)[-1]


class MetaFormatRegion(EnumBase, StrEnum):
    ASIA = auto()
    WEST = auto()
    ALL = auto()


class LimitlessMatch(BaseModel):
    leader_name: str = Field(description="The op tcg leader name")
    leader_id: str = Field(description="The op tcg leader id e.g. OP03-099")
    num_matches: int = Field(description="Total number of matches")
    score_win: int = Field(
        description="Number of matches won. its the first digit of the score string e.g. 31 - 35 - 0 -> 31")
    score_lose: int = Field(
        description="Number of matches lost. its the second digit of the score string e.g. 31 - 35 - 0 -> 35")
    score_draw: int = Field(
        description="Number of matches draw. its the third digit of the score string e.g. 31 - 35 - 0 -> 0")
    win_rate: float = Field(description="Ratio of games won. Number should be between 0 and 1.")


class LimitlessLeaderMetaDoc(BaseModel):
    leader_id: str = Field(description="The op tcg leader id e.g. OP03-099")
    meta_format: MetaFormat = Field(description="Meta in which matches happened, e.g. OP06")
    matches: list[LimitlessMatch] = Field(description="List of matches between this leader with all others")


class AllLeaderMetaDocs(BaseModel):
    documents: list[LimitlessLeaderMetaDoc]


def meta_format2release_datetime(meta_format: MetaFormat) -> datetime | None:
    if meta_format == MetaFormat.OP01:
        return datetime(2022, 12, 2)
    if meta_format == MetaFormat.OP02:
        return datetime(2023, 3, 10)
    if meta_format == MetaFormat.OP03:
        return datetime(2023, 6, 30)
    if meta_format == MetaFormat.OP04:
        return datetime(2023, 9, 22)
    if meta_format == MetaFormat.OP05:
        return datetime(2023, 12, 8)
    if meta_format == MetaFormat.OP06:
        return datetime(2024, 3, 8)
    if meta_format == MetaFormat.OP07:
        return datetime(2024, 6, 28)
    if meta_format == MetaFormat.OP08:
        return datetime(2024, 9, 13)
    if meta_format == MetaFormat.OP09:
        return datetime(2024, 12, 13)
    if meta_format == MetaFormat.OP10:
        return datetime(2025, 3, 21)
    # if meta_format == MetaFormat.OP11:
    #     return datetime(2024, 6, 14)
    else:
        return None

def get_meta_format_by_datetime(dt: datetime) -> MetaFormat:
    """
    returns: matching meta format to given datetime
    """
    # starts with latest (released) meta format
    for meta_format in sorted(MetaFormat.to_list(only_after_release=True), reverse=True):
        if dt >= meta_format2release_datetime(meta_format):
            return meta_format
    raise ValueError(f"Could not match meta format to datetime: {dt}")