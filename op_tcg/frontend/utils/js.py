import time
import random
from pathlib import Path

import streamlit.components.v1 as components

from streamlit_js_eval import streamlit_js_eval
from functools import cache
from uuid import uuid4
from op_tcg.frontend.utils.session import get_session_id
from op_tcg.frontend import scripts


def read_js_file(file_name: str) -> str:
    """Returns javascript code from a .js file"""
    with open(Path(scripts.__path__[0]) / f"{file_name}.js", "r") as fp:
        js_text = fp.read()
    return js_text


def execute_js_file(file_name: str, display_none: bool = False):
    """Executes js code from a .js file"""
    js_text = read_js_file(file_name)
    components.html(f"""
        <script>
            eval(`{js_text}`);
        </script>
    """, height=0, width=0)
    if display_none:
        prevent_js_frame_height()

@cache
def get_screen_width(session_id: str) -> int | None:
    """
    Return screen width by javascript call
    st_session_id is provided to ensure screen width is detected once per user (because of cache)

    raises:
        TypeError: If no screen width can be detected

    """

    # Note: Can be none, if javascript is not able to detect browser width -> will throw an exception
    try:
        screen_width = streamlit_js_eval(js_expressions='screen.width', want_output=True, key=f"SCR")
        return int(screen_width)
    except Exception as e:
        print(e)
        time.sleep(random.randint(0,2))
        screen_width = streamlit_js_eval(js_expressions='screen.width', want_output=True, key=f"SCR{uuid4().hex}")
        return int(screen_width)


def is_mobile() -> bool:
    try:
        width: int = get_screen_width(get_session_id())
    except TypeError:
        # Thrown if screen width is not know yet
        return False
    return width < 600

def prevent_js_frame_height():
    """execute_js_file creates a div with height, even though height is set to 0
    This function includes display None in that case
    """
    execute_js_file("iframe_display_none")