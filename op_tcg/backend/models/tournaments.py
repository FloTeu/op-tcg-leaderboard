from pydantic import BaseModel, Field
from datetime import datetime, date
from enum import IntEnum, StrEnum

from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.base import BQTableBaseModel
from op_tcg.backend.models.common import DataSource

class TournamentMode(StrEnum):
    BO1="BO1"
    BO3="BO3"
    BO5="BO5"


class TournamentPhase(BaseModel):
    phase: int = Field(description="Phase number")
    type: str = Field(description="Phase type, see organizer documentation for more details.")
    rounds: int = Field(description="Number of rounds in the phase. Note that live bracket phases are seen as 1 round internally.")
    mode: TournamentMode = Field(description="Number of games per match, BO1, BO3 or BO5.")

class TournamentRecord(BaseModel):
    wins: int
    losses: int
    ties: int

class Tournament(BQTableBaseModel):
    id: str = Field(description="Unique id of single tournament", primary_key=True)
    name: str = Field(description="Tournament name set by the organizer")
    num_players: int = Field(description="Number of players that participated in the tournament", alias="players")
    decklists: bool = Field(description="Indicates whether the tournament used decklist / teamlist submission")
    is_public: bool = Field(description="Indicates whether the tournament is listed publicly (otherwise accessible through direct link only)", alias="isPublic")
    is_online: bool = Field(description="Set to true if the tournament is played online, false if it's an in-person event", alias="isOnline")
    phases: list[TournamentPhase] = Field(description="The tournament structure as an array of objects, one per phase")
    meta_format: MetaFormat = Field(description="Meta in which tournament happened, e.g. OP06")
    official: bool = Field(default=False, description="Whether the tournament is official, i.e. comes from a official source")
    source: DataSource | str = Field(description="Origin of the tournament. In case of an unofficial match it can be the session id.")
    tournament_timestamp: datetime = Field(description="Scheduled tournament start set by the organizer.", alias="date")
    create_timestamp: datetime = Field(default_factory=datetime.now, description="Creation timestamp when the insert in BQ happened")

class TournamentStandings(BQTableBaseModel):
    tournament_id: str = Field(description="Unique id of single tournament", primary_key=True)
    player_id: str = Field(description="Username/ID used to uniquely identify the player. Does not change between tournaments.", primary_key=True)
    name: str = Field(description="Display name chosen by the player, can change between tournaments")
    country: str = Field(description="ISO alpha-2 code of the player's country, as selected by them.")
    placing: int = Field(description="The player's final placing in the tournament.")
    record: TournamentRecord = Field(description="Contains the number of wins, losses and ties the player finished with.")
    leader_id: str = Field(description="The op tcg leader id e.g. OP03-099")
    decklist: dict[str, int] = Field(description="Used decklist in this tournament. The key is the card id e.g. OP01-006 and the value is the number of cards in the deck")
    drop: int | None = Field(description="If the player dropped from the tournament, this field contains the round during which they did so.")



