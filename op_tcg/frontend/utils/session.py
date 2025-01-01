from enum import StrEnum, auto

import streamlit as st

class SessionKeys(StrEnum):
    MODAL_OPEN_CLICKED = auto()

def reset_session_state():
    """Reset session state to default"""
    st.session_state[SessionKeys.MODAL_OPEN_CLICKED] = False

def get_session_id():
    return st.runtime.scriptrunner.add_script_run_ctx().streamlit_script_run_ctx.session_id

