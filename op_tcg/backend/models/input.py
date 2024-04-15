from enum import StrEnum

from pydantic import BaseModel, Field

class MetaFormat(StrEnum):
    OP01 = "OP01"
    OP02 = "OP02"
    OP03 = "OP03"
    OP04 = "OP04"
    OP05 = "OP05"
    OP06 = "OP06"


class LimitlessMatch(BaseModel):
    leader_name: str = Field(description="The op tcg leader name")
    leader_id: str = Field(description="The op tcg leader id e.g. OP03-099")
    num_matches: int = Field(description="Total number of matches")
    score_win: int = Field(description="Number of matches won. its the first digit of the score string e.g. 31 - 35 - 0 -> 31")
    score_lose: int = Field(description="Number of matches lost. its the second digit of the score string e.g. 31 - 35 - 0 -> 35")
    score_draw: int = Field(description="Number of matches draw. its the third digit of the score string e.g. 31 - 35 - 0 -> 0")
    win_rate: float = Field(description="Ratio of games won. Number should be between 0 and 1.")


class LimitlessLeaderMetaMatches(BaseModel):
    leader_id: str = Field(description="The op tcg leader id e.g. OP03-099")
    meta_format: MetaFormat = Field(description="Meta in which matches happened, e.g. OP06")
    matches: list[LimitlessMatch] = Field(description="List of matches between this leader with all others")

