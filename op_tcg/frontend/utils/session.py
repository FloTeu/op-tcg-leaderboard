import streamlit as st

def get_session_id():
    return st.runtime.scriptrunner.add_script_run_ctx().streamlit_script_run_ctx.session_id

