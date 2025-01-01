from pydantic import Field, field_validator
from datetime import datetime
from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.backend.models.bq_classes import BQTableBaseModel
from op_tcg.backend.models.input import MetaFormat, CountryMetaFormat
from op_tcg.backend.models.tournaments import TournamentRecord


class Decklist(BQTableBaseModel):
    _dataset_id: str = BQDataset.MATCHES
    id: str = Field(description="Unique id of the decklist.", primary_key=True)
    leader_id: str = Field(description="The op tcg leader id e.g. OP03-099")
    decklist: dict[str, int] = Field(description="Used decklist in this tournament. The key is the card id e.g. OP01-006 and the value is the number of cards in the deck")
    meta_format: MetaFormat = Field(description="Meta in which decklist was used.")
    country_meta_format: CountryMetaFormat = Field(description="The country area, which defines which meta format is available")
    country: str | None = Field(description="Country of match were decklist was used.")

    @field_validator('decklist', mode="before")
    def parse_dicts(cls, value):
        if isinstance(value, str):
            return cls.str2dict(value)
        elif isinstance(value, dict) or value is None:
            return value
        else:
            raise ValueError("decklist must be a dictionary or a string that represents a dictionary")

class OpTopDeckDecklist(BQTableBaseModel):
    _dataset_id: str = BQDataset.MATCHES
    decklist_id: str = Field(description="Reference to decklist table.", primary_key=True)
    tournament_id: str = Field(description="Reference to tournament table.", primary_key=True)
    deck_name: str = Field(description="Name of the decklist. Usually meta format + leader name")
    author: str = Field(description="Name of the author how uploaded the decklist")
    tournament_name: str = Field(description="Name of the tournament")
    host: str = Field(description="Tournament organizer")
    placing_text: str | None = Field(description="The decklist's final placing in the tournament.")
    placing: int | None = Field(description="If possible, the transformed placing text into a real placing number.")
    record: TournamentRecord | None = Field(description="Contains the number of wins, losses and ties the player finished with.")
    num_players: int = Field(description="Number of players that participated in the tournament", alias="players")
    decklist_source: str | None = Field(description="Link to the source url of the decklist.")


class OpTopDeckDecklistExtended(OpTopDeckDecklist, Decklist):
    pass