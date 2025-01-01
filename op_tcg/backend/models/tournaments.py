from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
from enum import StrEnum

from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.backend.models.bq_classes import BQTableBaseModel
from op_tcg.backend.models.input import MetaFormat, CountryMetaFormat
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

class Tournament(BQTableBaseModel):
    _dataset_id: str = BQDataset.MATCHES
    id: str = Field(description="Unique id of single tournament. Limitless id or custom made id in case of op-top-decks", primary_key=True)
    name: str = Field(description="Tournament name set by the organizer. For op-top-decks its the host.")
    num_players: int | None = Field(description="Number of players that participated in the tournament", alias="players")
    decklists: bool = Field(description="Indicates whether the tournament used decklist / teamlist submission")
    is_public: bool | None = Field(description="Indicates whether the tournament is listed publicly (otherwise accessible through direct link only)", alias="isPublic")
    is_online: bool | None = Field(description="Set to true if the tournament is played online, false if it's an in-person event", alias="isOnline")
    phases: list[TournamentPhase] | None = Field(description="The tournament structure as an array of objects, one per phase")
    meta_format: MetaFormat | str = Field(description="Meta in which tournament happened, e.g. OP06")
    country_meta_format: CountryMetaFormat | None = Field(CountryMetaFormat.WEST, description="The country area, which defines which meta format is available")
    official: bool = Field(default=False, description="Whether the tournament is official, i.e. comes from a official source")
    source: DataSource | str = Field(description="Origin of the tournament. In case of an unofficial match it can be the session id.")
    tournament_timestamp: datetime = Field(description="Scheduled tournament start set by the organizer.", alias="date")

    @field_validator('phases', mode="before")
    def parse_phases(cls, value):
        phases_parsed = []
        for phase in value:
            if isinstance(phase, dict):
                phases_parsed.append(phase)
            elif isinstance(phase, str):
                phases_parsed.append(cls.str2dict(phase))
            else:
                raise NotImplementedError
        return phases_parsed


class TournamentRecord(BaseModel):
    wins: int
    losses: int
    ties: int

class TournamentStanding(BQTableBaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )

    _dataset_id: str = BQDataset.MATCHES
    tournament_id: str = Field(description="Unique id of single tournament", primary_key=True)
    player_id: str = Field(description="Username/ID used to uniquely identify the player. Does not change between tournaments.", alias="player", primary_key=True)
    name: str = Field(description="Display name chosen by the player, can change between tournaments")
    country: str | None = Field(description="ISO alpha-2 code of the player's country, as selected by them.")
    placing: int | None = Field(description="The player's final placing in the tournament.")
    record: TournamentRecord = Field(description="Contains the number of wins, losses and ties the player finished with.")
    leader_id: str | None = Field(description="The op tcg leader id e.g. OP03-099")
    decklist: dict[str, int] | None = Field(description="Used decklist in this tournament. The key is the card id e.g. OP01-006 and the value is the number of cards in the deck")
    drop: int | None = Field(description="If the player dropped from the tournament, this field contains the round during which they did so.")

    @field_validator('decklist', 'record', mode="before")
    def parse_dicts(cls, value):
        if isinstance(value, str):
            return cls.str2dict(value)
        elif isinstance(value, dict) or value is None:
            return value
        else:
            raise ValueError("decklist must be a dictionary or a string that represents a dictionary")

class TournamentStandingExtended(TournamentStanding, Tournament):
    pass

class TournamentDecklist(BQTableBaseModel):
    """Read only dataclass to extract data from BQ tables"""
    leader_id: str = Field(description="The op tcg leader id e.g. OP03-099")
    decklist: dict[str, int] = Field(description="Used decklist in this tournament. The key is the card id e.g. OP01-006 and the value is the number of cards in the deck")
    placing: int | None = Field(description="The player's final placing in the tournament.")
    player_id: str = Field(description="Username/ID used to uniquely identify the player. Does not change between tournaments.")
    meta_format: MetaFormat | str = Field(description="Meta in which tournament happened, e.g. OP06")
    tournament_timestamp: datetime = Field(description="Scheduled tournament start set by the organizer.")
    price_eur: float | None = Field(None, description="Sum of all card prices in decklist")
    price_usd: float | None = Field(None, description="Sum of all card prices in decklist")


    @field_validator('decklist', mode="before")
    def parse_dicts(cls, value):
        if isinstance(value, str):
            return cls.str2dict(value)
        elif isinstance(value, dict) or value is None:
            return value
        else:
            raise ValueError("decklist must be a dictionary or a string that represents a dictionary")