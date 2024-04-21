import random

import pandas as pd
import streamlit as st
from streamlit_elements import elements, mui, html, nivo, dashboard

from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import BQLeader
from op_tcg.backend.models.matches import BQMatch, BQLeaderElo
from op_tcg.frontend.extract import get_leader_data, get_match_data, get_leader_elo_data
from op_tcg.frontend.sidebar import display_meta_sidebar, display_leader_sidebar

st.header("Leader Meta Analysis")

st.write(
    "This page is supposted to show detailed meta anlysis similar to this reddit post: https://www.reddit.com/r/OnePieceTCG/comments/19dre7i/op05_meta_analysis_matchup_win_rates_for_128122/#lightbox")

selected_meta_formats: list[MetaFormat] = display_meta_sidebar()
selected_leader_elo_data: list[BQLeaderElo] = get_leader_elo_data(meta_formats=selected_meta_formats)
# first element is leader with best elo
sorted_leader_elo_data: list[BQLeaderElo] = sorted(selected_leader_elo_data, key=lambda x: x.elo, reverse=True)
bq_leaders: list[BQLeader] = get_leader_data()
leader_id2leader_data: dict[str, BQLeader] = {bq_leader_data.id: bq_leader_data for bq_leader_data in bq_leaders}

# TODO: Provide a list of available leader_ids based on selected meta (e.g. top 10 leaders with highest win rate/elo)
available_leader_ids = list(dict.fromkeys([f"{leader_id2leader_data[l.leader_id].name if l.leader_id in leader_id2leader_data else ''} ({l.leader_id})" for l
    in sorted_leader_elo_data]))
selected_leader_names: list[str] = display_leader_sidebar(available_leader_ids=available_leader_ids)
selected_leader_ids: list[str] = [ln.split("(")[1].strip(")") for ln in selected_leader_names]
selected_bq_leaders: list[BQLeader] = [l for l in bq_leaders if l.id in selected_leader_ids]
selected_match_data: list[BQMatch] = get_match_data(meta_formats=selected_meta_formats, leader_ids=selected_leader_ids)
df_selected_match_data = pd.DataFrame([match.dict() for match in selected_match_data])

# Calculate win rates
def calculate_win_rate(df_matches: pd.DataFrame):
    return "%.1f" % (((df_matches['result'] == 2).sum() / len(df_matches)) * 100) + "%"

win_rates_series = df_selected_match_data.groupby(["leader_id", "opponent_id"]).apply(calculate_win_rate, include_groups=False)
df_win_rates = win_rates_series.unstack(level=-1)

radar_chart_data = [
    {"taste": "red"},
    {"taste": "gree"},
    {"taste": "blue"},
    {"taste": "purple"},
    {"taste": "black"},
    {"taste": "yellow"},
]

# create random data
for data_row in radar_chart_data:
    for leader_id in selected_leader_ids:
        data_row[leader_id] = random.randint(50, 100)


def display_elements():
    with elements("dashboard"):
        # You can create a draggable and resizable dashboard using
        # any element available in Streamlit Elements.

        # First, build a default layout for every element you want to include in your dashboard

        layout = [
            # Parameters: element_identifier, x_pos, y_pos, width, height, [item properties...]
            dashboard.Item("first_item", 0, 0, 2, 2),
            dashboard.Item("second_item", 2, 0, 2, 2, isDraggable=False, moved=False),
            dashboard.Item("third_item", 0, 2, 4, 4, isResizable=True, movex=True),
        ]

        def handle_layout_change(updated_layout):
            # You can save the layout in a file, or do anything you want with it.
            # You can pass it back to dashboard.Grid() if you want to restore a saved layout.
            print(updated_layout)

        with dashboard.Grid(layout, onLayoutChange=handle_layout_change):
            children = [mui.Avatar(src=l.avatar_icon_url) for l in selected_bq_leaders]
            mui.AvatarGroup(children=children, key="second_item")

            with mui.Table(key="third_item"):
                table_head = mui.TableHead(children=[mui.TableRow(
                    children=[mui.TableCell(children="Winner\\Opponent")] + [mui.TableCell(children=col) for col in
                                                                             df_win_rates.columns.values])])
                table_rows = [mui.TableRow(
                    children=[mui.TableCell(children=df_row.name)] + [mui.TableCell(children=df_cell) for i, df_cell in
                                                                      df_row.items()]) for i, df_row in
                              df_win_rates.iterrows()]
                table_body = mui.TableBody(children=table_rows)
                mui.Table(
                    children=[table_head, table_body],
                )

            with mui.Box(sx={"height": 1000}, key="first_item"):
                nivo.Radar(
                    data=radar_chart_data,
                    keys=selected_leader_ids,
                    indexBy="taste",
                    valueFormat=">-.2f",
                    margin={"top": 70, "right": 80, "bottom": 40, "left": 80},
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
                            "itemTextColor": "#999",
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
                        "background": "#FFFFFF",
                        "textColor": "#31333F",
                        "tooltip": {
                            "container": {
                                "background": "#FFFFFF",
                                "color": "#31333F",
                            }
                        }
                    }
                )


display_elements()
