from contextlib import suppress

import streamlit as st

from op_tcg.frontend.utils.leader_data import lid2ldata_fn, lid_to_name_and_lid


def add_query_param(kwargs: dict[str, str]):
    for qparam, session_key in kwargs.items():
        st.query_params[qparam] = st.session_state[session_key].split("(")[1].strip(")")


def get_default_leader_name(available_leader_ids: list[str], query_param: str = "lid") -> str:
    qp_lid = st.query_params.get(query_param, None)
    if qp_lid:
        default_leader_name = lid_to_name_and_lid(qp_lid)
        if qp_lid not in available_leader_ids:
            st.warning(f"Leader {default_leader_name} is not available")
            default_leader_name = lid_to_name_and_lid(available_leader_ids[0])
        return default_leader_name
    else:
        # of no query param provided pick first of available_leader_ids
        return lid_to_name_and_lid(available_leader_ids[0])

def delete_query_param(q_param: str):
    with suppress(KeyError):
        del st.query_params[q_param]