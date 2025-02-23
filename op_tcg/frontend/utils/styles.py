from typing import overload

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


@overload
def read_style_sheet(file_name: str, selector: str) -> CSSStyleRule: ...

@overload
def read_style_sheet(file_name: str, selector: None = None) -> CSSStyleSheet: ...

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

def brighten_hex_color(hex_color, factor=1.1):
    """
    Brighten a hex color string by a given factor.

    :param hex_color: The hex color string (e.g., "#0b1214").
    :param factor: The factor by which to brighten the color (default is 1.1).
    :return: A new hex color string that is slightly brighter.
    """
    # Remove the '#' character if present
    hex_color = hex_color.lstrip('#')

    # Convert hex to RGB
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    # Brighten each component
    r = min(int(r * factor), 255)
    g = min(int(g * factor), 255)
    b = min(int(b * factor), 255)

    # Convert back to hex
    return f'#{r:02x}{g:02x}{b:02x}'