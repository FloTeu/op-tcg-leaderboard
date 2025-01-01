import time
import streamlit as st
from pydantic import BaseModel
from typing import Callable
from streamlit_elements.core.frame import ELEMENTS_FRAME_KEY

class ComponentViewSessionState(BaseModel):
    rendered_session_key: str | None = None # key used inside of fn to render component


class ElementsComponentView:
    """View class to render a streamlit component"""

    def __init__(self, fn: Callable, *fn_args, **fn_kwargs):
        self.fn = fn
        self.fn_args = fn_args
        self.fn_kwargs = fn_kwargs
        self.session_key = str(fn.__name__) # key used in this class to rerender component
        if self.session_key not in st.session_state:
            st.session_state[self.session_key] = ComponentViewSessionState()
        self.session: ComponentViewSessionState = st.session_state[self.session_key]

    @staticmethod
    def increment_session_key(key, retry: int = 0):
        if retry > 0:
            return f'{key}_{retry}'
        else:
            return f'{key}'


    def display(self, retries: int = 0):
        """Displays a component for the first time"""
        self.session.rendered_session_key = self.fn_kwargs.get("key")

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
                    retry_kwargs = {**self.fn_kwargs, "key": self.increment_session_key(self.fn_kwargs.get("key", ""), i+1)}
                    with component_placeholder:
                        self.fn(*self.fn_args, **retry_kwargs)
                    self.session.rendered_session_key = retry_kwargs["key"]
        except Exception as exp:
            print(exp)
            component_placeholder.error(f"Error while component was rendering")

    def rerender(self):
        """If component was rendered already this function can be called to rerender it"""
        # Do not use st.empty(), to prevent page reload (see #43)
        fn_kwargs = {**self.fn_kwargs, "key": self.session.rendered_session_key}
        self.fn(*self.fn_args, **fn_kwargs)



