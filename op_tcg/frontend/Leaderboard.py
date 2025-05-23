import streamlit as st
st.set_page_config(layout="wide")

from op_tcg.frontend.sub_pages.Leader_Detail_Analysis import add_qparam_on_change_fn
from op_tcg.frontend.sub_pages.utils import sub_page_title_to_url_path
from op_tcg.frontend.utils.js import is_mobile, execute_js_file, prevent_js_frame_height, execute_js_code
from op_tcg.frontend.utils.launch import init_load_data
from op_tcg.frontend.views.component import ElementsComponentView

import os
import numpy as np
import pandas as pd

from functools import partial
from datetime import datetime, date
from uuid import uuid4

from op_tcg.frontend.utils.chart import LineChartYValue, create_leader_line_chart
from op_tcg.frontend.sub_pages.constants import SUB_PAGE_LEADER_MATCHUP, SUB_PAGE_CARD_POPULARITY, SUB_PAGE_LEADER, \
    SUB_PAGE_LEADER_CARD_MOVEMENT, Q_PARAM_LEADER_ID, Q_PARAM_META, SUB_PAGE_TOURNAMENT
from op_tcg.backend.utils.utils import booleanize
from op_tcg.backend.etl.load import bq_insert_rows, get_or_create_table
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.leader import LeaderExtended, LeaderboardSortBy
from op_tcg.backend.models.cards import OPTcgColor
from op_tcg.backend.models.matches import Match, MatchResult
from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.frontend.utils.session import get_session_id, reset_session_state, SessionKeys
from op_tcg.frontend.sidebar import display_meta_select, display_only_official_toggle, display_release_meta_select, \
    display_match_count_slider_slider, display_leader_color_multiselect, display_leader_select, display_sortby_select, display_meta_format_region
from op_tcg.frontend.utils.extract import get_leader_extended
from op_tcg.frontend.utils.styles import execute_style_sheet, read_style_sheet, css_rule_to_dict
from op_tcg.frontend.utils.material_ui_fns import display_table, create_image_cell, value2color_table_cell
from op_tcg.frontend.utils.leader_data import get_lid2ldata_dict_cached, lids_to_name_and_lids, lname_and_lid_to_lid, \
    calculate_dominance_score
from op_tcg.frontend.utils.utils import bq_client
from op_tcg.frontend.sub_pages import (main_meta_analysis, main_leader_card_movement,
                                       main_leader_detail_analysis, main_admin_leader_upload,
                                       main_card_meta_analysis, main_bug_report, main_tournaments
                                       )

from streamlit_elements import elements, dashboard, mui

prevent_js_frame_height()


def change_sidebar_collapse_button_style():
    if is_mobile():
        execute_style_sheet("sidebar_button")


def leader_id2line_chart(leader_id: str, df_leader_extended, y_value: LineChartYValue = LineChartYValue.WIN_RATE,
                         visible_meta_formats: list[MetaFormat] = None, only_official: bool = True, enable_x_top_axis: bool = False):
    leader_extended_list: list[LeaderExtended] = df_leader_extended.replace({np.nan:None}).query(f"id == '{leader_id}'").apply(
        lambda row: LeaderExtended(**row), axis=1).tolist()
    leader_extended_list = [le for le in leader_extended_list if le.meta_format in visible_meta_formats]
    line_plot = create_leader_line_chart(leader_id, leader_extended_list, y_value=y_value, only_official=only_official,
                                         use_custom_component=False, enable_x_top_axis=enable_x_top_axis, fillup_meta_formats=visible_meta_formats)
    return mui.TableCell(mui.Box(line_plot, sx={"height": 120, "width": 190}), sx={"padding": "0px"})


def add_dominance_score(df_meta_group: pd.DataFrame) -> pd.DataFrame:
    # Extract max values for normalization
    max_values = {
        "win_rate": df_meta_group["win_rate"].max(),
        "total_matches": df_meta_group["total_matches"].max(),
        "elo": df_meta_group["elo"].max(),
        "tournament_wins": df_meta_group["tournament_wins"].max()
    }
    df_meta_group[LeaderboardSortBy.DOMINANCE_SCORE.value] = df_meta_group.apply(
        lambda x: f"""{int(round(calculate_dominance_score(
            win_rate_norm=(x.win_rate / max_values["win_rate"]),
            total_matches_norm=(x.total_matches / max_values["total_matches"]),
            elo_rating_norm=(x.elo / max_values["elo"]),
            tournament_wins_norm=(x.tournament_wins / max_values["tournament_wins"]),
        ), 2) * 100)}%""", axis=1)
    return df_meta_group


def display_leaderboard_table(df_leader_extended: LeaderExtended.paSchema(), meta_format: MetaFormat,
                              display_name2df_col_name: dict[str, str], only_official: bool = True, key="leaderboard_table"):
    # Define a callback function to handle link click
    def open_leader_page(leader_id: str):
        meta_format = st.query_params.get(Q_PARAM_META, None)
        url = f"/{sub_page_title_to_url_path(SUB_PAGE_LEADER)}?{Q_PARAM_LEADER_ID}={leader_id}"
        if meta_format:
            url = f"{url}&{Q_PARAM_META}={meta_format}"
        script = f'parent.window.open("{url}", "_self")'
        execute_js_code(script)

    # Add new cols
    df_leader_extended['win_rate_decimal'] = df_leader_extended['win_rate'].apply(lambda x: f"{x * 100:.2f}%")

    # data preprocessing
    all_meta_formats = MetaFormat.to_list()
    relevant_meta_formats = all_meta_formats[:all_meta_formats.index(meta_format) + 1]
    visible_meta_formats = relevant_meta_formats[max(0, len(relevant_meta_formats) - 5):]
    df_leader_extended = df_leader_extended.query("meta_format in @relevant_meta_formats")
    df_leader_extended_selected_meta = df_leader_extended.query(f"meta_format == '{meta_format}'").copy()
    if len(df_leader_extended_selected_meta) == 0:
        st.warning("No leader data available for the selected meta")
        return None

    display_columns = ["Name", "Set", LeaderboardSortBy.TOURNAMENT_WINS, "Match Count",
                       LeaderboardSortBy.WIN_RATE, LeaderboardSortBy.DOMINANCE_SCORE.value, "Elo"]
    df_leader_extended_selected_meta["Set"] = df_leader_extended_selected_meta["id"].apply(
        lambda lid: lid.split("-")[0])
    df_leader_extended_selected_meta['d_score'] = df_leader_extended_selected_meta['d_score'].apply(
        lambda x: f"{int(x * 100)}%")
    # df_leader_extended_selected_meta["Name"] = df_leader_extended_selected_meta["id"]  # .apply(lambda lid: lid2ldata(lid).name.replace('"', " ").replace('.', " "))
    for display_name, df_col_name in display_name2df_col_name.items():
        if display_name == LeaderboardSortBy.WIN_RATE:
            df_col_name = "win_rate_decimal"
        df_leader_extended_selected_meta[str(display_name)] = df_leader_extended_selected_meta[df_col_name]
    table_cell_styles = css_rule_to_dict(read_style_sheet("table", ".colored-table-cell"))

    with elements(key):
        # Layout for every element in the dashboard

        layout = [
            # Parameters: element_identifier, x_pos, y_pos, width, height, [item properties...]
            dashboard.Item("lboard_table_item", 0, 0, 12, 6, isResizable=False, isDraggable=False),
        ]

        # reset index in order to get ranking in index cell right
        df_leader_extended_selected_meta.reset_index(drop=True, inplace=True)

        with dashboard.Grid(layout):
            index_cells = [[create_image_cell(df_row.aa_image_url,
                                              text=f"#{i + 1}",
                                              overlay_color=df_row.color_hex_code,
                                              horizontal=True) for
                            i, df_row in df_leader_extended_selected_meta.iterrows()]]
            # keep only relevant columns
            df_leader_elos_filtered = df_leader_extended_selected_meta.drop(
                columns=[c for c in df_leader_extended_selected_meta.columns if c not in (display_columns + ["id"])])[
                display_columns + ["id"]]

            header_stylings = css_rule_to_dict(read_style_sheet("table", ".sticky-header"))
            header_cells = [mui.TableCell(children="Leader", sx={"width": "200px", **header_stylings})] + [
                mui.TableCell(col, sx=header_stylings) for col in
                (display_columns + [
                    "Win Rate Chart"])]

            df_leaderboard_display = df_leader_elos_filtered.copy()
            for col in display_columns:
                # df_leader_elos_display = df_leader_elos_display.map(lambda x: mui.TableCell(str(x)))
                if col == "Elo":
                    max_elo = df_leaderboard_display[col].max()
                    df_leaderboard_display[col] = df_leaderboard_display[col].apply(
                        lambda elo: value2color_table_cell(elo, max_value=max_elo,
                                                           color_switch_threshold=1000 if 1000 < max_elo else (
                                                                   max_elo * (7 / 8)), styles=table_cell_styles))
                elif col == "Name":
                    df_leaderboard_display[col] = df_leaderboard_display[[col, "id"]].apply(
                        lambda x: mui.TableCell(mui.Link(
                            str(x.Name.replace('"', " ").replace('.', " ")) if x.Name else "NaN",
                            onClick=partial(open_leader_page, leader_id=x.id),  # Call the function to open the link
                            style={"cursor": "pointer"}
                        )
                        ), axis=1)
                else:
                    df_leaderboard_display[col] = df_leaderboard_display[col].apply(lambda x: mui.TableCell(str(x)))

            df_leaderboard_display = df_leaderboard_display.drop(columns=["id"])
            first_lid = df_leader_extended_selected_meta.iloc[0].id
            df_leaderboard_display["Elo Chart"] = df_leader_extended_selected_meta["id"].apply(
                lambda lid: leader_id2line_chart(lid, df_leader_extended, y_value=LineChartYValue.WIN_RATE,
                                                 visible_meta_formats=visible_meta_formats,
                                                 only_official=only_official, enable_x_top_axis=lid == first_lid))

            display_table(df_leaderboard_display,
                          index_cells=index_cells,
                          header_cells=header_cells,
                          title=None,
                          key="lboard_table_item")


def sort_table_df(df: LeaderExtended.paSchema(), sort_by: LeaderboardSortBy,
                  display_name2df_col_name: dict[str, str]) -> LeaderExtended.paSchema():
    df_col_name = display_name2df_col_name[sort_by] if sort_by in display_name2df_col_name else sort_by
    # sort table
    if sort_by == LeaderboardSortBy.TOURNAMENT_WINS:
        # Custom sorting key
        df['sort_key'] = df.apply(
            lambda row: (row[df_col_name] > 0, row[df_col_name], row[display_name2df_col_name[LeaderboardSortBy.ELO]]),
            axis=1)
        # Sort the DataFrame using the custom sort key
        df = df.sort_values(by='sort_key', ascending=False).reset_index()
        # Drop the temporary sort key column
        df = df.drop(columns=['sort_key'])
    else:
        df = df.sort_values(df_col_name, ascending=False).reset_index()
    return df


@st.dialog("Upload Match")
def upload_match_dialog():
    st.session_state[SessionKeys.MODAL_OPEN_CLICKED] = True

    leader_id2leader_data = get_lid2ldata_dict_cached()
    meta_format = display_meta_select(multiselect=False, key="upload_form_meta_format")[0]
    allowed_meta_fomats = MetaFormat.to_list()[0:MetaFormat.to_list().index(meta_format) + 1]

    default_winner = st.session_state.get("match_leader_id", None)
    default_loser = st.session_state.get("match_opponent_leader_id", None)
    if st.button("Switch Leaders"):
        if st.session_state.match_leader_id:
            default_loser = st.session_state.match_leader_id
        if st.session_state.match_opponent_leader_id:
            default_winner = st.session_state.match_opponent_leader_id

    with st.form("upload_match_form"):
        available_leader_ids = [lid for lid, ldata in leader_id2leader_data.items() if
                                ldata.meta_format in allowed_meta_fomats]
        available_leader_ids = sorted(available_leader_ids)
        # add name to ids (drop duplicates and ensures right order)
        available_leader_names: list[str] = lids_to_name_and_lids(
            list([lid for lid in dict.fromkeys(available_leader_ids) if lid in leader_id2leader_data]))

        # display user input
        today_date = datetime.now().date()
        match_day: date = st.date_input("Match Day", value=today_date, max_value=today_date)
        match_datetime: datetime = datetime.combine(match_day, datetime.now().time())

        selected_winner_leader_name: str | None = display_leader_select(available_leader_names=available_leader_names,
                                                                        multiselect=False, label="Winner Leader",
                                                                        default=default_winner,
                                                                        key="match_leader_id")
        selected_winner_leader_id: str | None = lname_and_lid_to_lid(
            selected_winner_leader_name) if selected_winner_leader_name is not None else None

        selected_loser_leader_name: str | None = display_leader_select(available_leader_names=available_leader_names,
                                                                       multiselect=False, label="Looser Leader",
                                                                       default=default_loser,
                                                                       key="match_opponent_leader_id")
        selected_loser_leader_id: str | None = lname_and_lid_to_lid(
            selected_loser_leader_name) if selected_loser_leader_name is not None else None
        is_draw = st.checkbox("Is draw", value=False)

        # Every form must have a submit button.
        submitted = st.form_submit_button("Submit")
        if submitted:
            if selected_loser_leader_id is None or selected_winner_leader_id is None:
                st.warning("Winner or loser leader not yet selected")
            else:
                match_id = uuid4().hex
                session_id = get_session_id()
                rows_to_insert = []
                rows_to_insert.append(Match(id=match_id,
                                            leader_id=selected_winner_leader_id,
                                            opponent_id=selected_loser_leader_id,
                                            result=MatchResult.DRAW if is_draw else MatchResult.WIN,
                                            meta_format=meta_format,
                                            official=False,
                                            is_reverse=False,
                                            source=session_id,
                                            match_timestamp=match_datetime).model_dump()
                                      )
                rows_to_insert.append(Match(id=match_id,
                                            leader_id=selected_loser_leader_id,
                                            opponent_id=selected_winner_leader_id,
                                            result=MatchResult.DRAW if is_draw else MatchResult.LOSE,
                                            meta_format=meta_format,
                                            official=False,
                                            is_reverse=True,
                                            source=session_id,
                                            match_timestamp=match_datetime).model_dump()
                                      )

                bq_leader_table = get_or_create_table(model=Match, dataset_id=BQDataset.MATCHES,
                                                      client=bq_client)
                try:
                    bq_insert_rows(rows_to_insert, table=bq_leader_table, client=bq_client)
                    st.balloons()
                except Exception as e:
                    st.error(str(e))


def main():
    change_sidebar_collapse_button_style()

    # display data
    st.header("One Piece TCG Elo Leaderboard")

    # Make sidebar button bounce for leaderboard page
    execute_js_file("add_sidebar_bounce", display_none=True)

    if not st.session_state.get("launch_succeeded", False):
        with st.spinner("Launch App"):
            init_load_data()
            st.session_state["launch_succeeded"] = True

    with st.sidebar:
        meta_format: MetaFormat = display_meta_select(multiselect=False,
                                                      on_change=partial(add_qparam_on_change_fn,
                                                                       qparam2session_key={
                                                                           Q_PARAM_META: "selected_meta_format"}),
                                                      key="selected_meta_format",
                                                      )[0]
        meta_format_region: MetaFormatRegion = display_meta_format_region(multiselect=False)[0]
        release_meta_formats: list[MetaFormat] | None = display_release_meta_select(multiselect=True)
        selected_leader_colors: list[OPTcgColor] | None = display_leader_color_multiselect()
        display_max_match_count = 10000
        match_count_min, match_count_max = display_match_count_slider_slider(min=0, max=display_max_match_count)
        only_official: bool = display_only_official_toggle()
        sort_by: LeaderboardSortBy = display_sortby_select(LeaderboardSortBy)

    display_name2df_col_name = {
        "Name": "name",
        LeaderboardSortBy.DOMINANCE_SCORE.value: "d_score",
        LeaderboardSortBy.TOURNAMENT_WINS.value: "tournament_wins",
        "Match Count": "total_matches",
        LeaderboardSortBy.WIN_RATE.value: "win_rate",
        LeaderboardSortBy.ELO.value: "elo",
    }
    # get data
    leader_extended_data: list[LeaderExtended] = get_leader_extended(meta_format_region=meta_format_region)

    # drop None values
    required_values = ["elo", "win_rate", "total_matches", "only_official"]
    leader_extended_data: list[LeaderExtended] = list(
        filter(lambda x: all(getattr(x, v) is not None for v in required_values), leader_extended_data))

    def filter_fn(le: LeaderExtended) -> bool:
        keep_le = le.only_official == only_official
        # filter release_meta_formats
        if release_meta_formats:
            keep_le = keep_le and (le.release_meta_format in release_meta_formats)
        # filter colors
        if selected_leader_colors:
            keep_le = keep_le and any(lcolor in selected_leader_colors for lcolor in le.colors)
        # filter match_count
        if match_count_min:
            keep_le = keep_le and (le.total_matches >= match_count_min)
        if match_count_max != display_max_match_count:
            keep_le = keep_le and (le.total_matches <= match_count_max)
        return keep_le

    # run filters
    leader_extended_data = list(filter(lambda x: filter_fn(x), leader_extended_data))

    if st.button("Upload Match"):
        upload_match_dialog()
    if leader_extended_data:
        # display table.
        df_leader_extended = pd.DataFrame(
            [{**r.dict(), "color_hex_code": r.to_hex_color()} for r in leader_extended_data])
        df_leader_extended = sort_table_df(df_leader_extended, sort_by=sort_by,
                                           display_name2df_col_name=display_name2df_col_name)

        fn_args = (df_leader_extended, meta_format, display_name2df_col_name, only_official)
        fn_kwargs = {"key": "leaderboard_table"}

        # include retry if page is loaded for the first time
        if st.session_state.get(SessionKeys.MODAL_OPEN_CLICKED, False):
            ElementsComponentView(display_leaderboard_table, *fn_args, **fn_kwargs).rerender()
        else:
            ElementsComponentView(display_leaderboard_table, *fn_args, **fn_kwargs).display(retries=1)

        st.markdown(
            "*D-Score: Composite score from multiple metrics defining the dominance a leader has in the selected meta (Formula: $win\_rate * 0.1 + matches * 0.3 + elo * 0.2 + tournament\_wins * 0.4$ )")

    else:
        st.warning("Seems like the selected meta does not contain any matches")

    reset_session_state()


# main_meta_analysis, main_leader_detail_analysis_decklists, main_leader_detail_anylsis, main_admin_leader_upload
pages: dict[str, st.Page] = {"Leader": [
        st.Page(main, title="Leaderboard", icon="🏆", default=True),
        st.Page(main_leader_detail_analysis, title="Leader", icon="👤", url_path=sub_page_title_to_url_path(SUB_PAGE_LEADER)),
        st.Page(main_tournaments, title="Tournaments", icon="🏅", url_path=sub_page_title_to_url_path(SUB_PAGE_TOURNAMENT)),
        # st.Page(main_leader_detail_analysis_decklists, title=SUB_PAGE_LEADER_DECKLIST, url_path=SUB_PAGE_LEADER_DECKLIST),
        st.Page(main_leader_card_movement, title="Card Movement", icon="📈",
                url_path=sub_page_title_to_url_path(SUB_PAGE_LEADER_CARD_MOVEMENT)),
        st.Page(main_meta_analysis, title="Matchups", icon="🥊", url_path=sub_page_title_to_url_path(SUB_PAGE_LEADER_MATCHUP)),
    ],
    "Card": [
        st.Page(main_card_meta_analysis, title=SUB_PAGE_CARD_POPULARITY, icon="💃",
                url_path=sub_page_title_to_url_path(SUB_PAGE_CARD_POPULARITY)),
    ],
    "Support": [
        st.Page(main_bug_report, icon="👾", title="Bug Report")
    ]
}

# admin_password = st.sidebar.text_input("Show Admin Page")
# if admin_password in st.secrets["admin"]["emails"]:
#     pages.append(st.Page(main_admin_leader_upload, title='Admin_Leader_Upload', url_path="Admin_Leader_Upload"))

if booleanize(os.environ.get("DEBUG", "")):
    # if not admin_password in st.secrets["admin"]["emails"]:
    pages["Admin"] = [st.Page(main_admin_leader_upload, title='Admin_Leader_Upload', url_path="Admin_Leader_Upload")]

pg = st.navigation(pages)
pg.run()
