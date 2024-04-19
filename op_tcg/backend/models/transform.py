from pydantic import BaseModel

from op_tcg.backend.models.matches import MatchResult


class Transform2BQMatch(BaseModel):
    id: str
    leader_id: str
    opponent_id: str
    result: MatchResult
