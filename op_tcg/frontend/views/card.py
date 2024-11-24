from cssutils.css import CSSStyleRule
from streamlit.components import v1 as components
from streamlit_theme import st_theme

from op_tcg.frontend.utils.leader_data import lid_to_name_and_lid
from op_tcg.frontend.utils.styles import read_style_sheet

ST_THEME = st_theme(key=str(__file__)) or {"base": "dark"}

def display_card_attributes(card_data):
    def get_card_attribute_html(attribute_name: str, attribute_value: str) -> str:
        return f"""<div class="card-attribute">
                        <strong>{attribute_name}:</strong> {attribute_value}
                    </div>
        """

    card_attributes_html = f"""
    {get_card_attribute_html("Release Meta", card_data.meta_format)}
    {get_card_attribute_html("Card Type", card_data.card_category)}
    {get_card_attribute_html("Color", ", ".join(card_data.colors))}
    {get_card_attribute_html("Cost", card_data.cost) if card_data.cost is not None else ""}
    {get_card_attribute_html("Power", card_data.power) if card_data.power is not None else ""}
    {get_card_attribute_html("Counter", card_data.counter) if card_data.counter is not None else ""}
    {get_card_attribute_html("Life", card_data.life) if card_data.life is not None else ""}
    {get_card_attribute_html("Attribute",", ".join(card_data.attributes)) if card_data.attributes else ""}
    {get_card_attribute_html("Types", ", ".join(card_data.types))}
    {get_card_attribute_html("Ability", card_data.ability)}
"""

    title = lid_to_name_and_lid(card_data.id, leader_name=card_data.name)
    return_html = f"""
    <div class="card">
        <h1 class="card-title">{title}</h1>
        {card_attributes_html}
    </div>
    """

    card_attr_css = read_style_sheet("card_attributes")

    # Set text color for dark mode
    for rule in card_attr_css.cssRules:
        if isinstance(rule, CSSStyleRule) and (rule.selectorText == ".card-attribute" or rule.selectorText == ".card-attribute strong"):
            if ST_THEME["base"] == "dark":
                rule.style.color = "white"  # Change to white for dark mode
            else:
                rule.style.color = "black"  # Change to black for better visibility in light mode

    components.html(f"""
    <style> 
    {card_attr_css.cssText.decode()}
    </style>
    <body>
    {return_html}
    </body>""", height=500, scrolling=False)
