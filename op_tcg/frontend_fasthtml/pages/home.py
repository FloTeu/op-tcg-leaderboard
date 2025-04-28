from fasthtml import ft
import numpy as np
import pandas as pd
from datetime import datetime, date
from uuid import uuid4

from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.leader import LeaderExtended, LeaderboardSortBy
from op_tcg.backend.models.cards import OPTcgColor
from op_tcg.backend.models.matches import Match, MatchResult
from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.frontend.utils.leader_data import get_lid2ldata_dict_cached, lids_to_name_and_lids, lname_and_lid_to_lid, calculate_dominance_score

def create_filter_components():
    # Meta format select
    meta_formats = MetaFormat.to_list()
    meta_format_select = ft.Select(
        label="Meta Format",
        value=meta_formats[0],
        id="meta-format-select",
        name="meta_format",
        cls="w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
        hx_get="/api/leaderboard",
        hx_trigger="change",
        hx_target="#leaderboard-table",
        hx_include="[name='meta_format'],[name='region'],[name='only_official'],[name='sort_by']",
        *[ft.Option(mf, value=mf) for mf in meta_formats]
    )
    
    # Region select
    regions = MetaFormatRegion.to_list()
    region_select = ft.Select(
        label="Region",
        value=regions[0],
        id="region-select",
        name="region",
        cls="w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
        hx_get="/api/leaderboard",
        hx_trigger="change",
        hx_target="#leaderboard-table",
        hx_include="[name='meta_format'],[name='region'],[name='only_official'],[name='sort_by']",
        *[ft.Option(r, value=r) for r in regions]
    )
    
    # Only official toggle
    official_toggle = ft.Div(
        ft.Label("Only Official Matches", cls="text-white font-medium"),
        ft.Input(
            type="checkbox",
            checked=True,
            id="official-toggle",
            name="only_official",
            cls="ml-2 w-5 h-5 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500",
            hx_get="/api/leaderboard",
            hx_trigger="change",
            hx_target="#leaderboard-table",
            hx_include="[name='meta_format'],[name='region'],[name='only_official'],[name='sort_by']",
        ),
        cls="flex items-center p-3 bg-gray-800 rounded-lg"
    )
    
    # Sort by select
    sort_options = [
        LeaderboardSortBy.WIN_RATE,
        LeaderboardSortBy.TOURNAMENT_WINS,
        LeaderboardSortBy.ELO,
        LeaderboardSortBy.DOMINANCE_SCORE
    ]
    sort_select = ft.Select(
        label="Sort By",
        value=LeaderboardSortBy.WIN_RATE,
        id="sort-select",
        name="sort_by",
        cls="w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
        hx_get="/api/leaderboard",
        hx_trigger="change",
        hx_target="#leaderboard-table",
        hx_include="[name='meta_format'],[name='region'],[name='only_official'],[name='sort_by']",
        *[ft.Option(so, value=so) for so in sort_options]
    )
    
    return ft.Div(
        ft.Div(
            meta_format_select,
            region_select,
            official_toggle,
            sort_select,
            cls="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
        ),
        cls="mb-6"
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
    # TODO: Load actual data
    # For now, we'll use placeholder data
    df_leader_extended = pd.DataFrame({
        "id": ["OP01-001", "OP01-002"],
        "name": ["Monkey D. Luffy", "Roronoa Zoro"],
        "meta_format": [MetaFormat.OP01, MetaFormat.OP01],
        "win_rate": [0.65, 0.60],
        "total_matches": [100, 90],
        "elo": [1500, 1450],
        "tournament_wins": [5, 3],
        "d_score": [0.75, 0.70]
    })
    
    display_name2df_col_name = {
        "Name": "name",
        "Set": "id",
        LeaderboardSortBy.TOURNAMENT_WINS: "tournament_wins",
        "Match Count": "total_matches",
        LeaderboardSortBy.WIN_RATE: "win_rate",
        LeaderboardSortBy.DOMINANCE_SCORE: "d_score",
        "Elo": "elo"
    }
    
    return ft.Div(
        ft.H1("Leaderboard", cls="text-3xl font-bold text-white mb-6"),
        ft.Div(
            create_filter_components(),
            ft.Div(
                create_leaderboard_table(
                    df_leader_extended,
                    MetaFormat.OP01,
                    display_name2df_col_name,
                    only_official=True
                ),
                id="leaderboard-table"
            ),
            cls="space-y-4"
        ),
        cls="bg-gray-900 min-h-screen"
    ) 