from pydantic import BaseModel, Field
from datetime import datetime
from enum import IntEnum, Enum


class MatchResult(IntEnum):
    LOSE = 0
    WIN = 1
    DRAW = 2


class MetaFormat(str, Enum):
    OP01 = "OP01"
    OP02 = "OP02"
    OP03 = "OP03"
    OP04 = "OP04"
    OP05 = "OP05"
    OP06 = "OP06"


class BQMatch(BaseModel):
    leader_id: str = Field(description="The op tcg leader id e.g. OP03-099")
    opponent_id: str = Field(description="The op tcg opponent id e.g. OP03-099")
    result: MatchResult = Field(description="Result of the match. Can be win, lose or draw")
    meta_format: MetaFormat = Field(description="Meta in which matches happened, e.g. OP06")
    official_match: bool = Field(default=False, description="Whether the match ha originated from an official tournament")
    timestamp: datetime = Field(description="Approximate timestamp when the match happened")


