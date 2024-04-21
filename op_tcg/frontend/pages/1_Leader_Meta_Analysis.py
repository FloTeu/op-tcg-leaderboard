import random

import pandas as pd
import streamlit as st
from streamlit_elements import elements, mui, html, nivo, dashboard

from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import BQLeader
from op_tcg.frontend.extract import get_leader_data
from op_tcg.frontend.sidebar import display_meta_sidebar, display_leader_sidebar

st.header("Leader Meta Analysis")

st.write("This page is supposted to show detailed meta anlysis similar to this reddit post: https://www.reddit.com/r/OnePieceTCG/comments/19dre7i/op05_meta_analysis_matchup_win_rates_for_128122/#lightbox")

meta_formats: list[MetaFormat] = display_meta_sidebar()
# TODO: Provide a list of available leader_ids based on selected meta (e.g. top 10 leaders with highest win rate/elo)
leader_ids: list[str] = display_leader_sidebar(available_leader_ids=[])
bq_leaders: list[BQLeader] = get_leader_data()
selected_bq_leaders: list[BQLeader] = [l for l in bq_leaders if l.id in leader_ids]

# create random win rates
win_rate_list: list[dict[str, int]] = []
for leader_id in leader_ids:
    win_rate_dict = {}
    for opponent_leader_id in leader_ids:
        win_rate_dict[opponent_leader_id] = random.randint(40,60)
    win_rate_dict["leader_id"] = leader_id
    win_rate_list.append(win_rate_dict)

df_win_rates = pd.DataFrame(win_rate_list)
df_win_rates = df_win_rates.set_index("leader_id")

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
    for leader_id in leader_ids:
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
                print("bq_leaders", bq_leaders)
                table_head=mui.TableHead(children=[mui.TableRow(children=[mui.TableCell(children="Winner\\Opponent")] + [mui.TableCell(children=col) for col in df_win_rates.columns.values])])
                table_rows=[mui.TableRow(children=[mui.TableCell(children=df_row.name)] + [mui.TableCell(children=df_cell) for i, df_cell in df_row.items()]) for i, df_row in df_win_rates.iterrows()]
                table_body=mui.TableBody(children=table_rows)
                mui.Table(
                    children=[table_head, table_body],
                )

            with mui.Box(sx={"height": 1000}, key="first_item"):
                nivo.Radar(
                    data=radar_chart_data,
                    keys=leader_ids,
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