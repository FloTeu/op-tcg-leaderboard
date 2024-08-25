import time

import streamlit as st
from pydantic import BaseModel

from op_tcg.backend.models.cards import LatestCardPrice, ExtendedCardData
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.backend.models.tournaments import TournamentStandingExtended, TournamentDecklist
from op_tcg.frontend.utils.extract import get_card_data, get_tournament_standing_data, get_leader_extended, \
    get_tournament_decklist_data


class DecklistData(BaseModel):
    num_decklists: int
    avg_price_eur: float | None = None
    avg_price_usd: float | None = None
    card_id2occurrences: dict[str, int]
    card_id2occurrence_proportion: dict[str, float]
    card_id2total_count: dict[str, int]
    card_id2avg_count_card: dict[str, float]
    card_id2card_data: dict[str, LatestCardPrice]


def tournament_standings2decklist_data(tournament_standings: list[TournamentStandingExtended] | list[TournamentDecklist], card_id2card_data: dict[str, LatestCardPrice]) -> DecklistData:
    num_decklists = len(tournament_standings)
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
                        card_id2card_data={cid: cdata for cid, cdata in card_id2card_data.items() if cid in card_id2occurrences})


def get_card_id_card_data_lookup(aa_version: int = 0) -> dict[str, ExtendedCardData]:
    card_data = get_card_data()
    card_data = [cdata for cdata in card_data if cdata.aa_version == aa_version]
    return {card.id: card for card in card_data}


@st.cache_data
def get_leader_decklist_card_ids(leader_id: str, selected_meta_formats: list[MetaFormat], occurrence_threshold: float = 0.02) -> list[str]:
    card_id2card_data = get_card_id_card_data_lookup()
    tournament_decklists: list[TournamentDecklist] = get_tournament_decklist_data(
        meta_formats=selected_meta_formats, leader_ids=[leader_id])
    decklist_data: DecklistData = tournament_standings2decklist_data(tournament_decklists, card_id2card_data)
    return decklist_data_to_card_ids(decklist_data, occurrence_threshold=occurrence_threshold)

def decklist_data_to_card_ids(decklist_data: DecklistData, occurrence_threshold: float = 0.0, exclude_card_ids: list[str] | None = None) -> list[str]:
    exclude_card_ids = exclude_card_ids or []
    card_ids_sorted = sorted(decklist_data.card_id2occurrence_proportion.keys(),
                             key=lambda d: decklist_data.card_id2occurrences[d], reverse=True)
    def filter_fn(card_id) -> bool:
        conditions = []
        if exclude_card_ids:
            conditions.append(card_id not in exclude_card_ids)
        if occurrence_threshold:
            conditions.append(decklist_data.card_id2occurrence_proportion[card_id] >= occurrence_threshold)
        return all(conditions)

    return list(filter(lambda x: filter_fn(x), card_ids_sorted))

def get_most_similar_leader_ids(leader_id: str, meta_formats: list[MetaFormat]) -> dict[str, float]:
    """
    Calculates the similarity score for each leader combination of the same color.
    The higher the score the more cards are in common.
    returns: dict where the key is a leader_id and the value is a similarity score between 0 and 1
    """

    def calculate_similarity_score(decklist_data: DecklistData, compare_decklist_data: DecklistData) -> float:
        intersection = set(decklist_data.card_id2occurrence_proportion.keys()).intersection(set(compare_decklist_data.card_id2occurrence_proportion.keys()))
        return len(intersection) / len(decklist_data.card_id2occurrence_proportion)

    t1 = time.time()
    card_id2card_data = get_card_id_card_data_lookup()
    leader_extended_data: list[LeaderExtended] = get_leader_extended()
    leader_colors = list(filter(lambda x: x.id == leader_id, leader_extended_data))[0].colors
    # drop selected leader_id and all leaders with different color
    other_leader_ids = list(dict.fromkeys([l.id for l in leader_extended_data if (any(c in l.colors for c in leader_colors)) and (l.id != leader_id)]))
    lid2similarity_score: dict[str, float] = {}
    tournament_decklists: list[TournamentDecklist] = get_tournament_decklist_data(
        meta_formats=meta_formats, leader_ids=[leader_id] + other_leader_ids)
    print(f"data load elapsed time %.2f" % (time.time() - t1))

    decklist_data: DecklistData = tournament_standings2decklist_data([td for td in tournament_decklists if td.leader_id == leader_id], card_id2card_data)

    for lid in other_leader_ids:
        tournament_decklist_filtered = [td for td in tournament_decklists if td.leader_id == lid]
        t1 = time.time()
        compare_decklist_data = tournament_standings2decklist_data(tournament_decklist_filtered, card_id2card_data)
        print(f"{lid} elapsed time %.2f" % (time.time() - t1))
        lid2similarity_score[lid] = calculate_similarity_score(decklist_data, compare_decklist_data)
    return lid2similarity_score
