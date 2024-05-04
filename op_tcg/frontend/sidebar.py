import streamlit as st

from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import OPTcgColor


def display_meta_select(multiselect: bool=True) -> list[MetaFormat]:
    all_metas = MetaFormat.to_list()
    last_meta = all_metas[-1]
    if multiselect:
        return st.multiselect("Meta", all_metas, default=last_meta)
    else:
        return [st.selectbox("Meta", sorted(all_metas, reverse=True))]

def display_release_meta_select(multiselect: bool=True) -> list[MetaFormat] | None:
    all_metas = MetaFormat.to_list()
    if multiselect:
        return st.multiselect("Leader Release Meta", all_metas)
    else:
        return [st.selectbox("Leader Release Meta", sorted(all_metas, reverse=True))]

def display_leader_color_multiselect() -> list[OPTcgColor] | None:
    all_colors = OPTcgColor.to_list()
    return st.multiselect("Leader Color", all_colors, default=None)

def display_match_count_slider_slider(min=0, max=20000):
    return st.slider('Leader Match Count', min, max, (min, max))


def display_only_official_toggle() -> bool:
    return st.toggle("Only Official", value=True)

def display_leader_multiselect(available_leader_ids: list[str] | None = None, default: list[str] = None) -> list[str]:
    available_leader_ids = available_leader_ids if available_leader_ids else ["OP01-001", "OP05-041", "OP02-001", "ST01-001", "OP02-093", "OP02-026"]
    leader_ids: list[str] = st.multiselect("Leaders", available_leader_ids, default=default)
    return leader_ids