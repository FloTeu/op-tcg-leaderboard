import pandas as pd
from pydantic import BaseModel, Field
from datetime import datetime
from enum import IntEnum

from op_tcg.backend.models.input import MetaFormat


class MatchResult(IntEnum):
    LOSE = 0
    DRAW = 1
    WIN = 2


class BQMatch(BaseModel):
    leader_id: str = Field(description="The op tcg leader id e.g. OP03-099")
    opponent_id: str = Field(description="The op tcg opponent id e.g. OP03-099")
    result: MatchResult = Field(description="Result of the match. Can be win, lose or draw")
    meta_format: MetaFormat = Field(description="Meta in which matches happened, e.g. OP06")
    official: bool = Field(default=False, description="Whether the match is originated from an official tournament")
    timestamp: datetime = Field(description="Approximate timestamp when the match happened")

class BQMatches(BaseModel):
    matches: list[BQMatch]

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([r.dict() for r in self.matches])

