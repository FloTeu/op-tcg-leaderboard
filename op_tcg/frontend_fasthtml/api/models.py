from pydantic import BaseModel, field_validator
from typing import List, Optional, Any
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.leader import LeaderboardSortBy
from op_tcg.backend.models.cards import OPTcgColor, OPTcgCardCatagory, OPTcgAbility, CardCurrency, OPTcgAttribute


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
    ascending: bool = False
    
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
    """Parameters for leader data requests"""
    lid: Optional[str] = None
    similar_lid: Optional[str] = None
    meta_format: list[MetaFormat]
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


class TournamentPageParams(BaseModel):
    """Parameters for tournament page requests"""
    meta_format: list[MetaFormat]
    region: MetaFormatRegion = MetaFormatRegion.ALL
    
    @field_validator('meta_format', mode='before')
    def validate_meta_formats(cls, value):
        if value is None or (isinstance(value, list) and len(value) == 0):
            return [MetaFormat.latest_meta_format()]
        if isinstance(value, list):
            return [MetaFormat(item) if isinstance(item, str) else item for item in value]
        return [MetaFormat(value) if isinstance(value, str) else value]
    
    @field_validator('region', mode='before')
    def validate_region(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str):
            return MetaFormatRegion(value)
        return value


class MatchupParams(BaseModel):
    """Parameters for matchup page requests"""
    meta_format: list[MetaFormat]
    leader_ids: list[str]
    only_official: bool = True
    
    @field_validator('meta_format', mode='before')
    def validate_meta_formats(cls, value):
        if value is None or (isinstance(value, list) and len(value) == 0):
            return [MetaFormat.latest_meta_format()]
        if isinstance(value, list):
            return [MetaFormat(item) if isinstance(item, str) else item for item in value]
        return [MetaFormat(value) if isinstance(value, str) else value]
    
    @field_validator('leader_ids', mode='before')
    def validate_leader_ids(cls, value):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]
    
    @field_validator('only_official', mode='before')
    def validate_only_official(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str):
            return value.lower() in ("true", "on", "1", "yes")
        return bool(value)


class CardPopularityParams(BaseModel):
    """Parameters for card popularity page requests"""
    meta_format: MetaFormat = MetaFormat.latest_meta_format()
    card_colors: List[OPTcgColor] = OPTcgColor.to_list()
    card_attributes: Optional[List[OPTcgAttribute]] = None
    card_counter: Optional[int] = None
    card_category: List[OPTcgCardCatagory] = None
    card_types: Optional[List[str]] = None
    currency: CardCurrency = CardCurrency.EURO
    min_price: float = 0
    max_price: float = 80
    min_cost: int = 0
    max_cost: int = 10
    min_power: int = 0
    max_power: int = 15
    card_abilities: Optional[List[OPTcgAbility]] = None
    ability_text: Optional[str] = None
    filter_operator: str = "OR"
    page: int = 1

    @field_validator('meta_format', mode='before')
    def validate_meta_format(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str):
            return MetaFormat(value)
        return value

    @field_validator('card_colors', mode='before')
    def validate_card_colors(cls, value):
        if value is None:
            return OPTcgColor.to_list()
        if isinstance(value, list):
            return [OPTcgColor(item) if isinstance(item, str) else item for item in value]
        return [OPTcgColor(value) if isinstance(value, str) else value]

    @field_validator('card_attributes', mode='before')
    def validate_card_attributes(cls, value):
        if value is None:
            return None
        if isinstance(value, list):
            return [OPTcgAttribute(item) if isinstance(item, str) else item for item in value]
        return [OPTcgAttribute(value) if isinstance(value, str) else value]

    @field_validator('card_counter', mode='before')
    def validate_card_counter(cls, value):
        if value is None or value == "" or value == "Any":
            return None
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str):
            try:
                return int(value)
            except (ValueError, TypeError):
                return None
        return value

    @field_validator('card_category', mode='before')
    def validate_card_category(cls, value):
        if value is None or value == "" or value == "Any":
            return [cat for cat in OPTcgCardCatagory.to_list() if cat != OPTcgCardCatagory.LEADER]
        if isinstance(value, list):
            return [OPTcgCardCatagory(item) if isinstance(item, str) else item for item in value]
        return [OPTcgCardCatagory(value) if isinstance(value, str) else value]

    @field_validator('currency', mode='before')
    def validate_currency(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str):
            return CardCurrency(value)
        return value

    @field_validator('min_price', 'max_price', mode='before')
    def validate_price(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str):
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0.0
        return value if value is not None else 0.0

    @field_validator('min_cost', 'max_cost', 'min_power', 'max_power', mode='before')
    def validate_int_fields(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str):
            try:
                return int(value)
            except (ValueError, TypeError):
                return 0
        return value if value is not None else 0

    @field_validator('card_abilities', mode='before')
    def validate_card_abilities(cls, value):
        if value is None:
            return None
        if isinstance(value, list):
            return [OPTcgAbility(item) if isinstance(item, str) else item for item in value]
        return [OPTcgAbility(value) if isinstance(value, str) else value]

    @field_validator('ability_text', mode='before')
    def validate_ability_text(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        return value

    @field_validator('filter_operator', mode='before')
    def validate_filter_operator(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        if value not in ["OR", "AND"]:
            return "OR"
        return value

    @field_validator('page', mode='before')
    def validate_page(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str):
            try:
                return max(1, int(value))
            except (ValueError, TypeError):
                return 1
        return max(1, value if value is not None else 1)

    @field_validator('card_types', mode='before')
    def validate_card_types(cls, value):
        if value is None or value == "" or value == "Any":
            return None
        if isinstance(value, list):
            return value
        return [value]