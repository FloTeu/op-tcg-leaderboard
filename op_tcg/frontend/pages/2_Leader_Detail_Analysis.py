import streamlit as st
from streamlit_elements import elements, mui, dashboard, nivo

st.write("Example chart for leader performance vs different colors")

def main():

    with elements("dashboard"):
        # Layout for every element in the dashboard

        layout = [
            # Parameters: element_identifier, x_pos, y_pos, width, height, [item properties...]
            dashboard.Item("ldetailmeta_radar_plot_item", 0, 1, 6, 2, isDraggable=True, isResizable=True),
        ]

        with dashboard.Grid(layout):


            DATA = [
                { "taste": "red", "chardonay": 93, "carmenere": 61, "syrah": 114 },
                { "taste": "blue", "chardonay": 93, "carmenere": 61, "syrah": 114 },
                { "taste": "green", "chardonay": 91, "carmenere": 37, "syrah": 72 },
                { "taste": "purple", "chardonay": 56, "carmenere": 95, "syrah": 99 },
                { "taste": "black", "chardonay": 64, "carmenere": 90, "syrah": 30 },
                { "taste": "yellow", "chardonay": 119, "carmenere": 94, "syrah": 103 },
            ]

            box_elements: list = []
            # box_elements.append(html.H1("Color Win Rates"))
            box_elements.append(nivo.Radar(
                    data=DATA,
                    keys=[ "chardonay", "carmenere", "syrah" ],
                    indexBy="taste",
                    valueFormat=">-.2f",
                    margin={ "top": 70, "right": 80, "bottom": 40, "left": 80 },
                    borderColor={ "from": "color" },
                    gridLabelOffset=36,
                    dotSize=10,
                    dotColor={ "theme": "background" },
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
            )

            mui.Box(key="ldetailmeta_radar_plot_item", children=box_elements)


if __name__ == "__main__":
    main()