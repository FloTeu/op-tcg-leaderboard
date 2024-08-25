from enum import StrEnum
from typing import Any

import pandas as pd
from streamlit_elements import nivo

from op_tcg.backend.models.cards import OPTcgColor
from op_tcg.backend.models.input import MetaFormat
from streamlit_theme import st_theme

from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.frontend.utils.leader_data import lid2ldata_fn

ST_THEME = st_theme(key=str(__file__)) or {"base": "dark"}


class LineChartYValue(StrEnum):
    ELO = "elo"
    WIN_RATE = "win_rate"
    WIN_RATE_DECIMAL = "win_rate_decimal"


def create_leader_line_chart(leader_id: str,
                             leader_extended: list[LeaderExtended],
                             y_value: LineChartYValue = LineChartYValue.ELO,
                             only_official: bool = True,
                             enable_x_axis: bool = False,
                             enable_y_axis: bool = False,
                             ):
    # filter leader data
    leader_extended_filtered = list(
        filter(lambda x: x.id == leader_id and x.only_official == only_official, leader_extended))
    # sort values
    leader_extended_filtered.sort(key=lambda x: x.meta_format)

    data_dict = {
            le.meta_format: getattr(le, str(y_value)) for le in leader_extended_filtered
        }
    return create_line_chart(data_dict,
                             data_id="Elo" if y_value == "elo" else "WR",
                             y_format=" >-.2f" if y_value == LineChartYValue.WIN_RATE else "",
                             enable_x_axis=enable_x_axis,
                             enable_y_axis=enable_y_axis,
                             y_axis_label=str(y_value))

def dict_to_data_lines(data_dict: dict[Any, Any]) -> list[dict[Any, Any]]:
    data_lines = []
    for x, y in data_dict.items():
        data_lines.append({"x": x, "y": y})
    return data_lines


def create_line_chart(data_dict: dict[MetaFormat, str | None],
                      data_id: str,
                      y_format: str | None = None,
                      enable_x_axis: bool = False,
                      enable_y_axis: bool = False,
                      y_axis_label: str = ""):


    # fillup missing meta_format data
    for meta_format in sorted(MetaFormat.to_list(), reverse=True):
        # exclude OP01 since we have no official matches yet
        if meta_format not in data_dict and meta_format != MetaFormat.OP01:
            data_dict[meta_format] = None

    order_mapping = {meta: idx for idx, meta in enumerate(MetaFormat.to_list())}
    data_dict_sorted = dict(sorted(data_dict.items(), key=lambda item: order_mapping[item[0]]))

    data_lines = dict_to_data_lines(data_dict_sorted)
    data_lines_not_none = [dl for dl in data_lines if dl["y"] is not None]

    if len(data_lines_not_none) == 1:
        colors = "rgb(123, 237, 159)"
    else:
        colors = ["rgb(255, 107, 129)" if data_lines_not_none[-1]["y"] < data_lines_not_none[-2]["y"] else "rgb(123, 237, 159)"]


    DATA = [
        {
            "id": data_id,
            "data": data_lines
        }
    ]

    return nivo.Line(
        data=DATA,
        margin={"top": 10, "right": 20, "bottom": 50 if enable_x_axis else 10, "left": 50 if enable_x_axis or enable_y_axis else 10},
        enableGridX=False,
        enableGridY=False,
        yScale={
            "type": "linear",
            "min": "auto"
        },
        pointSize=10,
        pointBorderWidth=0,
        yFormat=y_format,
        axisBottom={
            "tickSize": 5,
            "tickPadding": 5,
            "tickRotation": 0,
            "legend": 'Meta',
            "legendOffset": 36,
            "legendPosition": 'middle',
            "truncateTickAt": 0
        } if enable_x_axis else None,
        axisLeft={
            "tickSize": 5,
            "tickPadding": 5,
            "tickRotation": 0,
            "legend": y_axis_label,
            "legendOffset": -40,
            "legendPosition": 'middle',
            "truncateTickAt": 0
        } if enable_y_axis else None,
        enableSlices="x",
        motionConfig="slow",
        colors=colors,
        theme={
            "background": "#2C3A47" if ST_THEME["base"] == "dark" else "#ffffff",
            "textColor": "#ffffff" if ST_THEME["base"] == "dark" else "#31333F",
            "tooltip": {
                "container": {
                    "background": "#FFFFFF",
                    "color": "#31333F",
                }
            }
        }
    )

def get_radar_chart_data(df_color_win_rates) -> list[dict[str, str | float]]:
    """
    df_color_win_rates: index: leader_id column: color cell: win rate
    """
    # create color chart data
    radar_chart_data: list[dict[str, str | float]] = []
    for color in OPTcgColor.to_list():
        if color in df_color_win_rates.columns.values:
            win_against_color = {lid2ldata_fn(lid).name: win_rate
                                 for lid, win_rate in df_color_win_rates[color].to_dict().items()}
            win_against_color = {k: v if not pd.isna(v) else 50 for k, v in win_against_color.items()}
        else:
            win_against_color = {lid2ldata_fn(lid).name: 50.0 for lid in df_color_win_rates.index.values}
        radar_chart_data.append({
            "color": color,
            **win_against_color
        })
    return radar_chart_data

def create_leader_win_rate_radar_chart(radar_chart_data, selected_leader_names, colors):
    return nivo.Radar(
        data=radar_chart_data,
        keys=selected_leader_names,
        indexBy="color",
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
        colors=colors
    )