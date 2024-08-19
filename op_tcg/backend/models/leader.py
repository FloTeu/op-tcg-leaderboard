from datetime import date

from pydantic import Field
from op_tcg.backend.models.cards import OPTcgColor, OPTcgAttribute, OPTcgLanguage, Card
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.backend.models.bq_classes import BQTableBaseModel
from op_tcg.backend.utils.color_fns import average_hex_colors


class Leader(Card):
    _dataset_id: str = BQDataset.LEADERS
    aa_image_url: str = Field(description="Public accessible url to alternative artwork image")
    meta_format: MetaFormat | None = Field(description="Meta in which set was released. None if release date is not known, e.g. Prize Cards")


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
