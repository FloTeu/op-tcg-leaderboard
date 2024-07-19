import datetime
from enum import StrEnum
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

    @classmethod
    def to_list(cls, only_after_release: bool = True):
        all_meta_formats = list(map(lambda c: c.value, cls))
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
    else:
        return None
