from dataclasses import dataclass

from op_tcg.backend.models.cards import OPTcgLanguage, CardReleaseSet, Card
from op_tcg.backend.models.tournaments import Tournament, TournamentStanding
from op_tcg.backend.models.matches import Match


@dataclass
class TournamentItem:
    tournament: Tournament
    tournament_standings: list[TournamentStanding]
    matches: list[Match]


@dataclass
class ReleaseSetItem:
    release_set: CardReleaseSet\

@dataclass
class CardsItem:
    cards: list[Card]


@dataclass
class LimitlessPriceRow:
    card_id: str
    aa_version: int
    language: OPTcgLanguage
    name: str
    card_category: str
    rarity: str
    price_usd: float | None
    price_eur: float | None
