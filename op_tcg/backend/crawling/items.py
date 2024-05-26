from dataclasses import dataclass
from op_tcg.backend.models.tournaments import Tournament, TournamentStanding
from op_tcg.backend.models.matches import Match


@dataclass
class TournamentItem:
    tournament: Tournament
    tournament_standings: list[TournamentStanding]
    matches: list[Match]