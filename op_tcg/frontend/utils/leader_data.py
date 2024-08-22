import pandas as pd
import streamlit as st
from pandera.typing import DataFrame

from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import Leader
from op_tcg.backend.models.cards import OPTcgColor, OPTcgAttribute, OPTcgLanguage, OPTcgTournamentStatus, \
    OPTcgCardRarity, OPTcgCardCatagory
from op_tcg.backend.models.matches import LeaderWinRate
from op_tcg.frontend.utils.extract import get_leader_data


def get_template_leader() -> Leader:
    """Returns an artificial leader, which can be used if no leader data ist available"""
    return Leader(
        id="NaN",
        name="NaN",
        life=5,
        power=5000,
        aa_version=0,
        meta_format=MetaFormat.to_list()[-1],
        image_url="",
        aa_image_url="",
        colors=[OPTcgColor.BLACK],
        attributes=[OPTcgAttribute.SLASH],
        ability="",
        types=[""],
        language=OPTcgLanguage.EN,
        tournament_status=OPTcgTournamentStatus.LEGAL,
        rarity=OPTcgCardRarity.LEADER,
        release_set_id="",
        cost=None,
        counter=None,
        card_category=OPTcgCardCatagory.LEADER,
    )


@st.cache_data(ttl=60 * 60)  # 1 hour
def get_lid2ldata_dict_cached() -> dict[str, Leader]:
    bq_leaders: list[Leader] = get_leader_data()
    return {bq_leader_data.id: bq_leader_data for bq_leader_data in
            bq_leaders}


def lid2ldata_fn(lid, leader_id2leader_data: dict[str, Leader] | None = None) -> Leader:
    """Return the leader data to a specific leader id.
    If no leader data is available, the template leader is used

    Caution:    As this function calls a cache function, it might break js react rendering,
                if the function is executed inside of a streamlit-elements statement. (see #24)
    """
    if leader_id2leader_data is None:
        leader_id2leader_data = get_lid2ldata_dict_cached()
    return leader_id2leader_data.get(lid, get_template_leader())


def leader_id2aa_image_url(leader_id: str, leader_id2leader_data: dict[str, Leader] | None = None):
    """If exists, it returns the alternative art of a leader
    """
    # constructed_deck_leaders_with_aa = ["ST13-001", "ST13-002", "ST13-002"]
    leader_data: Leader = lid2ldata_fn(leader_id, leader_id2leader_data)
    # has_aa = leader_id in constructed_deck_leaders_with_aa or not (leader_id[0:2] in ["ST"] or leader_id[0] in ["P"])
    return leader_data.aa_image_url # if has_aa else leader_data.image_url


def lids_to_name_and_lids(leader_ids: list[str], lid2ldata_dict: dict[str, Leader] | None = None) -> list[str]:
    """Transforms leader ids to leader name + leader ids"""
    # ensure dict type
    lid2ldata_dict = lid2ldata_dict or {}
    return [lid_to_name_and_lid(lid, leader_name=lid2ldata_dict.get(lid, None)) for lid in leader_ids]


def lid_to_name_and_lid(leader_id: str, leader_name: str | None = None) -> str:
    """Transforms leader id to leader name + leader id"""
    return f"{leader_name or lid2ldata_fn(leader_id).name} ({leader_id})"


def lname_and_lid_to_lid(lname_and_lid: str) -> str:
    """
    Extracts leader_id from leader_name and leader_id combination created by lid_to_name_and_lid
    Expects a string format like "<name> (<id>)"
    """
    return lname_and_lid.split("(")[1].strip(")")

def calculate_dominance_score(win_rate_norm: float, total_matches_norm: float, elo_rating_norm: float, tournament_wins_norm: float) -> float:
    return win_rate_norm * 0.1 + total_matches_norm * 0.3 + elo_rating_norm * 0.2 + tournament_wins_norm * 0.4


def get_win_rate_dataframes(df_win_rate_data: DataFrame[LeaderWinRate.paSchema()], selected_leader_ids: list[str]):
    def calculate_win_rate(df_win_rates: pd.DataFrame) -> float:
        weighted_average = (df_win_rates['win_rate'] * df_win_rates['total_matches']).sum() / df_win_rates['total_matches'].sum()
        return float("%.1f" % (weighted_average * 100))

    # calculate match counts between leaders
    def calculate_match_count(df_matches: pd.DataFrame) -> float:
        return df_matches.total_matches.sum()

    ## Win Rate and Match Count
    df_win_rate_selected_leader_data = df_win_rate_data.query("leader_id in @selected_leader_ids and opponent_id in @selected_leader_ids")

    win_rates_series = df_win_rate_selected_leader_data.groupby(["leader_id", "opponent_id"]).apply(calculate_win_rate, include_groups=False)
    df_Leader_vs_leader_win_rates = win_rates_series.unstack(level=-1)
    match_counts_series = df_win_rate_selected_leader_data.groupby(
        ["leader_id", "opponent_id"]).apply(calculate_match_count, include_groups=False)
    df_Leader_vs_leader_match_count = match_counts_series.unstack(level=-1)

    ## Color win rate
    # Create a new DataFrame with color information
    color_info: list[dict[str, str | OPTcgColor]] = []
    for leader_id, leader_data in get_lid2ldata_dict_cached().items():
        if leader_data:
            for color in leader_data.colors:
                color_info.append({'opponent_id': leader_id, 'color': color})

    # Convert the color_info list to a DataFrame
    df_color_info = pd.DataFrame(color_info)
    df_selected_color_match_data = df_win_rate_data.merge(df_color_info, on='opponent_id', how='left')

    # Calculate win rates
    win_rates_series = df_selected_color_match_data.query("leader_id in @selected_leader_ids").groupby(
        ["leader_id", "color"]).apply(calculate_win_rate, include_groups=False)
    df_color_win_rates = win_rates_series.unstack(level=-1)

    ## Ensure correct order
    dfs = [df_Leader_vs_leader_win_rates, df_Leader_vs_leader_match_count]
    for i in range(len(dfs)):
        # Convert the index to a categorical type with the specified order
        dfs[i].index = pd.Categorical(dfs[i].index, categories=selected_leader_ids, ordered=True)
        dfs[i].columns = pd.Categorical(dfs[i].columns, categories=selected_leader_ids, ordered=True)
        # Sort the DataFrame by the custom order (overwrites values in dfs list)
        dfs[i] = dfs[i].sort_index().sort_index(axis=1)

    df_color_win_rates.index = pd.Categorical(df_color_win_rates.index, categories=selected_leader_ids, ordered=True)
    df_color_win_rates = df_color_win_rates.sort_index().sort_index(axis=1)

    return dfs[0], dfs[1], df_color_win_rates
