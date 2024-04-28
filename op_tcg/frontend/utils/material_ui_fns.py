from streamlit_elements import mui, html, core

def display_table(df_data,
                  df_tooltip=None,
                  index_cells: list[core.element.Element]=None,
                  header_cells: list[core.element.Element]=None,
                  key="mui-table"):
    """
    df_data: DataFrame containing all data which should be display. Index and headers are also displayed by default
    df_tooltip: Dataframe containing optional tooltip information
    """
    if df_tooltip is not None:
        assert df_tooltip.shape == df_data.shape
    if index_cells:
        assert df_data.shape[0] == len(index_cells)
    else:
        index_cells = [mui.TableCell(children=i) for i in df_data.index]
    if header_cells:
        assert df_data.shape[1] + 1 == len(header_cells)
    else:
        header_cells = [mui.TableCell(children="")] + [mui.TableCell(children=col) for col in df_data.columns.values]
    with mui.TableContainer(key=key):
        with mui.Table():
            # header row
            mui.TableHead()(mui.TableRow()(header_cells))

            # body rows
            with mui.TableBody():
                for i, (index_name, df_row) in enumerate(df_data.iterrows()):
                    # Create a list of cells starting with the existing index cell
                    row_cells = [index_cells[i]]

                    # Append new cells to the row_cells list
                    for j, df_cell in df_row.items():
                        if df_tooltip is not None:
                            cell_input = mui.Tooltip(title=str(df_tooltip.iloc[i][j]))(
                                html.Span()(mui.Typography(df_cell))
                            )
                        else:
                            cell_input = mui.Typography(df_cell)
                        cell = mui.TableCell()(cell_input)
                        row_cells.append(cell)

                    # Create the table row with all the cells
                    mui.TableRow()(row_cells)


def create_image_cell(image_url, text):
    # Function to create an image cell in a table

    return mui.TableCell(children=[
        mui.Box(
            sx={'display': 'flex', 'alignItems': 'center'},
            children=[
                mui.Avatar(src=image_url, alt=text, sx={'width': 24, 'height': 24, 'marginRight': 1}),
                text
            ]
        )
    ])