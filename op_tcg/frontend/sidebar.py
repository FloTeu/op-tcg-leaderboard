import streamlit as st

from op_tcg.backend.models.input import MetaFormat


def sidebar_display_meta(multiselect: bool=True) -> list[MetaFormat]:
    all_metas = MetaFormat.to_list()
    last_meta = all_metas[-1]
    if multiselect:
        return st.sidebar.multiselect("Meta", all_metas, default=last_meta)
    else:
        return [st.sidebar.selectbox("Meta", sorted(all_metas, reverse=True))]

def sidebar_display_release_meta(multiselect: bool=True) -> list[MetaFormat] | None:
    all_metas = MetaFormat.to_list()
    if multiselect:
        return st.sidebar.multiselect("Leader Release Meta", all_metas)
    else:
        return [st.sidebar.selectbox("Leader Release Meta", sorted(all_metas, reverse=True))]

def sidebar_display_match_count_slider(min=0, max=20000):
    return st.sidebar.slider('Leader Match Count', min, max, (min, max))


def sidebar_display_only_official() -> bool:
    return st.sidebar.toggle("Only Official", value=True)

def sidebar_display_leader(available_leader_ids: list[str] | None = None) -> list[str]:
    # TODO: Make also leader name search possible
    # search_term: str | None = st.sidebar.text_input("Search by id")
    available_leader_ids = available_leader_ids if available_leader_ids else ["OP01-001", "OP05-041", "OP02-001", "ST01-001", "OP02-093", "OP02-026"]
    leader_ids: list[str] = st.sidebar.multiselect("Leaders", available_leader_ids, default=available_leader_ids[0:5])
    return leader_ids