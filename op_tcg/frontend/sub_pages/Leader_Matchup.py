from functools import partial

import pandas as pd
import streamlit as st

from op_tcg.backend.utils.leader_fns import df_win_rate_data2lid_dicts
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import Leader, LeaderExtended
from op_tcg.backend.models.matches import LeaderWinRate
from op_tcg.frontend.sub_pages.constants import Q_PARAM_LEADER_ID
from op_tcg.frontend.utils.chart import get_radar_chart_data, create_leader_win_rate_radar_chart
from op_tcg.frontend.utils.extract import get_leader_win_rate, get_leader_extended
from op_tcg.frontend.sidebar import display_meta_select, display_leader_select, display_only_official_toggle
from op_tcg.frontend.utils.js import is_mobile
from op_tcg.frontend.utils.material_ui_fns import create_image_cell, display_table, value2color_table_cell, \
    add_tooltip
from op_tcg.frontend.utils.leader_data import leader_id2aa_image_url, lid2ldata_fn, get_lid2ldata_dict_cached, \
    get_template_leader, lids_to_name_and_lids, lname_and_lid_to_lid, get_win_rate_dataframes

from streamlit_elements import elements, mui
from streamlit_theme import st_theme

from op_tcg.frontend.utils.query_params import add_query_param, get_default_leader_names
from op_tcg.frontend.utils.styles import css_rule_to_dict, read_style_sheet

ST_THEME = st_theme(key=str(__file__)) or {"base": "dark"}


def display_elements(selected_leader_ids,
                     selected_bq_leaders,
                     df_Leader_vs_leader_win_rates,
                     df_Leader_vs_leader_match_count,
                     radar_chart_data):
    lid2ldata_dict = get_lid2ldata_dict_cached()
    table_cell_styles = css_rule_to_dict(read_style_sheet("table", ".colored-table-cell"))

    def get_leader_name(leader_id: str) -> str:
        return f"{lid2ldata_dict.get(leader_id, get_template_leader()).name} ({lid2ldata_dict.get(leader_id, get_template_leader()).get_color_short_name()})"

    selected_leader_names = [get_leader_name(lid) for lid in selected_leader_ids]
    colors = [lid2ldata_dict.get(lid, get_template_leader()).to_hex_color() for lid in selected_leader_ids]
    # change radar ids to name
    for j, r_data in enumerate(radar_chart_data):
        radar_chart_data[j] = {k if i == 0 else get_leader_name(k): v for i, (k, v) in enumerate(r_data.items())}

    col1, col2 = st.columns([1, 1])
    col1.subheader("Leader Color Win Rates")
    with col2:
        with elements("avatars"):
            children = [mui.Avatar(src=l.aa_image_url) for l in selected_bq_leaders]
            mui.AvatarGroup(children=children, key="lmeta_avatar_group_item")

    rounder_corners_css = css_rule_to_dict(read_style_sheet("chart", selector=".rounded-corners"))
    styles = {"height": 450,
              **rounder_corners_css,
              }
    layout_overwrites = {"dotSize": 15, "legends": [
        {"effects":
             [{"style":
                   {"translateX": 0 if is_mobile() else 160,
                    "translateY": 70 if is_mobile() else 120}
               }]
         }
    ]}
    create_leader_win_rate_radar_chart(radar_chart_data, selected_leader_names, colors, styles=styles,
                                       layout_overwrites=layout_overwrites)

    with elements("dashboard"):
        # leader win rate
        leader2win_rate = get_leader2avg_win_rate_dict(df_Leader_vs_leader_match_count,
                                                       df_Leader_vs_leader_win_rates)
        sorted_leader_ids: list[str] = sorted(leader2win_rate, key=leader2win_rate.get, reverse=True)

        # sort data based on win rate
        df_Leader_vs_leader_win_rates = df_Leader_vs_leader_win_rates.loc[sorted_leader_ids]
        df_Leader_vs_leader_match_count = df_Leader_vs_leader_match_count.loc[sorted_leader_ids]
        df_Leader_vs_leader_win_rates = df_Leader_vs_leader_win_rates.loc[:, sorted_leader_ids]
        df_Leader_vs_leader_match_count = df_Leader_vs_leader_match_count.loc[:, sorted_leader_ids]

        header_cells = [mui.TableCell(children="Winner\\Opponent"), mui.TableCell(children="Win Rate")] + [
            create_image_cell(lid2ldata_dict.get(col, get_template_leader()).image_url,
                              text=lid2ldata_dict.get(col, get_template_leader()).name.replace('"', " ").replace('.',
                                                                                                                 " "),
                              overlay_color=lid2ldata_dict.get(col, get_template_leader()).to_hex_color(),
                              horizontal=False) for col in
            df_Leader_vs_leader_win_rates.columns.values]
        index_cells = []
        index_cells.append([create_image_cell(leader_id2aa_image_url(leader_id, lid2ldata_dict),
                                              text=lid2ldata_dict.get(leader_id, get_template_leader()).id.split("-")[
                                                       0] + "\n" + lid2ldata_dict.get(leader_id,
                                                                                      get_template_leader()).name.replace(
                                                  '"', " ").replace('.', " "),
                                              overlay_color=lid2ldata_dict.get(leader_id,
                                                                               get_template_leader()).to_hex_color())
                            for
                            leader_id, df_row in df_Leader_vs_leader_win_rates.iterrows()])
        index_cells.append(
            [value2color_table_cell(leader2win_rate[leader_id], max_value=100, styles=table_cell_styles) for leader_id in sorted_leader_ids])

        for col in df_Leader_vs_leader_match_count.columns.values:
            df_Leader_vs_leader_match_count[col] = df_Leader_vs_leader_match_count[col].fillna(0)
            df_Leader_vs_leader_match_count[col] = 'Match Count: ' + df_Leader_vs_leader_match_count[col].astype(
                int).astype(str)

        # create table cells with tooltip
        def apply_transform(row, other_df):
            result_row = []
            for i in range(len(row)):
                other_df_cell = other_df.loc[row.name, row.index[i]]
                result_row.append(value2color_table_cell(row.iloc[i], max_value=100, cell_input=add_tooltip(row.iloc[i],
                                                                                                            tooltip=other_df_cell), styles=table_cell_styles))
            return result_row

        df_Leader_vs_leader_win_rates_table_cells = df_Leader_vs_leader_win_rates.apply(
            lambda row: apply_transform(row, df_Leader_vs_leader_match_count), axis=1, result_type='expand')

        display_table(df_Leader_vs_leader_win_rates_table_cells,
                      index_cells=index_cells,
                      header_cells=header_cells,
                      title="Matchup Win Rates",
                      key="lmeta_table_item")


def get_leader2avg_win_rate_dict(df_Leader_vs_leader_match_count, df_Leader_vs_leader_win_rates) -> dict[str, float]:
    leader2win_rate: dict[str, float] = {}
    for leader_id, df_row in df_Leader_vs_leader_win_rates.iterrows():
        avg_leader_win_rate = 0
        total_leader_match_count = 0
        for opponent_id, win_rate in df_row.items():
            # exclude mirror matches and NaN data
            if opponent_id == leader_id or pd.isna(win_rate):
                continue
            match_count = df_Leader_vs_leader_match_count.loc[leader_id, opponent_id]
            avg_leader_win_rate += win_rate * match_count
            total_leader_match_count += match_count
        avg_leader_win_rate = avg_leader_win_rate / total_leader_match_count
        leader2win_rate[leader_id] = float("%.1f" % avg_leader_win_rate)
    return leader2win_rate


def add_qparam_on_change_fn(qparam2session_key: dict[str, str]):
    for qparam, session_key in qparam2session_key.items():
        if session_key == "selected_lids":
            selected_leader_names: list[str] = st.session_state[session_key]
            selected_leader_ids = [lname_and_lid_to_lid(lname) for lname in selected_leader_names]
            add_query_param(qparam, selected_leader_ids)
        else:
            raise NotImplementedError


def main_meta_analysis():
    st.header("Leader Matchup")

    with st.sidebar:
        selected_meta_formats: list[MetaFormat] = display_meta_select()
        only_official: bool = display_only_official_toggle()
    if len(selected_meta_formats) == 0:
        st.warning("Please select at least one meta format")
        return None

    leader_extended_data: list[LeaderExtended] = get_leader_extended()
    selected_meta_win_rate_data: list[LeaderWinRate] = get_leader_win_rate(meta_formats=selected_meta_formats)
    df_meta_win_rate_data = pd.DataFrame(
        [lwr.dict() for lwr in selected_meta_win_rate_data if lwr.only_official == only_official])
    if len(df_meta_win_rate_data) == 0:
        st.warning("No leader data available for the selected meta")
        return None

    lid2win_rate, lid2match_count = df_win_rate_data2lid_dicts(df_meta_win_rate_data)
    min_match_count = min(int(max(lid2match_count.values()) * 0.1), 30)

    # first element is leader with best d_score
    leader_extended_data = list(
        filter(lambda x: x.total_matches is not None and x.meta_format in selected_meta_formats and x.total_matches > min_match_count,
               leader_extended_data))
    leader_extended_data.sort(key=lambda x: x.d_score, reverse=True)
    available_leader_ids = list(dict.fromkeys([le.id for le in leader_extended_data]))
    available_leader_names = lids_to_name_and_lids(available_leader_ids)

    # sorted_leader_ids_by_win_rate = sorted([lid for lid, count in lid2match_count.items() if count > min_match_count], key= lambda lid: lid2win_rate[lid], reverse=True)
    # available_leader_ids = lids_to_name_and_lids(list(dict.fromkeys(sorted_leader_ids_by_win_rate)))

    with st.sidebar:
        default_leader_names = get_default_leader_names(available_leader_ids, query_param=Q_PARAM_LEADER_ID)
        if len(set(available_leader_names) - set(default_leader_names)) == 0:
            default_leader_names = default_leader_names[0:5]
        selected_leader_names: list[str] = display_leader_select(available_leader_names=available_leader_names,
                                                                 multiselect=True, default=default_leader_names,
                                                                 key="selected_lids",
                                                                 on_change=partial(add_qparam_on_change_fn,
                                                                                   qparam2session_key={
                                                                                       Q_PARAM_LEADER_ID: "selected_lids"}))
    if len(selected_leader_names) < 2:
        st.warning("Please select at least two leaders")
        return None

    selected_leader_ids: list[str] = [lname_and_lid_to_lid(ln) for ln in selected_leader_names]
    selected_bq_leaders: list[Leader] = [lid2ldata_fn(lid) for lid in selected_leader_ids]
    df_Leader_vs_leader_win_rates, df_Leader_vs_leader_match_count, df_color_win_rates = get_win_rate_dataframes(
        df_meta_win_rate_data, selected_leader_ids)
    radar_chart_data = get_radar_chart_data(df_color_win_rates)
    display_elements(selected_leader_ids,
                     selected_bq_leaders,
                     df_Leader_vs_leader_win_rates,
                     df_Leader_vs_leader_match_count,
                     radar_chart_data)
