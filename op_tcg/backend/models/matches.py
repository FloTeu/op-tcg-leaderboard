import pandas as pd
from pydantic import BaseModel, Field
from datetime import datetime, date
from enum import IntEnum, StrEnum

from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.backend.models.bq_classes import BQTableBaseModel
from op_tcg.backend.models.common import DataSource
from op_tcg.backend.models.input import MetaFormat


class MatchResult(IntEnum):
    LOSE = 0
    DRAW = 1
    WIN = 2


class Match(BQTableBaseModel):
    _dataset_id: str = BQDataset.MATCHES
    id: str = Field(description="Unique id of single match. One match contains 2 rows, including one reverse match", primary_key=True)
    leader_id: str = Field(description="The op tcg leader id e.g. OP03-099")
    opponent_id: str = Field(description="The op tcg opponent leader id e.g. OP03-099")
    result: MatchResult = Field(description="Result of the match. Can be win, lose or draw")
    meta_format: MetaFormat | str = Field(description="Meta in which matches happened, e.g. OP06")
    official: bool = Field(default=False, description="Whether the match is originated from an official tournament")
    is_reverse: bool = Field(description="Whether its the reverse match", primary_key=True)
    source: DataSource | str = Field(description="Origin of the match. In case of an unofficial match it can be the session id.")
    tournament_id: str | None = Field(None, description="Unique id of single tournament")
    tournament_round: int | None = Field(None, description="Round during which the match happened.", alias="round")
    tournament_phase: int | None = Field(None, description="Phase during which the match happened.", alias="phase")
    tournament_table: str | None = Field(None, description="Table number of the match (for all phase types except live brackets).", alias="table")
    tournament_match: str | None = Field(None, description="Match label, used in live brackets to identify where in the bracket it happened.", alias="match")
    player_id: str | None = Field(None, description="Username/ID used to uniquely identify the player. Does not change between tournaments.")
    opponent_player_id: str | None = Field(None, description="Username/ID used to uniquely identify the opponent. Does not change between tournaments.")
    match_timestamp: datetime = Field(description="Approximate timestamp when the match happened")

class BQMatches(BaseModel):
    matches: list[Match]

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([r.dict() for r in self.matches])

class LeaderWinRate(BQTableBaseModel):
    _dataset_id: str = BQDataset.MATCHES
    meta_format: MetaFormat = Field(description="Meta until or in which the elo is calculated", primary_key=True)
    leader_id: str = Field(description="The op tcg leader id e.g. OP03-099", primary_key=True)
    opponent_id: str = Field(description="The op tcg opponent leader id e.g. OP03-099", primary_key=True)
    win_rate: float = Field(description="Win rate as float value between 0 and 1, where 1 is 100% win rate")
    total_matches: int = Field(description="Number of matches between leader and opponent")
    only_official: bool = Field(default=False, description="Whether the matches are only originated from "
                                                           "official tournaments", primary_key=True)




