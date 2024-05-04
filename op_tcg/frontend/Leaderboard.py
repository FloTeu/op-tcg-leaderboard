import pandas as pd
import streamlit as st

st.set_page_config(layout="wide")
from streamlit_elements import elements, dashboard, mui, nivo
from streamlit_theme import st_theme

from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import Leader, OPTcgColor
from op_tcg.backend.models.matches import LeaderElo, BQLeaderElos, Match
from op_tcg.frontend.sidebar import display_meta_select, display_only_official_toggle, display_release_meta_select, \
    display_match_count_slider_slider, display_leader_color_multiselect, display_leader_multiselect
from op_tcg.frontend.utils.extract import get_leader_elo_data, get_leader_data, get_match_data
from op_tcg.frontend.utils.material_ui_fns import display_table, create_image_cell, value2color_table_cell
from op_tcg.frontend.utils.utils import leader_id2aa_image_url

ST_THEME = st_theme() or {"base": "dark"}

def leader_id2elo_chart(leader_id: str, df_leader_elos):
    # Streamlit Elements includes 45 dataviz components powered by Nivo.
    data_lines = df_leader_elos.query(f"leader_id == '{leader_id}'").sort_values("meta_format")[["meta_format", "elo"]].rename(columns={"meta_format": "x", "elo": "y"}).to_dict(orient="records")
    colors = [
        "rgb(255, 107, 129)" if data_lines[-1]["y"] < data_lines[0]["y"] else "rgb(123, 237, 159)"
    ]
    for meta_format in sorted(MetaFormat.to_list(), reverse=True):
        # exclude OP01 since we have no official matches yet
        if meta_format not in data_lines and meta_format != MetaFormat.OP01:
            data_lines.insert(0, {"x": meta_format, "y": None})

    DATA = [
      {
        "id": "Elo",
        "data": data_lines
      }
    ]

    radar_plot = nivo.Line(
        data=DATA,
        margin={"top": 10, "right": 20, "bottom": 10, "left": 10},
        enableGridX=False,
        enableGridY=False,
        yScale={
            "type": "linear",
            "min": "auto"
        },
        pointSize=10,
        pointBorderWidth=0,
        axisBottom=None,
        axisLeft=None,
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


    return mui.Box(radar_plot, sx={"height": 120, "width": 190})



def display_leaderboard_table(meta_format: MetaFormat, df_all_leader_elos: pd.DataFrame, df_meta_match_data, leader_id2leader_data: dict[str, Leader], match_count_min: int=None, match_count_max: int=None):
    def lid2name(leader_id: str) -> str:
        return leader_id2leader_data.get(leader_id).name

    def lid2meta(leader_id: str) -> MetaFormat | str:
        return leader_id2leader_data.get(leader_id).id.split("-")[0]

    def lid2match_count(leader_id: str) -> int:
        return len(df_meta_match_data.query(f"leader_id == '{leader_id}'"))

    # data preprocessing
    all_meta_formats = MetaFormat.to_list()
    relevant_meta_formats = all_meta_formats[:all_meta_formats.index(meta_format)+1]
    df_all_leader_elos = df_all_leader_elos.query("meta_format in @relevant_meta_formats")
    df_leader_elos = df_all_leader_elos.query(f"meta_format == '{meta_format}'").sort_values("elo", ascending=False).reset_index()
    display_columns = ["Name", "Release Set", "Match Count", "Elo"]
    #df_leader_elos["Meta"] = df_leader_elos["meta_format"].apply(lambda meta_format: meta_format)
    df_leader_elos["Release Set"] = df_leader_elos["leader_id"].apply(lambda lid: lid.split("-")[0])
    df_leader_elos["Name"] = df_leader_elos["leader_id"].apply(lambda lid: leader_id2leader_data[lid].name.replace('"', " ").replace('.', " "))
    df_leader_elos["Match Count"] = df_leader_elos["leader_id"].apply(lambda lid: lid2match_count(lid))
    df_leader_elos["Elo"] = df_leader_elos["elo"].apply(lambda elo: elo)
    if match_count_min:
        df_leader_elos = df_leader_elos.loc[df_leader_elos["Match Count"] > match_count_min]
    if match_count_max:
        df_leader_elos = df_leader_elos.loc[df_leader_elos["Match Count"] < match_count_max]

    with elements("dashboard"):
        # Layout for every element in the dashboard

        layout = [
            # Parameters: element_identifier, x_pos, y_pos, width, height, [item properties...]
            dashboard.Item("lboard_table_item", 0, 0, 6, 6, isResizable=False, isDraggable=False),
        ]

        with dashboard.Grid(layout):
            index_cells = [[create_image_cell(leader_id2aa_image_url(leader_id,leader_id2leader_data),
                                              text=f"#{i+1}",
                                              overlay_color=leader_id2leader_data[leader_id].to_hex_color(),
                                              horizontal=True,
                                              sx={"width": "200px"}) for
                            i, leader_id in df_leader_elos["leader_id"].items()]]
            # keep only relevant columns
            df_leader_elos_filtered = df_leader_elos.drop(
                columns=[c for c in df_leader_elos.columns if c not in display_columns])[display_columns]
            header_cells = [mui.TableCell(children="Leader", sx={"width": "200px"})] + [mui.TableCell(col) for col in
                                                                                        (display_columns + ["Elo Chart"])]

            df_leader_elos_display = df_leader_elos_filtered.copy()
            for col in display_columns:
                #df_leader_elos_display = df_leader_elos_display.map(lambda x: mui.TableCell(str(x)))
                if col == "Elo":
                    max_elo = df_leader_elos_display[col].max()
                    df_leader_elos_display[col] = df_leader_elos_display[col].apply(lambda elo: value2color_table_cell(elo, max=max_elo, color_switch_threshold=1000 if 1000 < max_elo else (max_elo*(7/8))))
                else:
                    df_leader_elos_display[col] = df_leader_elos_display[col].apply(lambda x: mui.TableCell(str(x)))
            df_leader_elos_display["Elo Chart"] = df_leader_elos["leader_id"].apply(
                lambda lid: leader_id2elo_chart(lid, df_all_leader_elos))

            display_table(df_leader_elos_display,
                          index_cells=index_cells,
                          header_cells=header_cells,
                          title=None,
                          key="lboard_table_item")


@st.experimental_dialog("Upload Match")
def upload_match_dialog(leader_id2leader_data):
    st.write(f"Upload your match")
    with st.form("upload_match_form"):
       st.write("Inside the form")
       meta_formats = display_meta_select(multiselect=False)
       leader_elo_data: list[LeaderElo] = get_leader_elo_data(meta_formats)
       available_leader_ids = list(set([lelo.leader_id for lelo in leader_elo_data]))
       # add name to ids
       available_leader_names: list[str] = list(dict.fromkeys(
           [
               f"{leader_id2leader_data[lid].name if lid in leader_id2leader_data else ''} ({lid})"
               for lid
               in available_leader_ids]))
       # display user input
       selected_leader_names: list[str] = display_leader_multiselect(available_leader_ids=available_leader_names)
       selected_leader_ids: list[str] = [ln.split("(")[1].strip(")") for ln in selected_leader_names]


       slider_val = st.slider("Form slider")
       checkbox_val = st.checkbox("Form checkbox")

       # Every form must have a submit button.
       submitted = st.form_submit_button("Submit")
       if submitted:
           st.write("slider", slider_val, "checkbox", checkbox_val)


def main():
    # display data
    st.header("One Piece TCG Elo Leaderboard")
    with st.sidebar:
        meta_formats: list[MetaFormat] = display_meta_select(multiselect=False)
        release_meta_formats: list[MetaFormat] | None = display_release_meta_select(multiselect=True)
        selected_leader_colors: list[OPTcgColor] | None = display_leader_color_multiselect()
        display_max_match_count=10000
        match_count_min, match_count_max = display_match_count_slider_slider(min=0, max=display_max_match_count)
        only_official: bool = display_only_official_toggle()

    # get data
    leader_elos: list[LeaderElo] = get_leader_elo_data()

    bq_leaders: list[Leader] = get_leader_data()
    leader_id2leader_data: dict[str, Leader] = {bq_leader_data.id: bq_leader_data for bq_leader_data in
                                                bq_leaders}

    # filter release_meta_formats
    if release_meta_formats:
        leader_elos: list[LeaderElo] = [lelo for lelo in leader_elos if leader_id2leader_data[lelo.leader_id].release_meta in release_meta_formats]
    if selected_leader_colors:
        leader_elos: list[LeaderElo] = [lelo for lelo in leader_elos if any(lcolor in selected_leader_colors for lcolor in leader_id2leader_data[lelo.leader_id].colors)]

    sorted_leader_elo_data: list[LeaderElo] = sorted(leader_elos, key=lambda x: x.elo,
                                                     reverse=True)

    selected_meta_leader_ids: list[str] = [lelo.leader_id for lelo in leader_elos]
    selected_meta_match_data: list[Match] = get_match_data(meta_formats=meta_formats,
                                                      leader_ids=selected_meta_leader_ids)
    df_meta_match_data = pd.DataFrame([match.dict() for match in selected_meta_match_data])
    if st.button("Upload Match"):
        upload_match_dialog(leader_id2leader_data)

    if sorted_leader_elo_data:
        # display table.
        df_leader_elos = BQLeaderElos(elo_ratings=sorted_leader_elo_data).to_dataframe()
        # only selected meta data
        df_leader_elos = df_leader_elos[df_leader_elos["only_official"] == only_official]
        display_leaderboard_table(meta_formats[0], df_leader_elos, df_meta_match_data, leader_id2leader_data, match_count_min=match_count_min, match_count_max=match_count_max if match_count_max != display_max_match_count else None)
    else:
        st.warning("Seems like the selected meta does not contain any matches")

if __name__ == "__main__":
    main()
