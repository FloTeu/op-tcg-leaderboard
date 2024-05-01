import pandas as pd
from streamlit_elements import mui, html, core

def display_table(df_data,
                  df_tooltip=None,
                  index_cells: list[list[core.element.Element]]=None,
                  header_cells: list[core.element.Element]=None,
                  title=None,
                  key="mui-table"):
    """
    df_data: DataFrame containing all data which should be display. Index and headers are also displayed by default
    df_tooltip: Dataframe containing optional tooltip information
    """
    if df_tooltip is not None:
        assert df_tooltip.shape == df_data.shape
    if index_cells:
        for index_cell_col in index_cells:
            assert df_data.shape[0] == len(index_cell_col)
    else:
        index_cells = [[mui.TableCell(children=i) for i in df_data.index]]
    if header_cells:
        assert df_data.shape[1] + len(index_cells) == len(header_cells)
    else:
        header_cells = [mui.TableCell(children="") for _ in range(len(index_cells))] + [mui.TableCell(children=col) for col in df_data.columns.values]
    with mui.TableContainer(key=key):
        if title:
            mui.Box()(html.H1(title))
        with mui.Table():
            # header row
            mui.TableHead()(mui.TableRow()(header_cells))

            # body rows
            with mui.TableBody():
                for i, (index_name, df_row) in enumerate(df_data.iterrows()):
                    # Create a list of cells starting with the existing index cell
                    row_cells = []
                    for j, index_cells_column in enumerate(index_cells):
                        if j > 0:
                            cell = win_rate2color_table_cell(index_cells_column[i])
                        else:
                            cell = index_cells_column[i]
                        row_cells.append(cell)

                    # Append new cells to the row_cells list
                    for j, df_cell in df_row.items():
                        tooltip = df_tooltip.iloc[i][j] if df_tooltip is not None else None
                        cell = win_rate2color_table_cell(df_cell, tooltip=tooltip)
                        row_cells.append(cell)

                    # Create the table row with all the cells
                    mui.TableRow()(row_cells)


def win_rate2color_table_cell(win_rate, tooltip=None):
    cell_text = f"{win_rate}%" if not pd.isna(win_rate) else win_rate
    cell_text_styles = {
        'fontSize': '1.35rem',  # Adjust font size as needed
        'color': 'black',  # Text color set to white
        'fontWeight': 'bold',  # Optional: make the text bold
    }
    if tooltip is not None:
        cell_input = mui.Tooltip(title=str(tooltip))(
            html.Span()(mui.Typography(sx=cell_text_styles)(cell_text))
        )
    else:
        cell_input = mui.Typography(cell_text)
    background_color = "rgb(164, 176, 190)"
    if win_rate < 50:
        background_color = f"rgba(255, 107, 129, {1 - (win_rate / 50 / 2)})"
    if win_rate > 50:
        background_color = f"rgba(123, 237, 159, {0.5 + (win_rate / 50 - 1) / 2})"
    cell = mui.TableCell(sx={"background": background_color,
                             "text-align": "center"
                             })(cell_input)
    return cell


# def create_image_cell(image_url, text):
#     # Function to create an image cell in a table
#
#     return mui.TableCell(children=[
#         mui.Box(
#             sx={'display': 'flex', 'alignItems': 'center'},
#             children=[
#                 mui.Avatar(src=image_url, alt=text, sx={'width': 24, 'height': 24, 'marginRight': 1}),
#                 text
#             ]
#         )
#     ])



def create_image_cell(image_url, text, overlay_color='#000000', horizontal=True):
    # Function to create an image cell in a table with a background image and formatted text

    return mui.TableCell(
        sx={
            'backgroundImage': f'linear-gradient(to top, {overlay_color}, transparent), url("{image_url}")',
            #'backgroundImage': f'url("{image_url}")',
            'backgroundSize': 'cover, 125%',  # Apply cover for gradient and zoom for image
            #'backgroundSize': '110%',  # Zoom in by 25%
            'backgroundPosition': 'bottom, center -50px' if horizontal else 'bottom, center 0px', # Gradient from bottom, image from 50px from top
            #'backgroundPosition': 'center -40px',  # Start from 50px from the top
            'backgroundRepeat': 'no-repeat',
            'position': 'relative',  # Needed to position children absolutely
            'height': '80px',  # Adjust height as needed
        },
        children=[
            mui.Box(
                sx={
                    'position': 'absolute',
                    'bottom': 0,
                    'right': 0,
                    'padding': '8px',
                },
                children=[
                    mui.Typography(
                        text_line,
                        sx={
                            'fontSize': '1.15rem',  # Adjust font size as needed
                            'color': 'white',  # Text color set to white
                            'fontWeight': 'bold',  # Optional: make the text bold
                            '-webkit-text-stroke': '1px black',  # Black border line around the text
                            'textShadow': '2px 2px 4px black',  # Optional: text shadow for better readability
                        }
                    ) for text_line in text.split("\n")
                ]
            )
        ]
    )

