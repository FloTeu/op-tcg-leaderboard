from enum import StrEnum

import streamlit as st

from op_tcg.backend.models.base import EnumBase
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.cards import OPTcgColor


class LeaderboardSortBy(EnumBase, StrEnum):
    TOURNAMENT_WINS = "Tournament Wins"
    WIN_RATE = "Win Rate"
    ELO = "elo"


def display_meta_select(multiselect: bool = True, key: str | None = None) -> list[MetaFormat]:
    all_metas = MetaFormat.to_list()
    last_meta = all_metas[-1]
    if multiselect:
        return st.multiselect("Meta", all_metas, default=last_meta, key=key)
    else:
        return [st.selectbox("Meta", sorted(all_metas, reverse=True), key=key)]


def display_release_meta_select(multiselect: bool = True, default: list[MetaFormat] | None = None) -> list[
                                                                                                          MetaFormat] | None:
    all_metas = MetaFormat.to_list()
    if multiselect:
        return st.multiselect("Leader Release Meta", all_metas, default=default)
    else:
        return [st.selectbox("Leader Release Meta", sorted(all_metas, reverse=True))]


def display_leader_color_multiselect(default: list[OPTcgColor] | None = None) -> list[OPTcgColor] | None:
    all_colors = OPTcgColor.to_list()
    return st.multiselect("Leader Color", all_colors, default=default)


def display_match_count_slider_slider(min=0, max=20000):
    return st.slider('Leader Match Count', min, max, (min, max))


def display_only_official_toggle() -> bool:
    return st.toggle("Only Official", value=True)


def display_sortby_select() -> LeaderboardSortBy:
    return st.selectbox("Sort By", LeaderboardSortBy.to_list())


def display_leader_select(available_leader_ids: list[str] | None = None, multiselect: bool = True,
                          default: list[str] | str = None, label: str = "Leader", key: str | None = None) -> list[
                                                                                                           str] | str | None:
    available_leader_ids = available_leader_ids if available_leader_ids else ["OP01-001", "OP05-041", "OP02-001",
                                                                              "ST01-001", "OP02-093", "OP02-026"]
    if multiselect:
        return st.multiselect(label, available_leader_ids, default=default, key=key)
    else:
        if isinstance(default, list):
            default = default[0]
        index = available_leader_ids.index(default) if default else None
        leader: str | None = st.selectbox(label, available_leader_ids, index=index, key=key)
        return leader


def display_match_result_toggle() -> bool:
    return st.toggle("Only Official", value=True)
