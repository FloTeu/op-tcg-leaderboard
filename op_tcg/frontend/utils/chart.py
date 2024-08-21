from enum import StrEnum

from streamlit_elements import nivo

from op_tcg.backend.models.input import MetaFormat
from streamlit_theme import st_theme

from op_tcg.backend.models.leader import LeaderExtended

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
    data_lines = [
        {
            "x": le.meta_format,
            "y": getattr(le, str(y_value))
        }
        for le in leader_extended_filtered
    ]
    colors = ["rgb(255, 107, 129)" if data_lines[-1]["y"] < data_lines[0]["y"] else "rgb(123, 237, 159)"]
    for meta_format in sorted(MetaFormat.to_list(), reverse=True):
        # exclude OP01 since we have no official matches yet
        if meta_format not in data_lines and meta_format != MetaFormat.OP01:
            data_lines.insert(0, {"x": meta_format, "y": None})

    DATA = [
        {
            "id": "Elo" if y_value == "elo" else "WR",
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
        yFormat=" >-.2f" if y_value == LineChartYValue.WIN_RATE else "",
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
            "legend": str(y_value),
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
