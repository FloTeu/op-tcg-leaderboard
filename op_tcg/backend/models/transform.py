from pydantic import BaseModel, Field

from op_tcg.backend.models.matches import MatchResult


class Transform2BQMatch(BaseModel):
    id: str
    is_reverse: bool = Field(description="Whether its the reverse match", default=False)
    leader_id: str
    opponent_id: str
    result: MatchResult
