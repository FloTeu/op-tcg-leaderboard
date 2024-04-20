import pandas as pd
from pydantic import BaseModel, Field
from datetime import datetime, date
from enum import IntEnum

from op_tcg.backend.models.input import MetaFormat


class MatchResult(IntEnum):
    LOSE = 0
    DRAW = 1
    WIN = 2


class BQMatch(BaseModel):
    id: str = Field(description="Unique id of single match. One match contains 2 rows, including one reverse match")
    leader_id: str = Field(description="The op tcg leader id e.g. OP03-099")
    opponent_id: str = Field(description="The op tcg opponent id e.g. OP03-099")
    result: MatchResult = Field(description="Result of the match. Can be win, lose or draw")
    meta_format: MetaFormat = Field(description="Meta in which matches happened, e.g. OP06")
    official: bool = Field(default=False, description="Whether the match is originated from an official tournament")
    is_reverse: bool = Field(description="Whether its the reverse match")
    timestamp: datetime = Field(description="Approximate timestamp when the match happened")

class BQMatches(BaseModel):
    matches: list[BQMatch]

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([r.dict() for r in self.matches])

class BQLeaderElo(BaseModel):
    leader_id: str = Field(description="The op tcg leader id e.g. OP03-099")
    elo: int = Field(description="Elo rating of leader until a certain time/ meta format")
    only_official: bool = Field(default=False, description="Whether the matches are only originated from "
                                                           "official tournaments")
    meta_format: MetaFormat = Field(description="Meta until or in which the elo is calculated")
    start_date: date = Field(description="Date in which the elo calculation started")
    end_date: date = Field(description="Date in which the elo calculation ended")

class BQLeaderElos(BaseModel):
    elo_ratings: list[BQLeaderElo]

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([r.dict() for r in self.elo_ratings])