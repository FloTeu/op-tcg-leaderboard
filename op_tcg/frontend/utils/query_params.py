from contextlib import suppress

import streamlit as st

from op_tcg.frontend.utils.leader_data import lid_to_name_and_lid

def add_query_param(qparam_key: str, qparam_value: str | list[str]):
    st.query_params[qparam_key] = qparam_value

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

def get_default_leader_names(available_leader_ids: list[str], query_param: str = "lid") -> list[str]:
    qp_lids = st.query_params.get_all(query_param)
    if qp_lids:
        return [lid_to_name_and_lid(qp_lid) for qp_lid in qp_lids if qp_lid in available_leader_ids]
    else:
        # of no query param provided use all available_leader_ids
        return [lid_to_name_and_lid(lid) for lid in available_leader_ids]

def delete_query_param(q_param: str):
    with suppress(KeyError):
        del st.query_params[q_param]