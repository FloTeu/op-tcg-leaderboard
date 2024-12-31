import time
import streamlit as st
from typing import Callable
from streamlit_elements.core.frame import ELEMENTS_FRAME_KEY

class ElementsComponentView:
    """View class to render a streamlit component"""

    def __init__(self, fn: Callable, *fn_args, **fn_kwargs):
        self.fn = fn
        self.fn_args = fn_args
        self.fn_kwargs = fn_kwargs

    def display(self, retries: int = 0):
        component_placeholder = st.empty()
        try:
            with st.spinner():
                with component_placeholder:
                    self.fn(*self.fn_args, **self.fn_kwargs)
                for i in range(retries):
                    #st.header(f"Retry {i+1}")
                    # ensure component session state is deleted
                    if ELEMENTS_FRAME_KEY in st.session_state:
                        del st.session_state[ELEMENTS_FRAME_KEY]
                    component_placeholder.empty()
                    time.sleep(0.5)
                    retry_kwargs = {**self.fn_kwargs, "key": f'{self.fn_kwargs.get("key", "")}_{i}'}
                    with component_placeholder:
                        self.fn(*self.fn_args, **retry_kwargs)
        except Exception as exp:
            print(exp)
            st.error(f"Error during component render")
