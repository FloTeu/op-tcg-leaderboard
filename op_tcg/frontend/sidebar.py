from enum import StrEnum
from typing import Callable, Generic, TypeVar

import streamlit as st

from op_tcg.backend.models.base import EnumBase
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.cards import OPTcgColor, OPTcgAbility, OPTcgAttribute
from op_tcg.frontend.utils.extract import get_card_types
from op_tcg.frontend.utils.meta_format import get_latest_released_meta_format_with_data

T = TypeVar('T')  # Define type variable "T"

class LeaderboardSortBy(EnumBase, StrEnum):
    DOMINANCE_SCORE = "D-Score"
    TOURNAMENT_WINS = "Tournament Wins"
    WIN_RATE = "Win Rate"
    ELO = "Elo"

class LeaderCardMovementSortBy(EnumBase, StrEnum):
    CARD_MOVEMENT_WINNER = "Winner"
    CARD_MOVEMENT_LOSER = "Loser"


def display_meta_select(multiselect: bool = True,
                        key: str | None = None,
                        label: str="Meta",
                        reverse=True,
                        on_change: Callable[..., None] | None = None,
                        default: MetaFormat | list[MetaFormat] | None  = None) -> list[MetaFormat]:
    all_metas = MetaFormat.to_list()
    default = default or get_latest_released_meta_format_with_data()
    if reverse:
        all_metas = sorted(all_metas, reverse=reverse)
    if multiselect:
        return st.multiselect(label, all_metas, default=default, on_change=on_change, key=key)
    else:
        index = all_metas.index(default) if default else None
        return [st.selectbox(label, all_metas, index=index, on_change=on_change, key=key)]

def display_meta_format_region(multiselect: bool = False, key: str | None = None, label: str= "Meta Region", reverse=True, default: MetaFormatRegion = MetaFormatRegion.ALL) -> list[MetaFormatRegion]:
    all_metas = MetaFormatRegion.to_list()
    if reverse:
        all_metas = sorted(all_metas, reverse=reverse)
    if multiselect:
        return st.multiselect(label, all_metas, default=default, key=key)
    else:
        index = all_metas.index(default) if default else None
        return [st.selectbox(label, all_metas, index=index, key=key)]


def display_release_meta_select(multiselect: bool = True, default: list[MetaFormat] | None = None, label: str="Leader Release Meta") -> list[
                                                                                                          MetaFormat] | None:
    all_metas = MetaFormat.to_list()
    if multiselect:
        return st.multiselect(label, all_metas, default=default)
    else:
        return [st.selectbox(label, sorted(all_metas, reverse=True))]


def display_leader_color_multiselect(default: list[OPTcgColor] | None = None) -> list[OPTcgColor] | None:
    all_colors = OPTcgColor.to_list()
    return st.multiselect("Leader Color", all_colors, default=default)

def display_card_color_multiselect(default: list[OPTcgColor] | None = None) -> list[OPTcgColor] | None:
    all_colors = OPTcgColor.to_list()
    return st.multiselect("Card Color", all_colors, default=default)

def display_card_attribute_multiselect(default: list[OPTcgAttribute] | None = None) -> list[OPTcgAttribute] | None:
    all_attributes = OPTcgAttribute.to_list()
    return st.multiselect("Card Attribute", all_attributes, default=default)

def display_card_ability_multiselect(default: list[OPTcgAbility] | None = None) -> list[OPTcgAbility] | None:
    all_abilities = OPTcgAbility.to_list()
    card_abilities = st.multiselect("Card Ability", all_abilities, default=default)
    return card_abilities if len(card_abilities) > 0 else None

def display_match_count_slider_slider(min=0, max=20000):
    return st.slider('Leader Match Count', min, max, (min, max))


def display_only_official_toggle() -> bool:
    return st.toggle("Only Official", value=True)


def display_sortby_select(enum_cls: Generic[T]) -> T:
    return st.selectbox("Sort By", enum_cls.to_list())


def display_leader_select(available_leader_names: list[str] | None = None,
                          multiselect: bool = True,
                          default: list[str] | str = None,
                          label: str = "Leader",
                          key: str | None = None,
                          on_change: Callable[..., None] | None = None,
                          **kwargs) -> list[
                                                                                                           str] | str | None:
    available_leader_names = available_leader_names if available_leader_names else ["OP01-001", "OP05-041", "OP02-001",
                                                                              "ST01-001", "OP02-093", "OP02-026"]
    if multiselect:
        return st.multiselect(label, available_leader_names, default=default, key=key, on_change=on_change, kwargs=kwargs)
    else:
        if isinstance(default, list):
            default = default[0]
        index = available_leader_names.index(default) if default else None
        leader: str | None = st.selectbox(label, available_leader_names, index=index, key=key, on_change=on_change, kwargs=kwargs)
        return leader


def display_card_fraction_multiselect(default: list[str] | None = None) -> list[str] | None:
    all_fractions = get_card_types()
    return st.multiselect("Subtype(s)", all_fractions, default=default)


def display_match_result_toggle() -> bool:
    return st.toggle("Only Official", value=True)
