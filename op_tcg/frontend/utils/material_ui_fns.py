import pandas as pd
from typing import Any, Callable

from streamlit_elements import mui, html

from op_tcg.frontend.utils.styles import GREEN_RGB, RED_RGB, css_rule_to_dict, read_style_sheet


def display_table(table_cells,
                  index_cells: list[list[Any]] = None,
                  header_cells: list[Any] = None,
                  title=None,
                  sx=None,
                  key="mui-table"):
    """
    table_cells: DataFrame containing all table cells which should be displayed. Index and headers are also displayed by default
    """
    sx = sx or {}
    if index_cells:
        for index_cell_col in index_cells:
            assert table_cells.shape[0] == len(index_cell_col)
    count_index_sells = len(index_cells) if index_cells is not None else 0
    if header_cells:
        assert table_cells.shape[1] + count_index_sells == len(header_cells)
    else:
        header_cells = [mui.TableCell(children="") for _ in range(count_index_sells)] + [mui.TableCell(children=col) for
                                                                                         col in
                                                                                         table_cells.columns.values]
    with mui.TableContainer(key=key):
        if title:
            mui.Box(html.H2(title), sx={"font-family": '"Source Sans Pro", sans-serif;'})
        with mui.Table(sx=sx):
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


def calculate_transparency(value, min_value, max_value):
    """
    Calculate transparency between 0.5 and 1 based on a given range.
    If the value is the half of (max_value + min_value) it should be 0.5
    If the value is above half of (max_value + min_value) it should be >0.5 <=1
    If the value is below half of (max_value + min_value) it should be >0.5 <=1
    If the value is max_value it should be 1
    If the value is min_value it should be 1

    Examples:
        print(calculate_transparency(-1, -1, 1))  # Output: 1
        print(calculate_transparency(0, -1, 1))  # Output: 0.5
        print(calculate_transparency(1, -1, 1))  # Output: 1
        print(calculate_transparency(0.9999, -1, 1))  # Output: ~1
        print(calculate_transparency(0.5, -1, 1))  # Output: 0.75
        print(calculate_transparency(-0.5, -1, 1))  # Output: 0.75

        print(calculate_transparency(0, 0, 1))  # Output: 1
        print(calculate_transparency(0.25, 0, 1))  # Output: 0.75
        print(calculate_transparency(0.5, 0, 1))  # Output: 0.5
        print(calculate_transparency(0.75, 0, 1))  # Output: 0.75
        print(calculate_transparency(1, 0, 1))  # Output: 1

    Parameters:
    - value: The current value for which transparency is calculated.
    - min_value: The minimum value of the range.
    - max_value: The maximum value of the range.

    Returns:
    - Transparency value between 0.5 and 1.
    """
    midpoint = (max_value + min_value) / 2.0
    if value == midpoint:
        return 0.5
    elif value == min_value or value == max_value:
        return 1
    else:
        # Calculate the transparency on a scale from 0.5 to 1.0
        if value > midpoint:
            # Scale between midpoint and max_value
            return 0.5 + (value - midpoint) / (max_value - midpoint) * 0.5
        else:
            # Scale between min_value and midpoint
            return 0.5 + (midpoint - value) / (midpoint - min_value) * 0.5


def value2color_table_cell(value: str | float | int, max_value: float | int, min_value: float | int = 0,
                           color_switch_threshold: float | int = None, cell_input=None, styles: dict | None = None):
    styles = styles or {}
    cell_input = cell_input or value
    background_color = "rgb(164, 176, 190)"
    half_max = ((max_value + min_value) / 2)
    color_switch_threshold = color_switch_threshold or half_max
    transparency = calculate_transparency(value, min_value, max_value)
    color_rgb = RED_RGB if value < color_switch_threshold else GREEN_RGB
    background_color = f"rgba({color_rgb[0]},{color_rgb[1]},{color_rgb[2]}, {transparency})"

    # if value < color_switch_threshold:
    #     # expected to be between 0 (0.5 in best case) and 1
    #     transparency = 1 - (value / half_max / (max / half_max))
    #     background_color = f"rgba({RED_RGB[0]},{RED_RGB[1]},{RED_RGB[2]}, {transparency})"
    # if value > color_switch_threshold:
    #     # expected to be between 0 (0.5 in best case) and 1
    #     transparency = 0.5 + (value / half_max - 1) / (max_value / half_max)
    #     background_color = f"rgba({GREEN_RGB[0]},{GREEN_RGB[1]},{GREEN_RGB[2]}, {transparency})"

    cell = mui.TableCell(cell_input, sx={"background": background_color,
                                         **styles
                                         })
    return cell


def create_image_cell(image_url, text: str | None = None, overlay_color='#000000', sx: dict = None,
                      sx_table_cell: dict = None, sx_text: dict = None, horizontal=True, on_click: Callable | None = None):
    # Function to create an image cell in a table with a background image and formatted text
    width = "200px" if horizontal else "auto"
    sx = sx or {}
    sx_text = sx_text or {}
    sx_table_cell = sx_table_cell or {}
    text_blocks = []
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
    text_style = {
        'position': 'absolute',
        'bottom': 0,
        'right': 0,
        'padding': '8px',
        **sx_text
    }
    text_element = mui.Link(text_blocks, sx=text_style, onClick=on_click) if on_click else mui.Box(text_blocks,
                                                                                                   sx=text_style)
    return mui.TableCell(mui.Box(mui.Box(
        sx={
            'backgroundImage': f'linear-gradient(to top, {overlay_color}, transparent), url("{image_url}")',
            # 'backgroundImage': f'url("{image_url}")',
            'backgroundSize': 'cover, 125%',  # Apply cover for gradient and zoom for image
            # 'backgroundSize': '110%',  # Zoom in by 25%
            'backgroundPosition': 'bottom, center -50px' if horizontal else 'bottom, center 0px',
            # Gradient from bottom, image from 50px from top
            # 'backgroundPosition': 'center -40px',  # Start from 50px from the top
            'backgroundRepeat': 'no-repeat',
            'position': 'relative',  # Needed to position children absolutely
            'height': '120px',  # Adjust height as needed
            'width': width,
            **sx
        },
        children=[
            text_element
        ]), sx={'position': 'relative', 'width': "100%"})
        , sx={"padding": "0px",
              'width': width,
              **sx_table_cell
              },
        onClick=on_click
    )
