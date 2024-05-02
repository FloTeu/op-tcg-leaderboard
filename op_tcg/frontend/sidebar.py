import streamlit as st

from op_tcg.backend.models.input import MetaFormat


def display_meta_sidebar() -> list[MetaFormat]:
    return st.sidebar.multiselect("Meta", [MetaFormat.OP01, MetaFormat.OP02, MetaFormat.OP03, MetaFormat.OP04, MetaFormat.OP05, MetaFormat.OP06], default=MetaFormat.OP06)

def display_only_official_sidebar() -> bool:
    return st.sidebar.toggle("Only Official", value=True)

def display_leader_sidebar(available_leader_ids: list[str] | None = None) -> list[str]:
    # TODO: Make also leader name search possible
    # search_term: str | None = st.sidebar.text_input("Search by id")
    available_leader_ids = available_leader_ids if available_leader_ids else ["OP01-001", "OP05-041", "OP02-001", "ST01-001", "OP02-093", "OP02-026"]
    leader_ids: list[str] = st.sidebar.multiselect("Leaders", available_leader_ids, default=available_leader_ids[0:5])
    return leader_ids