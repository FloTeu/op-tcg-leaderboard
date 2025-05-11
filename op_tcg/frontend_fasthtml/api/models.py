from pydantic import BaseModel, field_validator
from typing import List, Optional, Any
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.leader import LeaderboardSortBy


class LeaderboardFilter(BaseModel):
    meta_format: MetaFormat = MetaFormat.latest_meta_format
    release_meta_formats: Optional[List[MetaFormat]] = None
    region: MetaFormatRegion = MetaFormatRegion.ALL
    only_official: bool = True
    min_matches: int = 0
    max_matches: int = 10000
    
    @field_validator('meta_format', mode='before')
    def validate_meta_format(cls, value):
        if isinstance(value, list) and value:
            # If a list is passed, take the first value
            value = value[0]
        if isinstance(value, str):
            return MetaFormat(value)
        return value
    
    @field_validator('release_meta_formats', mode='before')
    def validate_release_meta_formats(cls, value):
        if value is None:
            return None
        if isinstance(value, list):
            return [MetaFormat(item) if isinstance(item, str) else item for item in value]
        # If it's a single value, convert to a list
        return [MetaFormat(value) if isinstance(value, str) else value]
    
    @field_validator('region', mode='before')
    def validate_region(cls, value):
        if isinstance(value, list) and value:
            # If a list is passed, take the first value
            value = value[0]
        if isinstance(value, str):
            return MetaFormatRegion(value)
        return value
    
    @field_validator('only_official', mode='before')
    def validate_only_official(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str):
            return value.lower() in ("true", "on", "1", "yes")
        return bool(value)
    
    @field_validator('min_matches', 'max_matches', mode='before')
    def validate_int_fields(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str):
            try:
                return int(value)
            except (ValueError, TypeError):
                return 0
        return value if value is not None else 0


class LeaderboardSort(BaseModel):
    sort_by: LeaderboardSortBy = LeaderboardSortBy.WIN_RATE
    meta_format: MetaFormat = MetaFormat.latest_meta_format
    
    @field_validator('sort_by', mode='before')
    def validate_sort_by(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str):
            return LeaderboardSortBy(value)
        return value
    
    @field_validator('meta_format', mode='before')
    def validate_meta_format(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str):
            return MetaFormat(value)
        return value


class LeaderSelectParams(BaseModel):
    meta_format: Optional[List[MetaFormat]] = None
    lid: Optional[str] = None
    
    @field_validator('meta_format', mode='before')
    def validate_meta_formats(cls, value):
        if value is None or (isinstance(value, list) and len(value) == 0):
            return [MetaFormat.latest_meta_format()]
        if isinstance(value, list):
            return [MetaFormat(item) if isinstance(item, str) else item for item in value]
        return [MetaFormat(value) if isinstance(value, str) else value]
    
    @field_validator('lid', mode='before')
    def validate_lid(cls, value):
        if isinstance(value, list) and value:
            return value[0]
        return value


class LeaderDataParams(BaseModel):
    meta_format: Optional[List[MetaFormat]] = None
    lid: Optional[str] = None
    only_official: bool = True
    
    @field_validator('meta_format', mode='before')
    def validate_meta_formats(cls, value):
        if value is None or (isinstance(value, list) and len(value) == 0):
            return [MetaFormat.latest_meta_format()]
        if isinstance(value, list):
            return [MetaFormat(item) if isinstance(item, str) else item for item in value]
        return [MetaFormat(value) if isinstance(value, str) else value]
    
    @field_validator('lid', mode='before')
    def validate_lid(cls, value):
        if isinstance(value, list) and value:
            return value[0]
        return value
    
    @field_validator('only_official', mode='before')
    def validate_only_official(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str):
            return value.lower() in ("true", "on", "1", "yes")
        return bool(value)


class Matchup(BaseModel):
    leader_id: str
    win_rate: float
    total_matches: int
    meta_formats: list[MetaFormat]
    win_rate_chart_data: dict[MetaFormat, float]


class OpponentMatchups(BaseModel):
    easiest_matchups: list[Matchup]
    hardest_matchups: list[Matchup]