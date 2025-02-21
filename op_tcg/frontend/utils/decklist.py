from datetime import date, datetime

import numpy as np
import streamlit as st
from pydantic import BaseModel, Field

from op_tcg.backend.models.cards import LatestCardPrice, ExtendedCardData, CardCurrency
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.backend.models.tournaments import TournamentStandingExtended, TournamentDecklist
from op_tcg.backend.utils.utils import timeit
from op_tcg.frontend.utils.card_price import get_decklist_price
from op_tcg.frontend.utils.extract import get_leader_extended, \
    get_tournament_decklist_data, get_card_id_card_data_lookup


class DecklistFilter(BaseModel):
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    min_tournament_placing: int | None = None
    filter_currency: CardCurrency | None = None
    min_price: float | None = None
    max_price: float | None = None


class DecklistData(BaseModel):
    num_decklists: int
    avg_price_eur: float | None = None
    avg_price_usd: float | None = None
    card_id2occurrences: dict[str, int]
    card_id2occurrence_proportion: dict[str, float]
    card_id2total_count: dict[str, int]
    card_id2avg_count_card: dict[str, float]
    card_id2card_data: dict[str, LatestCardPrice]
    meta_formats: list[MetaFormat] | None
    min_tournament_date: date | None = None
    max_tournament_date: date | None = None


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

    min_tournament_date = min(ts.tournament_timestamp for ts in tournament_standings).date() if len(
        tournament_standings) > 0 else None
    max_tournament_date = max(ts.tournament_timestamp for ts in tournament_standings).date() if len(
        tournament_standings) > 0 else None
    avg_price_eur = None
    avg_price_usd = None
    if len(tournament_standings) > 0 and isinstance(tournament_standings[0], TournamentDecklist):
        avg_price_eur = np.mean([ts.price_eur for ts in tournament_standings if ts.price_eur])
        avg_price_usd = np.mean([ts.price_usd for ts in tournament_standings if ts.price_usd])

    meta_formats = list(set([ts.meta_format for ts in tournament_standings]))
    return DecklistData(num_decklists=num_decklists,
                        avg_price_eur=avg_price_eur,
                        avg_price_usd=avg_price_usd,
                        card_id2occurrences=card_id2occurrences,
                        card_id2occurrence_proportion=card_id2occurrence_proportion,
                        card_id2total_count=card_id2total_count,
                        card_id2avg_count_card=card_id2avg_count_card,
                        card_id2card_data={cid: cdata for cid, cdata in card_id2card_data.items() if
                                           cid in card_id2occurrences},
                        meta_formats=meta_formats,
                        min_tournament_date=min_tournament_date,
                        max_tournament_date=max_tournament_date
                        )


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
                            compare_leader_id: str, threshold_occurrence: float | None = None) -> SimilarLeaderData:
    """similarity score: How much of occurred cards in decklist_data is also available in other deck"""
    card_ids = [card_id for card_id, occ in decklist_data.card_id2occurrence_proportion.items() if (occ > threshold_occurrence if threshold_occurrence else True) and card_id != leader_id]
    compare_card_ids = [card_id for card_id, occ in compare_decklist_data.card_id2occurrence_proportion.items() if (occ > threshold_occurrence if threshold_occurrence else True) and card_id != compare_leader_id]

    intersection = set(card_ids).intersection(
        set(compare_card_ids))
    max_occurrences = sum([compare_decklist_data.card_id2occurrence_proportion[cid] for cid in compare_card_ids])
    occurrence_list = [compare_decklist_data.card_id2occurrence_proportion[cid] for cid in compare_card_ids if cid in intersection]

    similarity_score = (sum(occurrence_list) / max_occurrences) if max_occurrences != 0 else 0
    intersection_sorted = sorted(list(intersection),
                                 key=lambda x: compare_decklist_data.card_id2occurrence_proportion[x], reverse=True)

    cards_missing = set(compare_card_ids) - set(card_ids)
    cards_missing_sorted = sorted(list(cards_missing),
                                  key=lambda x: compare_decklist_data.card_id2occurrence_proportion[x], reverse=True)

    return SimilarLeaderData(leader_id=compare_leader_id,
                             similarity_score=similarity_score,
                             cards_intersection=intersection_sorted,
                             cards_missing=cards_missing_sorted,
                             card_id2occurrence_proportion=compare_decklist_data.card_id2occurrence_proportion,
                             card_id2avg_count_card=compare_decklist_data.card_id2avg_count_card
                             )


@timeit
def get_most_similar_leader_data(leader_id: str, meta_formats: list[MetaFormat], threshold_occurrence: float | None = None) -> dict[str, SimilarLeaderData]:
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
                                                           leader_id=leader_id, compare_leader_id=lid, threshold_occurrence=threshold_occurrence)
    return lid2sim_leader_data


def get_prices_of_decklists(decklists: list[dict[str, int]], card_id2card_data: dict[str, ExtendedCardData],
                            currency: CardCurrency = CardCurrency.EURO) -> list[float]:
    return [get_decklist_price(d, card_id2card_data, currency=currency)
            for d in decklists if d]


def filter_tournament_decklist(tournament_decklist: TournamentDecklist, decklist_filter: DecklistFilter) -> bool:
    is_in_placing = True
    if decklist_filter.min_tournament_placing:
        is_in_placing = (tournament_decklist.placing != None and
                         tournament_decklist.placing <= decklist_filter.min_tournament_placing)
    is_in_price = True
    if tournament_decklist.price_eur and tournament_decklist.price_usd and decklist_filter.max_price and decklist_filter.min_price:
        if decklist_filter.filter_currency == CardCurrency.EURO:
            is_in_price = (
                    tournament_decklist.price_eur >= decklist_filter.min_price and
                    tournament_decklist.price_eur <= decklist_filter.max_price
            )
        else:
            is_in_price = (
                    tournament_decklist.price_usd >= decklist_filter.min_price and
                    tournament_decklist.price_usd <= decklist_filter.max_price
            )
    return (
            tournament_decklist.tournament_timestamp.date() >= decklist_filter.start_datetime.date() and
            tournament_decklist.tournament_timestamp.date() <= decklist_filter.end_datetime.date() and
            is_in_placing and
            is_in_price
    )


def filter_tournament_decklists(tournament_decklists: list[TournamentDecklist], decklist_filter: DecklistFilter) -> \
        list[TournamentDecklist]:
    return [td for td in tournament_decklists if filter_tournament_decklist(td, decklist_filter)]


def get_best_matching_decklist(tournament_decklists: list[TournamentDecklist], decklist_data: DecklistData) -> \
dict[str, int]:
    decklists: list[dict[str, int]] = [ts.decklist for ts in tournament_decklists]
    card_ids_sorted: list[str] = sorted(decklist_data.card_id2occurrence_proportion.keys(),
                                        key=lambda d: decklist_data.card_id2occurrences[d], reverse=True)
    should_have_card_ids_in_decklist: set[str] = set()
    card_count: float = 0.0
    for card_id in card_ids_sorted:
        if card_count < 51:  # 50 + leader
            should_have_card_ids_in_decklist.add(card_id)
            card_count += decklist_data.card_id2avg_count_card[card_id]
    best_matching_decklist: dict[str, int] = {}
    best_overlap = 0
    for decklist in decklists:
        card_in_decklist = set(decklist.keys())
        current_overlap = len(card_in_decklist.intersection(should_have_card_ids_in_decklist))
        if best_overlap < current_overlap:
            best_matching_decklist = decklist
            best_overlap = current_overlap

    return best_matching_decklist

def decklist_to_export_str(decklist: dict[str, int]):
    """Transforms a decklist dict into a export string for TCGSim"""
    return "\n".join([f"{c_count}x{cid}" for cid, c_count in decklist.items()])

def ensure_leader_id(decklist: dict[str, int], leader_id: str) -> dict[str, int]:
    return {leader_id: 1, **decklist}

def decklist_data_to_fictive_decklist(decklist_data: DecklistData, leader_id: str) -> dict[str, int]:
    decklist: dict[str, int] = {leader_id: 1}
    num_cards = 0
    sorted_decklist_card_ids = decklist_data_to_card_ids(decklist_data, exclude_card_ids=[leader_id])
    for cid in sorted_decklist_card_ids:
        avg_cid_count = round(decklist_data.card_id2avg_count_card[cid])
        if num_cards + avg_cid_count > 50:
            avg_cid_count = 50 - num_cards
        decklist[cid] = avg_cid_count
        num_cards += avg_cid_count
        # if we have 50 cards in deck the deck is completed
        if num_cards >= 50:
            return decklist
    return decklist
