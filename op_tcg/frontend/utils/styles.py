import cssutils
import streamlit as st
from pathlib import Path

from streamlit_theme import st_theme

from op_tcg.frontend import styles
from cssutils.css import CSSStyleSheet, CSSStyleRule

# RGB colors
GREEN_RGB = (123, 237, 159)
RED_RGB = (255, 107, 129)
PRIMARY_COLOR_RGB = (41, 128, 185)


def read_style_sheet(file_name: str, selector: str | None = None) -> CSSStyleSheet | CSSStyleRule:
    """
    returns: CSSStyleSheet in case no selector is provided, otherwise CSSStyleRule
    """
    with open(Path(styles.__path__[0]) / f"{file_name}.css", "r") as fp:
        css_text = fp.read()

    sheet = cssutils.parseString(css_text)
    return_object = None
    if selector:
        for rule in sheet:
            if hasattr(rule, "selectorText"):
                css_selector = rule.selectorText
                if selector == css_selector:
                    return_object = rule
                    break
        if return_object is None:
            raise ValueError(f"Could not find selector {selector}")
    else:
        return_object = sheet

    return return_object

def execute_style_sheet(file_name: str, selector: str | None = None):
    """Executes css code from a .css file"""
    if selector:
        css_text = read_style_sheet(file_name, selector).cssText
    else:
        css_text = read_style_sheet(file_name, selector).cssText.decode()

    st.markdown(
        f"""
        <style>
        {css_text}
        </style>
        """, unsafe_allow_html=True
    )

def css_rule_to_dict(rule: CSSStyleRule) -> dict:
    return {style: rule.style[style] for style in rule.style.keys()}
