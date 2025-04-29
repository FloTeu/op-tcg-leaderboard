from fasthtml import ft
import numpy as np
import pandas as pd
from datetime import datetime, date
from uuid import uuid4

from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.leader import LeaderExtended, LeaderboardSortBy

# Common HTMX attributes for filter components
FILTER_HX_ATTRS = {
    "hx_get": "/api/leaderboard",
    "hx_trigger": "change", 
    "hx_target": "#leaderboard-table",
    "hx_include": "[name='meta_format'],[name='region'],[name='only_official'],[name='sort_by'],[name='release_meta_formats']",
    "hx_indicator": "#loading-indicator"
}

# Common CSS classes for select components
SELECT_CLS = "w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"

def create_filter_components():
    # Meta format select
    meta_formats = MetaFormat.to_list()
    meta_format_select = ft.Select(
        label="Meta Format",
        id="meta-format-select", 
        name="meta_format",
        cls=SELECT_CLS + " styled-select",
        *[ft.Option(mf, value=mf, selected=mf == meta_formats[-1]) for mf in meta_formats],
        **FILTER_HX_ATTRS,
    )
    
    # Release meta formats multi-select
    release_meta_formats_select = ft.Select(
        label="Release Meta Formats",
        id="release-meta-formats-select",
        name="release_meta_formats",
        multiple=True,
        size=1,
        cls=SELECT_CLS + " relative",
        *[ft.Option(mf, value=mf) for mf in meta_formats],
        **FILTER_HX_ATTRS,
    )
    
    # Region select
    regions = MetaFormatRegion.to_list()
    region_select = ft.Select(
        label="Region",
        value=MetaFormatRegion.ALL,
        id="region-select",
        name="region",
        cls=SELECT_CLS + " styled-select",
        *[ft.Option(r, value=r) for r in regions],
        **FILTER_HX_ATTRS,
    )
    
    # Only official toggle
    official_toggle = ft.Div(
        ft.Label("Only Official Matches", cls="text-white font-medium"),
        ft.Input(
            type="checkbox",
            checked=True,
            id="official-toggle",
            name="only_official",
            **FILTER_HX_ATTRS
        ),
        cls="flex items-center space-x-2"
    )
    
    # Sort by select
    sort_by_options = [
        LeaderboardSortBy.WIN_RATE,
        LeaderboardSortBy.TOURNAMENT_WINS,
        LeaderboardSortBy.DOMINANCE_SCORE,
        "Match Count",
        "Elo"
    ]
    sort_by_select = ft.Select(
        label="Sort By",
        id="sort-by-select",
        name="sort_by",
        cls=SELECT_CLS + " styled-select",
        *[ft.Option(opt, value=opt) for opt in sort_by_options],
        **FILTER_HX_ATTRS,
    )
    
    return ft.Div(
        meta_format_select,
        release_meta_formats_select,
        region_select,
        official_toggle,
        sort_by_select,
        cls="space-y-4"
    )

def create_leaderboard_table(df_leader_extended, meta_format, display_name2df_col_name, only_official=True):
    # Add new cols
    df_leader_extended['win_rate_decimal'] = df_leader_extended['win_rate'].apply(lambda x: f"{x * 100:.2f}%")
    
    # data preprocessing
    all_meta_formats = MetaFormat.to_list()
    relevant_meta_formats = all_meta_formats[:all_meta_formats.index(meta_format) + 1]
    visible_meta_formats = relevant_meta_formats[max(0, len(relevant_meta_formats) - 5):]
    df_leader_extended = df_leader_extended.query("meta_format in @relevant_meta_formats")
    df_leader_extended_selected_meta = df_leader_extended.query(f"meta_format == '{meta_format}'").copy()
    
    if len(df_leader_extended_selected_meta) == 0:
        return ft.Div("No leader data available for the selected meta", cls="text-red-400")
    
    display_columns = ["name", "Set", "tournament_wins", "total_matches",
                      "win_rate_decimal", "d_score", "elo"]
    
    # Prepare the data
    df_leader_extended_selected_meta["Set"] = df_leader_extended_selected_meta["id"].apply(
        lambda lid: lid.split("-")[0])
    df_leader_extended_selected_meta['d_score'] = df_leader_extended_selected_meta['d_score'].apply(
        lambda x: f"{int(x * 100)}%")
    
    # Create table header
    header = ft.Thead(
        ft.Tr(
            ft.Th("Rank", cls="px-4 py-2 bg-gray-800 text-white font-semibold"),
            ft.Th("Leader", cls="px-4 py-2 bg-gray-800 text-white font-semibold"),
            *[ft.Th(col.replace("_", " ").title(), cls="px-4 py-2 bg-gray-800 text-white font-semibold") for col in display_columns],
            cls=""
        )
    )
    
    # Create table body
    rows = []
    for idx, row in df_leader_extended_selected_meta.iterrows():
        cells = [
            ft.Td(f"#{idx + 1}", cls="px-4 py-2 text-gray-200"),
            ft.Td(
                ft.A(
                    row["name"].replace('"', " ").replace('.', " "),
                    href=f"/leader/{row['id']}",
                    cls="text-blue-400 hover:text-blue-300"
                ),
                cls="px-4 py-2"
            )
        ]
        
        for col in display_columns:
            if col == "elo":
                max_elo = df_leader_extended_selected_meta["elo"].max()
                elo_value = row["elo"]
                color_class = "text-green-400" if elo_value > (max_elo * 0.7) else "text-yellow-400" if elo_value > (max_elo * 0.4) else "text-red-400"
                cells.append(ft.Td(str(elo_value), cls=f"px-4 py-2 {color_class}"))
            else:
                cells.append(ft.Td(str(row[col]), cls="px-4 py-2 text-gray-200"))
        
        rows.append(ft.Tr(*cells, cls="border-b border-gray-700 hover:bg-gray-800/50"))
    
    body = ft.Tbody(*rows)
    
    return ft.Div(
        ft.Table(
            header,
            body,
            cls="w-full border-collapse bg-gray-900"
        ),
        cls="overflow-x-auto rounded-lg border border-gray-700 shadow-gray-800/50"
    )

def home_page():
    return ft.Div(
        ft.H1("Leaderboard", cls="text-3xl font-bold text-white mb-6"),
        ft.Div(
            ft.Div(
                # Loading indicator
                ft.Div(
                    ft.Div(
                        cls="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-white mx-auto"
                    ),
                    cls="text-white text-center py-8 htmx-indicator",
                    id="loading-indicator"
                ),
                # Content
                ft.Div(
                    cls="text-white text-center py-8",
                    hx_get="/api/leaderboard",
                    hx_trigger="load",
                    hx_include="[name='meta_format'],[name='region'],[name='only_official'],[name='sort_by']",
                    hx_target="#leaderboard-table",
                    hx_indicator="#loading-indicator",
                    id="leaderboard-table"
                ),
                cls="relative"
            ),
            cls="space-y-4"
        ),
        cls="min-h-screen"
    ) 