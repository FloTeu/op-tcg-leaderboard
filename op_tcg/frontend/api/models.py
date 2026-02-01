from pydantic import BaseModel, field_validator
from typing import List, Optional, Any
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.leader import LeaderboardSortBy
from op_tcg.backend.models.cards import OPTcgColor, OPTcgCardCatagory, OPTcgAbility, CardCurrency, OPTcgAttribute, OPTcgCardRarity


class MetaFormatParams(BaseModel):
    """Parameters for matchup page requests"""
    meta_format: list[MetaFormat]
    only_official: bool = True
    
    @field_validator('meta_format', mode='before')
    def validate_meta_formats(cls, value):
        if value is None or (isinstance(value, list) and len(value) == 0):
            return [MetaFormat.latest_meta_format()]
        if isinstance(value, list):
            return [MetaFormat(item) if isinstance(item, str) else item for item in value]
        return [MetaFormat(value) if isinstance(value, str) else value]
    
    @field_validator('only_official', mode='before')
    def validate_only_official(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str):
            return value.lower() in ("true", "on", "1", "yes")
        return bool(value)
    

class LeaderboardFilter(BaseModel):
    meta_format: MetaFormat = MetaFormat.latest_meta_format
    release_meta_formats: Optional[List[MetaFormat]] = None
    region: MetaFormatRegion = MetaFormatRegion.ALL
    only_official: bool = True
    min_matches: int = 0
    max_matches: int = 10000
    min_price: float = 0.0
    max_price: float = 300.0

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


class LeaderDataParams(BaseModel):
    """Parameters for leader data requests"""
    lid: Optional[str] = None
    similar_lid: Optional[str] = None
    meta_format: list[MetaFormat]
    only_official: bool = True
    region: Optional[MetaFormatRegion] = MetaFormatRegion.ALL
    min_matches: int = 4

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
    
    @field_validator('region', mode='before')
    def validate_region(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str):
            return MetaFormatRegion(value)
        return value or MetaFormatRegion.ALL

    @field_validator('min_matches', mode='before')
    def validate_min_matches(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return 4
        return value if value is not None else 4


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
    min_matches: int = 0
    max_matches: int | None = None
    
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
    
    @field_validator('min_matches', 'max_matches', mode='before')
    def validate_matches(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str):
            return int(value)
        return value if value is not None else None


class MatchupParams(MetaFormatParams):
    """Parameters for matchup page requests"""
    leader_ids: list[str] | None = None
    
    @field_validator('leader_ids', mode='before')
    def validate_leader_ids(cls, value):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]


class CardPopularityParams(BaseModel):
    """Parameters for card popularity page requests"""
    meta_format: MetaFormat = MetaFormat.latest_meta_format()
    card_colors: List[OPTcgColor] = OPTcgColor.to_list()
    card_attributes: Optional[List[OPTcgAttribute]] = None
    card_counter: Optional[int] = None
    card_category: List[OPTcgCardCatagory] = [cat for cat in OPTcgCardCatagory.to_list() if cat != OPTcgCardCatagory.LEADER]
    card_types: Optional[List[str]] = None
    currency: CardCurrency = CardCurrency.EURO
    min_price: float = 0
    max_price: float = 80
    min_cost: int = 0
    max_cost: int = 10
    min_power: int = 0
    max_power: int = 15
    card_abilities: Optional[List[OPTcgAbility]] = None
    card_rarity: Optional[List[OPTcgCardRarity]] = None
    ability_text: Optional[str] = None
    filter_operator: str = "OR"
    page: int = 1
    search_term: Optional[str] = None
    release_meta_format: Optional[MetaFormat] = None

    @field_validator('search_term', mode='before')
    def validate_search_term(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        return value

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
    def validate_optional_int_lists(cls, value):
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

    @field_validator('release_meta_format', mode='before')
    def validate_release_meta_format(cls, value):
        if value is None or value == "" or value == "Any":
            return None
        return value

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

    @field_validator('card_rarity', mode='before')
    def validate_card_rarity(cls, value):
        if value is None:
            return None
        if isinstance(value, list):
            return [OPTcgCardRarity(item) if isinstance(item, str) else item for item in value]
        return [OPTcgCardRarity(value) if isinstance(value, str) else value]

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


class PriceOverviewParams(BaseModel):
    """Parameters for card price overview requests"""
    currency: CardCurrency = CardCurrency.EURO
    start_date: Optional[int] = None
    end_date: Optional[int] = None
    min_latest_price: float = 0.0
    max_latest_price: Optional[float] = None
    max_results: int = 20
    include_alt_art: bool = False
    rarity: Optional[str] = None
    order_by: str = "rising"  # rising | fallers | expensive
    change_metric: str = "absolute"  # absolute | relative
    page: int = 1
    query: Optional[str] = None

    @field_validator('currency', mode='before')
    def validate_currency(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str):
            return CardCurrency(value)
        return value

    @field_validator('start_date', 'end_date', mode='before')
    def validate_dates(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str):
            try:
                return int(float(value))
            except (ValueError, TypeError):
                return None
        return value

    @field_validator('max_results', mode='before')
    def validate_ints(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str):
            try:
                return int(value)
            except (ValueError, TypeError):
                return 0
        return value if value is not None else 0

    @field_validator('min_latest_price', mode='before')
    def validate_min_price(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str):
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0.0
        return value if value is not None else 0.0

    @field_validator('max_latest_price', mode='before')
    def normalize_max_price(cls, value):
        # Treat slider max (500) as no upper bound (None)
        if isinstance(value, list) and value:
            value = value[-1]
        if value is None or value == "":
            return None
        try:
            v = float(value)
            return None if v >= 500 else v
        except (ValueError, TypeError):
            return None

    @field_validator('include_alt_art', mode='before')
    def validate_bool(cls, value):
        if isinstance(value, list) and value:
            # If both hidden(false) and checkbox(true) are sent, take the last occurrence
            value = value[-1]
        if isinstance(value, str):
            return value.lower() in ("true", "on", "1", "yes")
        return bool(value)

    @field_validator('order_by', mode='before')
    def validate_order_by(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        if not value:
            return "rising"
        v = str(value).lower()
        return v if v in ("rising", "fallers", "expensive", "diff_eur_high", "diff_usd_high") else "rising"

    @field_validator('change_metric', mode='before')
    def validate_change_metric(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        v = (value or "absolute").lower()
        return v if v in ("absolute", "relative") else "absolute"

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

    @field_validator('rarity', mode='before')
    def validate_rarity(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        if value == "All":
            return None
        return value

