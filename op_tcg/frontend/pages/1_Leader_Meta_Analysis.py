import pandas as pd
import streamlit as st
from streamlit_elements import elements, mui, html, nivo, dashboard
from streamlit_theme import st_theme

from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import Leader, OPTcgColor
from op_tcg.backend.models.matches import Match, LeaderElo
from op_tcg.frontend.utils.extract import get_leader_data, get_match_data, get_leader_elo_data
from op_tcg.frontend.sidebar import display_meta_sidebar, display_leader_sidebar
from op_tcg.frontend.utils.material_ui_fns import create_image_cell, display_table

st.set_page_config(layout="wide")

ST_THEME = st_theme()


# TODO: Provide a list of available leader_ids based on selected meta (e.g. top 10 leaders with highest win rate/elo)


def data_setup(selected_leader_names, selected_meta_formats, leader_id2leader_data):
    selected_leader_ids: list[str] = [ln.split("(")[1].strip(")") for ln in selected_leader_names]
    selected_bq_leaders: list[Leader] = [l for l in bq_leaders if l.id in selected_leader_ids]
    selected_match_data: list[Match] = get_match_data(meta_formats=selected_meta_formats,
                                                      leader_ids=selected_leader_ids)
    df_selected_match_data = pd.DataFrame([match.dict() for match in selected_match_data])

    # Create a new DataFrame with color information
    color_info = []
    for leader_id, leader_data in leader_id2leader_data.items():
        if leader_data:
            for color in leader_data.colors:
                color_info.append({'opponent_id': leader_id, 'color': color})

    # Convert the color_info list to a DataFrame
    df_color_info = pd.DataFrame(color_info)
    df_selected_color_match_data = df_selected_match_data.merge(df_color_info, on='opponent_id', how='left')

    # Calculate win rates
    def calculate_win_rate(df_matches: pd.DataFrame) -> float:
        return float("%.1f" % (((df_matches['result'] == 2).sum() / len(df_matches)) * 100))

    win_rates_series = df_selected_match_data[df_selected_match_data["opponent_id"].isin(selected_leader_ids)].groupby(
        ["leader_id", "opponent_id"]).apply(calculate_win_rate, include_groups=False)
    df_Leader_vs_leader_win_rates = win_rates_series.unstack(level=-1)

    # calculate match counts between leaders
    def calculate_match_count(df_matches: pd.DataFrame) -> float:
        return len(df_matches)

    match_counts_series = df_selected_match_data[df_selected_match_data["opponent_id"].isin(selected_leader_ids)].groupby(
        ["leader_id", "opponent_id"]).apply(calculate_match_count, include_groups=False)
    df_Leader_vs_leader_match_count = match_counts_series.unstack(level=-1)


    win_rates_series = df_selected_color_match_data.groupby(["leader_id", "color"]).apply(calculate_win_rate,
                                                                                          include_groups=False)
    df_color_win_rates = win_rates_series.unstack(level=-1)

    return selected_leader_ids, selected_bq_leaders, df_Leader_vs_leader_win_rates, df_Leader_vs_leader_match_count, df_color_win_rates


def get_radar_chart_data(df_color_win_rates, leader_id2leader_data) -> list[dict[str, str | float]]:
    # create color chart data
    radar_chart_data: list[dict[str, str | float]] = []
    for color in OPTcgColor.to_list():
        if color in df_color_win_rates.columns.values:
            win_against_color = {leader_id2leader_data.get(lid).name: win_rate
                                 for lid, win_rate in df_color_win_rates[color].to_dict().items()}
            win_against_color = {k: v if not pd.isna(v) else 50 for k, v in win_against_color.items()}
        else:
            win_against_color = {leader_id2leader_data.get(lid).name: 50.0 for lid in df_color_win_rates.index.values}
        radar_chart_data.append({
            "taste": color,
            **win_against_color
        })
    return radar_chart_data


def display_elements(selected_leader_ids,
                     selected_bq_leaders,
                     df_Leader_vs_leader_win_rates,
                     df_Leader_vs_leader_match_count,
                     radar_chart_data,
                     leader_id2leader_data: dict[str, Leader]):
    def lid2name(leader_id: str) -> str:
        return leader_id2leader_data.get(leader_id).name

    def lid2meta(leader_id: str) -> MetaFormat | str:
        return leader_id2leader_data.get(leader_id).id.split("-")[0]


    # The rest of your code remains the same...

    with elements("dashboard"):
        # You can create a draggable and resizable dashboard using
        # any element available in Streamlit Elements.

        # First, build a default layout for every element you want to include in your dashboard

        layout = [
            # Parameters: element_identifier, x_pos, y_pos, width, height, [item properties...]
            dashboard.Item("radar_plot_item_title", 0, 0, 3, 0.5, isDraggable=False, isResizable=False),
            dashboard.Item("radar_plot_item", 0, 1, 6, 2, isDraggable=True, isResizable=True),
            dashboard.Item("avatar_group_item", 4, 0, 2, 0.5, isDraggable=True),
            dashboard.Item("table_item", 0, 3, 6, 6, isResizable=False, isDraggable=False),
        ]

        def handle_layout_change(updated_layout):
            # You can save the layout in a file, or do anything you want with it.
            # You can pass it back to dashboard.Grid() if you want to restore a saved layout.
            pass

        with dashboard.Grid(layout, onLayoutChange=handle_layout_change):
            children = [mui.Avatar(src=l.avatar_icon_url) for l in selected_bq_leaders]
            mui.AvatarGroup(children=children, key="avatar_group_item")


            # leader win rate
            leader2win_rate = get_leader2avg_win_rate_dict(df_Leader_vs_leader_match_count,
                                                           df_Leader_vs_leader_win_rates)
            sorted_leader_ids: list[str] = sorted(leader2win_rate, key=leader2win_rate.get, reverse=True)

            # sort data based on win rate
            df_Leader_vs_leader_win_rates = df_Leader_vs_leader_win_rates.loc[sorted_leader_ids]
            df_Leader_vs_leader_match_count = df_Leader_vs_leader_match_count.loc[sorted_leader_ids]
            df_Leader_vs_leader_win_rates = df_Leader_vs_leader_win_rates.loc[:,sorted_leader_ids]
            df_Leader_vs_leader_match_count = df_Leader_vs_leader_match_count.loc[:,sorted_leader_ids]


            header_cells = [mui.TableCell(children="Winner\\Opponent"), mui.TableCell(children="Win Rate")] + [create_image_cell(leader_id2leader_data[col].image_url, lid2name(col), overlay_color=leader_id2leader_data[col].to_hex_color(), horizontal=False) for col in
                          df_Leader_vs_leader_win_rates.columns.values]
            index_cells = []
            index_cells.append([create_image_cell(leader_id2leader_data[leader_id].image_aa_url,
                            lid2meta(leader_id) + "\n" + lid2name(leader_id), overlay_color=leader_id2leader_data[leader_id].to_hex_color()) for leader_id, df_row in df_Leader_vs_leader_win_rates.iterrows()])
            index_cells.append([leader2win_rate[leader_id] for leader_id in sorted_leader_ids])

            for col in df_Leader_vs_leader_match_count.columns.values:
                df_Leader_vs_leader_match_count[col] = df_Leader_vs_leader_match_count[col].fillna(0)
                df_Leader_vs_leader_match_count[col] = 'Match Count: ' + df_Leader_vs_leader_match_count[col].astype(int).astype(str)

            display_table(df_Leader_vs_leader_win_rates,
                          df_tooltip=df_Leader_vs_leader_match_count,
                          index_cells=index_cells,
                          header_cells=header_cells,
                          title="Matchup Win Rates",
                          key="table_item")

            mui.Box(sx={"font-family": '"Source Sans Pro", sans-serif;'}, key="radar_plot_item_title")(html.H2("Leader Color Win Rates"))
            box_elements: list = []
            #box_elements.append(html.H1("Color Win Rates"))
            box_elements.append(nivo.Radar(
                    data=radar_chart_data,
                    keys=[lid2name(lid) for lid in selected_leader_ids],
                    indexBy="taste",
                    valueFormat=">-.2f",
                    margin={"top": 70, "right": 80, "bottom": 70, "left": 80},
                    borderColor={"from": "color"},
                    gridLabelOffset=36,
                    dotSize=10,
                    dotColor={"theme": "background"},
                    dotBorderWidth=2,
                    motionConfig="wobbly",
                    legends=[
                        {
                            "anchor": "top-left",
                            "direction": "column",
                            "translateX": -50,
                            "translateY": -40,
                            "itemWidth": 80,
                            "itemHeight": 20,
                            "itemTextColor": "#ffffff" if ST_THEME["base"] == "dark" else "#999",
                            "symbolSize": 12,
                            "symbolShape": "circle",
                            "effects": [
                                {
                                    "on": "hover",
                                    "style": {
                                        "itemTextColor": "#000"
                                    }
                                }
                            ]
                        }
                    ],
                    theme={
                        "background": "#2C3A47" if ST_THEME["base"] == "dark" else "#ffffff",
                        "textColor": "#ffffff" if ST_THEME["base"] == "dark" else "#31333F",
                        "tooltip": {
                            "container": {
                                "background": "#FFFFFF",
                                "color": "#31333F",
                            }
                        }
                    },
                    colors=[leader_id2leader_data[lid].to_hex_color() for lid in selected_leader_ids]
                ))

            mui.Box(key="radar_plot_item", children=box_elements)


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


st.header("Leader Meta Analysis")

# TODO clean code up

selected_meta_formats: list[MetaFormat] = display_meta_sidebar()
if len(selected_meta_formats) == 0:
    st.warning("Please select at least one meta format")
else:
    selected_leader_elo_data: list[LeaderElo] = get_leader_elo_data(meta_formats=selected_meta_formats)
# first element is leader with best elo
sorted_leader_elo_data: list[LeaderElo] = sorted(selected_leader_elo_data, key=lambda x: x.elo,
                                                 reverse=True)
bq_leaders: list[Leader] = get_leader_data()
leader_id2leader_data: dict[str, Leader] = {bq_leader_data.id: bq_leader_data for bq_leader_data in
                                            bq_leaders}
available_leader_ids = list(dict.fromkeys(
    [
        f"{leader_id2leader_data[l.leader_id].name if l.leader_id in leader_id2leader_data else ''} ({l.leader_id})"
        for l
        in sorted_leader_elo_data]))
selected_leader_names: list[str] = display_leader_sidebar(available_leader_ids=available_leader_ids)
if len(selected_leader_names) < 2:
    st.warning("Please select at least two leaders")
else:
    selected_leader_ids, selected_bq_leaders, df_Leader_vs_leader_win_rates, df_Leader_vs_leader_match_count, df_color_win_rates = data_setup(
        selected_leader_names, selected_meta_formats, leader_id2leader_data)
    radar_chart_data = get_radar_chart_data(df_color_win_rates, leader_id2leader_data)
    display_elements(selected_leader_ids,
                     selected_bq_leaders,
                     df_Leader_vs_leader_win_rates,
                     df_Leader_vs_leader_match_count,
                     radar_chart_data,
                     leader_id2leader_data)
