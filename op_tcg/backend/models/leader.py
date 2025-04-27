from datetime import date
from enum import StrEnum

from pydantic import Field

from op_tcg.backend.models.base import EnumBase
from op_tcg.backend.models.cards import OPTcgColor, OPTcgAttribute, OPTcgLanguage, Card
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.backend.models.bq_classes import BQTableBaseModel
from op_tcg.backend.utils.color_fns import average_hex_colors


class Leader(Card):
    _dataset_id: str = BQDataset.LEADERS
    aa_image_url: str = Field(description="Public accessible url to alternative artwork image")
    meta_format: MetaFormat | None = Field(description="Meta in which leader was released. None if release date is not known, e.g. Prize Cards")


class LeaderElo(BQTableBaseModel):
    _dataset_id: str = BQDataset.LEADERS
    meta_format: MetaFormat = Field(description="Meta until or in which the elo is calculated", primary_key=True)
    leader_id: str = Field(description="The op tcg leader id e.g. OP03-099", primary_key=True)
    only_official: bool = Field(default=False, description="Whether the matches are only originated from "
                                                           "official tournaments", primary_key=True)
    elo: int = Field(description="Elo rating of leader until a certain time/ meta format")
    start_date: date = Field(description="Date in which the elo calculation started")
    end_date: date = Field(description="Date in which the elo calculation ended")


class TournamentWinner(BQTableBaseModel):
    _dataset_id: str = BQDataset.LEADERS
    meta_format: MetaFormat = Field(description="Meta until or in which the elo is calculated", primary_key=True)
    leader_id: str = Field(description="The op tcg leader id e.g. OP03-099", primary_key=True)
    win_count: int = Field(description="Number of total tournament wins in meta format")
    only_official: bool = Field(default=False, description="Whether the matches are only originated from "
                                                           "official tournaments", primary_key=True)
    meta_format_region: MetaFormatRegion = Field(description="The country area, which defines which meta format is available")

class LeaderExtended(Leader):
    _dataset_id = BQDataset.LEADERS
    release_meta_format: MetaFormat | None = Field(description="Meta in which leader was released. None if release date is not known, e.g. Prize Cards")
    meta_format: MetaFormat | None = Field(description="Meta in which win rate and elo as calculated. None if no data is available")
    tournament_wins: int = Field(description="Number of tournament the leader won in the meta_format")
    win_rate: float | None = Field(description="Win rate as float value between 0 and 1, where 1 is 100% win rate. If not matches happened win_rate is NULL")
    total_matches: int | None = Field(description="Number of matches between leader and opponent. If not matches happened win_rate is NULL")
    elo: int | None = Field(description="Elo rating of leader until a certain time/ meta format. None if no elo is calculated")
    d_score: float | None = Field(description="Composite score from multiple metrics defining the dominance a leader has in the selected meta")
    only_official: bool | None = Field(default=False, description="Whether the matches are only originated from official tournaments. None, if no data si available", primary_key=True)
    meta_format_region: MetaFormatRegion | None = Field(description="The country area, which defines which meta format is available")


class LeaderboardSortBy(EnumBase, StrEnum):
    DOMINANCE_SCORE = "D-Score"
    TOURNAMENT_WINS = "Tournament Wins"
    WIN_RATE = "Win Rate"
    ELO = "Elo"
