import time
from contextlib import suppress

import streamlit as st
from pydantic import BaseModel, Field

from op_tcg.backend.models.cards import LatestCardPrice, ExtendedCardData, CardCurrency
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.backend.models.tournaments import TournamentStandingExtended, TournamentDecklist
from op_tcg.backend.utils.utils import timeit
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


class SimilarLeaderData(BaseModel):
    leader_id: str
    similarity_score: float
    cards_intersection: list[str] = Field(
        description="List of card ids available in both sets sorted by occurrence in similar leader decklists")
    cards_missing: list[str] = Field(
        description="List of card ids not available but required by similar leader sorted by occurrence")
    card_id2occurrence_proportion: dict[str, float]
    card_id2avg_count_card: dict[str, float]

def tournament_standings2decklist_data(
        tournament_standings: list[TournamentStandingExtended] | list[TournamentDecklist],
        card_id2card_data: dict[str, LatestCardPrice]) -> DecklistData:
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
                        card_id2card_data={cid: cdata for cid, cdata in card_id2card_data.items() if
                                           cid in card_id2occurrences})


def get_card_id_card_data_lookup(aa_version: int = 0, ensure_latest_price_not_null=True) -> dict[str, ExtendedCardData]:
    card_data = get_card_data()
    card_data = [cdata for cdata in card_data if cdata.aa_version == aa_version]
    if ensure_latest_price_not_null:
        for cdata in card_data:
            cdata.ensure_latest_price_not_none()
    return {card.id: card for card in card_data}


@st.cache_data
def get_leader_decklist_card_ids(leader_id: str, selected_meta_formats: list[MetaFormat],
                                 occurrence_threshold: float = 0.02) -> list[str]:
    card_id2card_data = get_card_id_card_data_lookup()
    tournament_decklists: list[TournamentDecklist] = get_tournament_decklist_data(
        meta_formats=selected_meta_formats, leader_ids=[leader_id])
    decklist_data: DecklistData = tournament_standings2decklist_data(tournament_decklists, card_id2card_data)
    return decklist_data_to_card_ids(decklist_data, occurrence_threshold=occurrence_threshold)


def decklist_data_to_card_ids(decklist_data: DecklistData, occurrence_threshold: float = 0.0,
                              exclude_card_ids: list[str] | None = None) -> list[str]:
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

def get_similar_leader_data(decklist_data: DecklistData, compare_decklist_data: DecklistData, leader_id: str,
                                compare_leader_id: str) -> SimilarLeaderData:
    """similarity score: How much of occurred cards in decklist_data is also available in other deck"""
    occurrence_list = []
    intersection = set(decklist_data.card_id2occurrence_proportion.keys()).intersection(
        set(compare_decklist_data.card_id2occurrence_proportion.keys()))
    max_occurrences = sum([occ for cid, occ in compare_decklist_data.card_id2occurrence_proportion.items() if
                           cid not in [leader_id, compare_leader_id]])
    for card_id, occurrence in compare_decklist_data.card_id2occurrence_proportion.items():
        if card_id in [leader_id, compare_leader_id]:
            continue
        if card_id in intersection:
            occurrence_list.append(occurrence)
    similarity_score = (sum(occurrence_list) / max_occurrences) if max_occurrences != 0 else 0
    intersection_sorted = sorted(list(intersection), key=lambda x: compare_decklist_data.card_id2occurrence_proportion[x], reverse=True)
    cards_missing = set(compare_decklist_data.card_id2occurrence_proportion.keys()) - set(decklist_data.card_id2occurrence_proportion.keys())
    with suppress(KeyError):
        cards_missing.remove(compare_leader_id)
    cards_missing_sorted = sorted(list(cards_missing), key=lambda x: compare_decklist_data.card_id2occurrence_proportion[x], reverse=True)
    return SimilarLeaderData(leader_id=compare_leader_id,
                             similarity_score=similarity_score,
                             cards_intersection=intersection_sorted,
                             cards_missing=cards_missing_sorted,
                             card_id2occurrence_proportion=compare_decklist_data.card_id2occurrence_proportion,
                             card_id2avg_count_card=compare_decklist_data.card_id2avg_count_card
                             )

@timeit
def get_most_similar_leader_data(leader_id: str, meta_formats: list[MetaFormat]) -> dict[str, SimilarLeaderData]:
    """
    Calculates the similarity score for each leader combination of the same color.
    The higher the score the more cards are in common.
    returns: dict where the key is a leader_id and the value is a similarity score between 0 and 1
    """
    card_id2card_data = get_card_id_card_data_lookup()
    leader_extended_data: list[LeaderExtended] = get_leader_extended()
    leader_colors = list(filter(lambda x: x.id == leader_id, leader_extended_data))[0].colors
    # drop selected leader_id and all leaders with different color
    other_leader_ids = list(dict.fromkeys([l.id for l in leader_extended_data if
                                           (any(c in l.colors for c in leader_colors)) and (l.id != leader_id)]))
    lid2sim_leader_data: dict[str, SimilarLeaderData] = {}
    tournament_decklists: list[TournamentDecklist] = get_tournament_decklist_data(
        meta_formats=meta_formats, leader_ids=[leader_id] + other_leader_ids)

    decklist_data: DecklistData = tournament_standings2decklist_data(
        [td for td in tournament_decklists if td.leader_id == leader_id], card_id2card_data)

    for lid in other_leader_ids:
        tournament_decklist_filtered = [td for td in tournament_decklists if td.leader_id == lid]
        compare_decklist_data = tournament_standings2decklist_data(tournament_decklist_filtered, card_id2card_data)
        lid2sim_leader_data[lid] = get_similar_leader_data(decklist_data, compare_decklist_data,
                                                            leader_id=leader_id, compare_leader_id=lid)
    return lid2sim_leader_data

def get_decklist_price(decklist: dict[str, int], card_id2card_data: dict[str, LatestCardPrice],
                       currency: CardCurrency = CardCurrency.EURO) -> float:
    deck_price = 0.0
    for card_id, count in decklist.items():
        card_data = card_id2card_data.get(card_id, None)
        if currency == CardCurrency.EURO:
            deck_price += card_data.latest_eur_price * count if card_data and card_data.latest_eur_price else 0.0
        elif currency == CardCurrency.US_DOLLAR:
            deck_price += card_data.latest_usd_price * count if card_data and card_data.latest_usd_price else 0.0
        else:
            raise NotImplementedError
    return deck_price

def get_prices_of_decklists(decklists: list[dict[str, int]], card_id2card_data: dict[str, ExtendedCardData], currency: CardCurrency = CardCurrency.EURO) -> list[float]:
    return [get_decklist_price(d, card_id2card_data, currency=currency)
            for d in decklists if d]

