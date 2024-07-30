from pydantic import BaseModel

from op_tcg.backend.models.cards import LatestCardPrice
from op_tcg.backend.models.tournaments import TournamentStandingExtended
from op_tcg.frontend.utils.extract import get_card_data


class DecklistData(BaseModel):
    num_decklists: int
    avg_price_eur: float | None = None
    avg_price_usd: float | None = None
    card_id2occurrences: dict[str, int]
    card_id2occurrence_proportion: dict[str, float]
    card_id2total_count: dict[str, int]
    card_id2avg_count_card: dict[str, float]
    card_id2card_data: dict[str, LatestCardPrice]


def tournament_standings2decklist_data(tournament_standings: list[TournamentStandingExtended]) -> DecklistData:
    num_decklists = len(tournament_standings)
    card_id2card_data = get_card_id_card_data_lookup()
    card_id2occurrences: dict[str, int] = {}
    card_id2occurrence_proportion: dict[str, float] = {}
    card_id2total_count: dict[str, int] = {}
    card_id2avg_count_card: dict[str, float] = {}
    for tournament_standing in tournament_standings:
        for card_id, count in tournament_standing.decklist.items():
            if card_id not in card_id2occurrences:
                card_id2occurrences[card_id] = 1
                card_id2total_count[card_id] = count
            else:
                card_id2occurrences[card_id] += 1
                card_id2total_count[card_id] += count

    for card_id, total_count in card_id2total_count.items():
        card_id2avg_count_card[card_id] = float("%.2f" % (total_count / card_id2occurrences[card_id]))
        card_id2occurrence_proportion[card_id] = card_id2occurrences[card_id] / num_decklists

    return DecklistData(num_decklists=num_decklists,
                        card_id2occurrences=card_id2occurrences,
                        card_id2occurrence_proportion=card_id2occurrence_proportion,
                        card_id2total_count=card_id2total_count,
                        card_id2avg_count_card=card_id2avg_count_card,
                        card_id2card_data=card_id2card_data)


def get_card_id_card_data_lookup(aa_version: int = 0) -> dict[str, LatestCardPrice]:
    card_data = get_card_data()
    card_data = [cdata for cdata in card_data if cdata.aa_version == aa_version]
    return {card.id: card for card in card_data}
