import pandas as pd
from typing import Any

from streamlit_elements import mui, html

from op_tcg.frontend.utils.styles import GREEN_RGB, RED_RGB


def display_table(table_cells,
                  index_cells: list[list[Any]]=None,
                  header_cells: list[Any]=None,
                  title=None,
                  key="mui-table"):
    """
    df_data: DataFrame containing all data which should be display. Index and headers are also displayed by default
    df_tooltip: Dataframe containing optional tooltip information
    """
    if index_cells:
        for index_cell_col in index_cells:
            assert table_cells.shape[0] == len(index_cell_col)
    count_index_sells = len(index_cells) if index_cells is not None else 0
    if header_cells:
        assert table_cells.shape[1] + count_index_sells == len(header_cells)
    else:
        header_cells = [mui.TableCell(children="") for _ in range(count_index_sells)] + [mui.TableCell(children=col) for col in table_cells.columns.values]
    with mui.TableContainer(key=key):
        if title:
            mui.Box(html.H2(title), sx={"font-family": '"Source Sans Pro", sans-serif;'})
        with mui.Table():
            # header row
            mui.TableHead(mui.TableRow(header_cells))

            # body rows
            with mui.TableBody():
                for i, (index_name, df_row) in enumerate(table_cells.iterrows()):
                    # Create a list of cells starting with the existing index cell
                    row_cells = []
                    if index_cells:
                        for j, index_cells_column in enumerate(index_cells):
                            row_cells.append(index_cells_column[i])

                    # Append new cells to the row_cells list
                    for j, df_cell in df_row.items():
                        row_cells.append(df_cell)

                    # Create the table row with all the cells
                    mui.TableRow(row_cells)

def add_tooltip(win_rate, tooltip=None):
    cell_text = f"{win_rate}%" if not pd.isna(win_rate) else win_rate
    cell_text_styles = {
        'fontSize': '1.35rem',  # Adjust font size as needed
        'color': 'black',  # Text color set to white
        'fontWeight': 'bold',  # Optional: make the text bold
    }
    if tooltip is not None:
        cell_input = mui.Tooltip(title=str(tooltip))(
            html.Span(mui.Typography(cell_text, sx=cell_text_styles))
        )
    else:
        cell_input = mui.Typography(cell_text, sx=cell_text_styles)
    return cell_input

def value2color_table_cell(value: float | int, max: float | int, color_switch_threshold: float | int = None, cell_input=None):
    cell_input = cell_input or value
    background_color = "rgb(164, 176, 190)"
    half_max = (max/2)
    color_switch_threshold = color_switch_threshold or half_max
    if value < color_switch_threshold:
        # expected to be between 0 (0.5 in best case) and 1
        transparency = 1 - (value / half_max / 2)
        background_color = f"rgba({RED_RGB[0]},{RED_RGB[1]},{RED_RGB[2]}, {transparency})"
    if value > color_switch_threshold:
        # expected to be between 0 (0.5 in best case) and 1
        transparency = 0.5 + (value / half_max - 1) / 2
        background_color = f"rgba({GREEN_RGB[0]},{GREEN_RGB[1]},{GREEN_RGB[2]}, {transparency})"
    cell = mui.TableCell(cell_input, sx={"background": background_color,
                             "text-align": "center",
                            'fontSize': '1.35rem',  # Adjust font size as needed
                            'color': 'black',  # Text color set to white
                            'fontWeight': 'bold',  # Optional: make the text bold
                            'border': '0px',
                             })
    return cell


def create_image_cell(image_url, text: str | None=None, overlay_color='#000000', sx: dict=None, horizontal=True):
    # Function to create an image cell in a table with a background image and formatted text
    width = "200px" if horizontal else "auto"
    sx = sx or {}
    text_blocks=[]
    if text:
        text_blocks = [mui.Typography(
                            text_line,
                            sx={
                                'fontSize': '1.15rem',  # Adjust font size as needed
                                'color': 'white',  # Text color set to white
                                'fontWeight': 'bold',  # Optional: make the text bold
                                '-webkit-text-stroke': '0.1px beige',  # Black border line around the text
                                'textShadow': '1px 2px 4px black',  # Optional: text shadow for better readability
                            }
                        ) for text_line in text.split("\n")]

    return mui.TableCell(mui.Box(mui.Box(
        sx={
            'backgroundImage': f'linear-gradient(to top, {overlay_color}, transparent), url("{image_url}")',
            #'backgroundImage': f'url("{image_url}")',
            'backgroundSize': 'cover, 125%',  # Apply cover for gradient and zoom for image
            #'backgroundSize': '110%',  # Zoom in by 25%
            'backgroundPosition': 'bottom, center -50px' if horizontal else 'bottom, center 0px', # Gradient from bottom, image from 50px from top
            #'backgroundPosition': 'center -40px',  # Start from 50px from the top
            'backgroundRepeat': 'no-repeat',
            'position': 'relative',  # Needed to position children absolutely
            'height': '120px',  # Adjust height as needed
            'width': width,
            **sx
        },
        children=[
            mui.Box(
                sx={
                    'position': 'absolute',
                    'bottom': 0,
                    'right': 0,
                    'padding': '8px',
                },
                children=text_blocks
            )
        ]), sx={'position': 'relative', 'width': "100%"})
        , sx={"padding": "0px",
              'width': width
              }
    )

