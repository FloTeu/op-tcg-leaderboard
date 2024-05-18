import pandas as pd
from pydantic import BaseModel, Field
from datetime import datetime, date
from enum import IntEnum

from op_tcg.backend.models.common import DataSource
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.base import BQTableBaseModel


class MatchResult(IntEnum):
    LOSE = 0
    DRAW = 1
    WIN = 2


class Match(BQTableBaseModel):
    id: str = Field(description="Unique id of single match. One match contains 2 rows, including one reverse match", primary_key=True)
    leader_id: str = Field(description="The op tcg leader id e.g. OP03-099")
    opponent_id: str = Field(description="The op tcg opponent leader id e.g. OP03-099")
    result: MatchResult = Field(description="Result of the match. Can be win, lose or draw")
    meta_format: MetaFormat = Field(description="Meta in which matches happened, e.g. OP06")
    official: bool = Field(default=False, description="Whether the match is originated from an official tournament")
    is_reverse: bool = Field(description="Whether its the reverse match", primary_key=True)
    source: DataSource | str = Field(description="Origin of the match. In case of an unofficial match it can be the session id.")
    tournament_id: str | None = Field(None, description="Unique id of single tournament")
    tournament_round: int | None = Field(None, description="Round during which the match happened.", alias="round")
    tournament_phase: int | None = Field(None, description="Phase during which the match happened.", alias="phase")
    tournament_table: int | None = Field(None, description="Table number of the match (for all phase types except live brackets).", alias="table")
    tournament_match: int | None = Field(None, description="Match label, used in live brackets to identify where in the bracket it happened.", alias="match")
    player_id: str | None = Field(None, description="Username/ID used to uniquely identify the player. Does not change between tournaments.")
    opponent_player_id: str | None = Field(None, description="Username/ID used to uniquely identify the opponent. Does not change between tournaments.")
    match_timestamp: datetime = Field(description="Approximate timestamp when the match happened")
    create_timestamp: datetime = Field(default_factory=datetime.now, description="Creation timestamp when the insert in BQ happened")

class BQMatches(BaseModel):
    matches: list[Match]

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([r.dict() for r in self.matches])

class LeaderElo(BQTableBaseModel):
    meta_format: MetaFormat = Field(description="Meta until or in which the elo is calculated", primary_key=True)
    leader_id: str = Field(description="The op tcg leader id e.g. OP03-099", primary_key=True)
    only_official: bool = Field(default=False, description="Whether the matches are only originated from "
                                                           "official tournaments", primary_key=True)
    elo: int = Field(description="Elo rating of leader until a certain time/ meta format")
    start_date: date = Field(description="Date in which the elo calculation started")
    end_date: date = Field(description="Date in which the elo calculation ended")

class BQLeaderElos(BaseModel):
    elo_ratings: list[LeaderElo]

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([r.dict() for r in self.elo_ratings])