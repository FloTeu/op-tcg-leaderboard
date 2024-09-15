import streamlit as st

from op_tcg.backend.models.input import MetaFormat
from op_tcg.frontend.utils.extract import get_leader_win_rate


@st.cache_data
def get_latest_released_meta_format_with_data() -> MetaFormat:
    # iterate over all released meta formate and return the first with match data
    meta_format: MetaFormat = MetaFormat.latest_meta_format()
    for i in range(len(MetaFormat.to_list(only_after_release=True))):
        meta_format: MetaFormat = MetaFormat.to_list(only_after_release=True)[-(i+1)]
        if len(get_leader_win_rate(meta_formats=[meta_format])) == 0:
            continue
        else:
            break
    return meta_format