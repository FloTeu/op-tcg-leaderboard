from fasthtml import ft
from shad4fast import *
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
    meta_format_select = Select(
        label="Meta Format",
        items=meta_formats,
        default_value=meta_formats[0],
        id="meta-format-select",
        cls="w-full bg-white dark:bg-gray-800 text-gray-900 dark:text-white",
        on_change="updateLeaderboard()"
    )
    
    # Region select
    regions = MetaFormatRegion.to_list()
    region_select = Select(
        label="Region",
        items=regions,
        default_value=regions[0],
        id="region-select",
        cls="w-full bg-white dark:bg-gray-800 text-gray-900 dark:text-white",
        on_change="updateLeaderboard()"
    )
    
    # Only official toggle
    official_toggle = Switch(
        label="Only Official Matches",
        default_checked=True,
        id="official-toggle",
        cls="w-full",
        on_change="updateLeaderboard()"
    )
    
    # Sort by select
    sort_options = [
        LeaderboardSortBy.WIN_RATE,
        LeaderboardSortBy.TOURNAMENT_WINS,
        LeaderboardSortBy.ELO,
        LeaderboardSortBy.DOMINANCE_SCORE
    ]
    sort_select = Select(
        label="Sort By",
        items=sort_options,
        default_value=LeaderboardSortBy.WIN_RATE,
        id="sort-select",
        cls="w-full bg-white dark:bg-gray-800 text-gray-900 dark:text-white",
        on_change="updateLeaderboard()"
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
        return ft.Div("No leader data available for the selected meta", cls="text-red-500")
    
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
            ft.Th("Rank", cls="px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white"),
            ft.Th("Leader", cls="px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white"),
            *[ft.Th(col.replace("_", " ").title(), cls="px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white") for col in display_columns],
            cls=""
        )
    )
    
    # Create table body
    rows = []
    for idx, row in df_leader_extended_selected_meta.iterrows():
        cells = [
            ft.Td(f"#{idx + 1}", cls="px-4 py-2 text-gray-900 dark:text-white"),
            ft.Td(
                ft.A(
                    row["name"].replace('"', " ").replace('.', " "),
                    href=f"/leader/{row['id']}",
                    cls="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
                ),
                cls="px-4 py-2"
            )
        ]
        
        for col in display_columns:
            if col == "elo":
                max_elo = df_leader_extended_selected_meta["elo"].max()
                elo_value = row["elo"]
                color_class = "text-green-600 dark:text-green-400" if elo_value > (max_elo * 0.7) else "text-yellow-600 dark:text-yellow-400" if elo_value > (max_elo * 0.4) else "text-red-600 dark:text-red-400"
                cells.append(ft.Td(str(elo_value), cls=f"px-4 py-2 {color_class}"))
            else:
                cells.append(ft.Td(str(row[col]), cls="px-4 py-2 text-gray-900 dark:text-white"))
        
        rows.append(ft.Tr(*cells, cls="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"))
    
    body = ft.Tbody(*rows)
    
    return ft.Div(
        ft.Table(
            header,
            body,
            cls="w-full border-collapse bg-white dark:bg-gray-900"
        ),
        cls="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700"
    )

def home_page():
    # Add JavaScript for handling filter updates
    js_code = """
    async function updateLeaderboard() {
        const metaFormat = document.getElementById('meta-format-select').value;
        const region = document.getElementById('region-select').value;
        const onlyOfficial = document.getElementById('official-toggle').checked;
        const sortBy = document.getElementById('sort-select').value;
        
        try {
            const response = await fetch(`/api/leaderboard?meta_format=${metaFormat}&region=${region}&only_official=${onlyOfficial}&sort_by=${sortBy}`);
            const data = await response.json();
            
            // Update the table with new data
            const tableContainer = document.getElementById('leaderboard-table');
            tableContainer.innerHTML = data.html;
        } catch (error) {
            console.error('Error updating leaderboard:', error);
        }
    }
    
    // Initial load
    document.addEventListener('DOMContentLoaded', updateLeaderboard);
    """
    
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
        ft.Script(js_code),
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
        cls="p-8"
    ) 