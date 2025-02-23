from collections import Counter

import streamlit as st
from cachetools import TTLCache

from op_tcg.backend.models.bq_classes import BQTableBaseModel
from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.backend.models.cards import LatestCardPrice, CardPopularity, Card, CardReleaseSet, ExtendedCardData, \
    CardCurrency
from op_tcg.backend.models.decklists import Decklist
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.leader import Leader, TournamentWinner, LeaderElo, LeaderExtended
from op_tcg.backend.models.matches import Match, LeaderWinRate
from op_tcg.backend.models.tournaments import TournamentStanding, Tournament, TournamentStandingExtended, \
    TournamentDecklist, TournamentExtended
from op_tcg.backend.utils.utils import timeit
from op_tcg.frontend.utils.card_price import get_decklist_price
from op_tcg.frontend.utils.utils import run_bq_query

# maxsize: Number of elements the cache can hold
CACHE = TTLCache(maxsize=10, ttl=60 * 60 * 24)

def get_bq_table_id(table: type[BQTableBaseModel]) -> str:
    return f'{st.secrets["gcp_service_account"]["project_id"]}.{table.get_dataset_id()}.{table.__tablename__}'

def get_leader_data() -> list[Leader]:
    # cached for each session
    leader_data_rows = run_bq_query(f"""SELECT * FROM `{get_bq_table_id(Leader)}`""")
    bq_leaders = [Leader(**d) for d in leader_data_rows]
    return bq_leaders


def get_match_data(meta_formats: list[MetaFormat], leader_ids: list[str] | None = None) -> list[Match]:
    bq_matches: list[Match] = []
    for meta_format in meta_formats:
        # cached for each session
        match_data_rows = run_bq_query(f"""SELECT * FROM `{get_bq_table_id(Match)}` where meta_format = '{meta_format}'""")
        bq_matches.extend([Match(**d) for d in match_data_rows])

    if leader_ids:
        return [bqm for bqm in bq_matches if (bqm.leader_id in leader_ids)]
    else:
        return bq_matches

def get_leader_win_rate(meta_formats: list[MetaFormat], leader_ids: list[str] | None = None) -> list[LeaderWinRate]:
    bq_win_rates: list[LeaderWinRate] = []
    for meta_format in meta_formats:
        # cached for each session
        win_rate_data_rows = run_bq_query(f"""SELECT * FROM `{get_bq_table_id(LeaderWinRate)}` where meta_format = '{meta_format}'""")
        bq_win_rates.extend([LeaderWinRate(**d) for d in win_rate_data_rows])

    if leader_ids:
        return [bqwr for bqwr in bq_win_rates if (bqwr.leader_id in leader_ids)]
    else:
        return bq_win_rates

def get_leader_extended(meta_formats: list[MetaFormat] | None = None, leader_ids: list[str] | None = None, meta_format_region: MetaFormatRegion = MetaFormatRegion.ALL) -> list[LeaderExtended]:
    bq_leader_data: list[LeaderExtended] = []
    if meta_formats:
        for meta_format in meta_formats:
            # cached for each session
            leader_data_rows = run_bq_query(f"""SELECT * FROM `{get_bq_table_id(LeaderExtended)}` where meta_format = '{meta_format}'""")
            bq_leader_data.extend([LeaderExtended(**d) for d in leader_data_rows])
    else:
        leader_data_rows = run_bq_query(
            f"""SELECT * FROM `{get_bq_table_id(LeaderExtended)}`""")
        bq_leader_data.extend([LeaderExtended(**d) for d in leader_data_rows])

    if leader_ids:
        bq_leader_data = [bql for bql in bq_leader_data if (bql.id in leader_ids)]
    if meta_format_region:
        bq_leader_data = [bql for bql in bq_leader_data if (bql.meta_format_region == meta_format_region)]

    return bq_leader_data

@timeit
def get_tournament_standing_data(meta_formats: list[MetaFormat], leader_id: str | None = None) -> list[TournamentStandingExtended]:
    bq_tournament_standings: list[TournamentStandingExtended] = []
    for meta_format in meta_formats:
        # cached for each session
        tournament_standing_rows = run_bq_query(f"""
SELECT t1.*, t2.* EXCEPT (create_timestamp, name) FROM `{get_bq_table_id(TournamentStanding)}` t1
left join `{get_bq_table_id(Tournament)}` t2
on t1.tournament_id = t2.id
where t2.meta_format = '{meta_format}'""")
        bq_tournament_standings.extend([TournamentStandingExtended(**d) for d in tournament_standing_rows])
    if leader_id:
        bq_tournament_standings = [ts for ts in bq_tournament_standings if ts.leader_id == leader_id]
    return bq_tournament_standings


def get_tournament_decklist_data(meta_formats: list[MetaFormat], leader_ids: list[str] | None = None) -> list[TournamentDecklist]:
    leader_ids = leader_ids or []
    bq_decklists = get_all_tournament_decklist_data()
    if leader_ids:
        bq_decklists = [ts for ts in bq_decklists if ts.leader_id in leader_ids]
    if meta_formats:
        bq_decklists = [ts for ts in bq_decklists if ts.meta_format in meta_formats]
    return bq_decklists

def get_all_tournament_decklist_data() -> list[TournamentDecklist]:
    if "TOURNAMENT_DECKLISTS" in CACHE:
        return CACHE["TOURNAMENT_DECKLISTS"]
    else:
        card_id2card_data = get_card_id_card_data_lookup()
        # cached for each session
        tournament_standing_rows = run_bq_query(f"""
    SELECT t1.leader_id, t1.tournament_id, COALESCE(t3.decklist, t1.decklist) AS decklist, t1.placing, t1.player_id, t2.meta_format, COALESCE(t2.meta_format_region, 'west') AS meta_format_region , t2.tournament_timestamp 
    FROM `{get_bq_table_id(TournamentStanding)}` t1
    left join `{get_bq_table_id(Tournament)}` t2 on t1.tournament_id = t2.id
    left join `{get_bq_table_id(Decklist)}` t3 on t1.decklist_id = t3.id
    where
    t1.decklist IS NOT NULL 
    OR t3.decklist IS NOT NULL""")
        tournament_decklists: list[TournamentDecklist] = []
        for ts in tournament_standing_rows:
            tournament_decklist = TournamentDecklist(**ts)
            tournament_decklist.price_usd = get_decklist_price(tournament_decklist.decklist, card_id2card_data, currency=CardCurrency.US_DOLLAR)
            tournament_decklist.price_eur = get_decklist_price(tournament_decklist.decklist, card_id2card_data, currency=CardCurrency.EURO)
            tournament_decklists.append(tournament_decklist)
        CACHE["TOURNAMENT_DECKLISTS"] = tournament_decklists
        return tournament_decklists

def get_all_tournament_extened_data(meta_formats: list[MetaFormat] | None = None) -> list[TournamentExtended]:
    if "TOURNAMENT_EXTENDED" in CACHE:
        tournaments = CACHE["TOURNAMENT_EXTENDED"]
    else:
        tournament_extended_rows = run_bq_query(f"""SELECT * FROM `{get_bq_table_id(TournamentExtended)}` order by tournament_timestamp desc""")
        tournaments: list[TournamentExtended] = []
        for te in tournament_extended_rows:
            tournaments.append(TournamentExtended(**te))
        CACHE["TOURNAMENT_EXTENDED"] = tournaments

    if meta_formats:
        tournaments = [t for t in tournaments if t.meta_format in meta_formats]
    return tournaments

def get_leader_elo_data(meta_formats: list[MetaFormat] | None=None) -> list[LeaderElo]:
    """First element is leader with best elo.
    """
    bq_leader_elos: list[LeaderElo] = []
    if meta_formats:
        for meta_format in meta_formats:
            # cached for each session
            leader_elo_rows = run_bq_query(f"""SELECT * FROM `{get_bq_table_id(LeaderElo)}` where meta_format = '{meta_format}' order by elo desc""")
            bq_leader_elos.extend([LeaderElo(**d) for d in leader_elo_rows])
    else:
        leader_elo_rows = run_bq_query(
            f"""SELECT * FROM `{get_bq_table_id(LeaderElo)}` order by elo desc""")
        bq_leader_elos.extend([LeaderElo(**d) for d in leader_elo_rows])
    bq_leader_elos.sort(key=lambda x: x.elo, reverse=True)
    return bq_leader_elos


def get_leader_tournament_wins(meta_formats: list[MetaFormat] | None=None) -> list[TournamentWinner]:
    """First element is leader with best elo.
    """
    bq_leader_tournament_wins: list[TournamentWinner] = []
    if meta_formats:
        for meta_format in meta_formats:
            # cached for each session
            leader_wins_rows = run_bq_query(f"""SELECT * FROM `{get_bq_table_id(TournamentWinner)}` where meta_format = '{meta_format}'""")
            bq_leader_tournament_wins.extend([TournamentWinner(**d) for d in leader_wins_rows])
    else:
        leader_wins_rows = run_bq_query(
            f"""SELECT * FROM `{get_bq_table_id(TournamentWinner)}`""")
        bq_leader_tournament_wins.extend([TournamentWinner(**d) for d in leader_wins_rows])
    return bq_leader_tournament_wins

def get_card_data() -> list[LatestCardPrice]:
    latest_card_rows = run_bq_query(
            f"""SELECT t0.*, t1.* except(id, name, language, create_timestamp) 
            FROM `{get_bq_table_id(LatestCardPrice)}` t0
            LEFT JOIN `{get_bq_table_id(CardReleaseSet)}` t1 on t0.release_set_id = t1.id
    """)
    return [ExtendedCardData(**d) for d in latest_card_rows]

def get_card_popularity_data() -> list[CardPopularity]:
    latest_card_rows = run_bq_query(
            f"""SELECT * FROM `{get_bq_table_id(CardPopularity)}`""")
    return [CardPopularity(**d) for d in latest_card_rows]

def get_card_popularity_by_meta(card_id: str, until_meta_format: MetaFormat | None = None) -> dict[MetaFormat, float]:
    card_popularity_by_meta: dict[MetaFormat, float] = {}
    card_colors = get_card_id_card_data_lookup().get(card_id).colors
    card_popularities = [cpd for cpd in get_card_popularity_data() if cpd.card_id == card_id]
    for meta_format in MetaFormat.to_list(until_meta_format=until_meta_format):
        card_popularities_in_meta = [cp for cp in card_popularities if cp.meta_format == meta_format and cp.color in card_colors]
        if len(card_popularities_in_meta) > 0:
            # take the maximum popularity if card is played in multi colored decks
            max_popularity = max([cp.popularity for cp in card_popularities_in_meta])
            card_popularity_by_meta[meta_format] = max_popularity
        else:
            card_popularity_by_meta[meta_format] = 0.0
    return card_popularity_by_meta

@st.cache_data
def get_meta_format_to_num_decklists() -> dict[MetaFormat, int]:
    decklists = get_all_tournament_decklist_data()
    # Use a Counter to count occurrences of each meta_format
    meta_format_counter = Counter(decklist.meta_format for decklist in decklists)
    return dict(meta_format_counter)

def get_card_types() -> list[str]:
    latest_card_rows = run_bq_query(
            f"""SELECT DISTINCT(types) FROM `{get_bq_table_id(Card)}` c, UNNEST(c.types) AS types """)
    return [d["types"] for d in latest_card_rows]


def get_card_id_card_data_lookup(aa_version: int = 0, ensure_latest_price_not_null=True) -> dict[str, ExtendedCardData]:
    card_data = get_card_data()
    card_data = [cdata for cdata in card_data if cdata.aa_version == aa_version]
    if ensure_latest_price_not_null:
        for cdata in card_data:
            cdata.ensure_latest_price_not_none()
    return {card.id: card for card in card_data}
