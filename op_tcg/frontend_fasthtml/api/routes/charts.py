import json
import html
from fasthtml import ft
from starlette.requests import Request
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.cards import OPTcgCardCatagory
from op_tcg.frontend_fasthtml.utils.colors import ChartColors
from op_tcg.frontend_fasthtml.utils.extract import (
    get_leader_extended, 
    get_card_id_card_data_lookup,
    get_tournament_decklist_data
)
from op_tcg.frontend_fasthtml.utils.charts import create_line_chart, create_leader_win_rate_radar_chart, create_card_occurrence_streaming_chart
from op_tcg.frontend_fasthtml.utils.win_rate import get_radar_chart_data
from op_tcg.frontend_fasthtml.utils.api import get_filtered_leaders
from op_tcg.frontend_fasthtml.utils.leader_data import lid_to_name_and_lid



def setup_api_routes(rt):

    @rt("/api/leader-chart/{leader_id}", methods=["GET", "POST"])
    async def leader_line_chart(request: Request, leader_id: str):
        # Check if this is a POST request with chart data
        if request.method == "POST":
            try:
                # Try to get chart data from the request body
                body = await request.body()
                if body:
                    form_data = await request.form()
                    chart_data_str = form_data.get("chart_data")
                    if chart_data_str:
                        # Unescape HTML entities and parse the provided chart data
                        chart_data_unescaped = html.unescape(chart_data_str)
                        chart_data = json.loads(chart_data_unescaped)
                        
                        # Determine chart color based on win rate trend
                        win_rate_values = [d["winRate"] for d in chart_data if d["winRate"] is not None]
                        color = ChartColors.POSITIVE if len(win_rate_values) < 2 or (len(win_rate_values) >= 2 and win_rate_values[-1] > win_rate_values[-2]) else ChartColors.NEGATIVE
                        
                        # Create and return the chart using provided data
                        return create_line_chart(
                            container_id=f"win-rate-chart-{leader_id}",
                            data=chart_data,
                            color=color,
                            show_x_axis=False,
                            show_y_axis=False
                        )
            except (json.JSONDecodeError, KeyError, TypeError):
                # If parsing fails, fall through to the original logic
                pass
        
        # Original logic - fetch data from database
        # Get query parameters
        all_meta_formats = MetaFormat.to_list()
        meta_format_list = request.query_params.getlist("meta_format")
        meta_format = MetaFormat(meta_format_list[0] if meta_format_list else MetaFormat.latest_meta_format())
        meta_format_index = all_meta_formats.index(meta_format)
        
        # Get the last_n parameter (default to 5)
        try:
            last_n = int(request.query_params.get("last_n", "5"))
        except ValueError:
            last_n = 5
        
        # Get color parameter (default to neutral for leader page)
        color_param = request.query_params.get("color", None)
        
        # Get leader data for all meta formats
        filtered_leaders = get_filtered_leaders(request)
        
        # Sort by meta format to ensure chronological order
        filtered_leaders.sort(key=lambda x: all_meta_formats.index(x.meta_format))

        first_meta_format = filtered_leaders[0].meta_format if filtered_leaders else None
        
        leader_history = [l for l in filtered_leaders if l.id == leader_id]
        start_index = all_meta_formats.index(first_meta_format) if first_meta_format in all_meta_formats else 0
        meta_formats_between = all_meta_formats[start_index:]
        
        # Create a lookup for existing data points
        meta_to_leader = {l.meta_format: l for l in leader_history}
        
        # Determine range of meta formats to include based on last_n
        end_index = meta_format_index + 1 - start_index  # Exclusive end index
        start_index = max(0, end_index - last_n)  # Take at most last_n meta formats
        relevant_meta_formats = meta_formats_between[start_index:end_index]
        
        # Prepare data for the chart, including null values for missing meta formats
        chart_data = []
        for meta_format in relevant_meta_formats:
            if meta_format in meta_to_leader:
                leader = meta_to_leader[meta_format]
                chart_data.append({
                    "meta": str(meta_format),
                    "winRate": round(leader.win_rate * 100, 2) if leader.win_rate is not None else None,
                    "elo": leader.elo,
                    "matches": leader.total_matches
                })
            else:
                chart_data.append({
                    "meta": str(meta_format),
                    "winRate": None,
                    "elo": None,
                    "matches": None
                })
        
        # Determine chart color based on parameter or trend
        if color_param == "neutral":
            color = ChartColors.NEUTRAL
        else:
            # Default behavior: determine color based on win rate trend
            win_rate_values = [d["winRate"] for d in chart_data if d["winRate"] is not None]
            color = ChartColors.POSITIVE if len(win_rate_values) < 2 or (len(win_rate_values) >= 2 and win_rate_values[-1] > win_rate_values[-2]) else ChartColors.NEGATIVE

        # Create and return the chart
        return create_line_chart(
            container_id=f"win-rate-chart-{leader_id}",
            data=chart_data,
            color=color,
            show_x_axis=True,
            show_y_axis=True
        )


    @rt("/api/leader-radar-chart")
    def leader_radar_chart(request: Request):
        # Get the main leader ID and optional best/worst matchup IDs
        leader_id = request.query_params.get("lid")
        best_matchup_id = request.query_params.get("lid_best")
        worst_matchup_id = request.query_params.get("lid_worst")
        
        # Collect all leader IDs to display
        leader_ids = [leader_id]
        if best_matchup_id:
            leader_ids.append(best_matchup_id)
        if worst_matchup_id:
            leader_ids.append(worst_matchup_id)
        
        # Get meta formats from request
        meta_formats = request.query_params.getlist("meta_format")
        if not meta_formats:
            meta_formats = [MetaFormat.latest_meta_format()]
        else:
            # Convert string values to MetaFormat enum
            meta_formats = [MetaFormat(mf) for mf in meta_formats]
            
        only_official = request.query_params.get("only_official", "true").lower() == "true"
        
        if not leader_id:
            return ft.Div(ft.P("No leader selected", cls="text-red-400"))
        
        # Get leader data to determine colors
        leader_data = get_leader_extended(leader_ids=leader_ids)
        if not leader_data:
            return ft.Div(ft.P("Leader data not found", cls="text-red-400"))
            
        # Get filtered leader data and their colors
        leaders = []
        colors = []
        for lid in leader_ids:
            leader = next((l for l in leader_data if l.id == lid and l.meta_format in meta_formats), None)
            if leader:
                leaders.append(leader)
                colors.append(leader.to_hex_color())
        
        if not leaders:
            return ft.Div(ft.P("Leaders not found in selected meta format", cls="text-red-400"))
        
        # Get radar chart data
        radar_data = get_radar_chart_data(leader_ids, meta_formats, only_official)
        if not radar_data:
            return ft.Div(ft.P("No matchup data available", cls="text-gray-400"))
        
        # Create a unique ID for this chart instance to avoid conflicts
        chart_id = f"radar-chart-{'-'.join(leader_ids)}-{hash(str(meta_formats))}"
        
        # Create radar chart
        return create_leader_win_rate_radar_chart(
            container_id=chart_id,
            data=radar_data,
            leader_ids=leader_ids,
            colors=colors,
            show_legend=True,
        )

    @rt("/api/card-occurrence-chart")
    def get_card_occurrence_chart(request: Request):
        """Return the card occurrence streaming chart data."""
        card_id = request.query_params.get("card_id")
        meta_format = request.query_params.get("meta_format")
        normalized = request.query_params.get("normalized", "false").lower() == "true"
        
        if not card_id:
            return ft.Div("No card ID provided", cls="text-red-400")
            
        if not meta_format:
            return ft.Div("No meta format provided", cls="text-red-400")
            
        try:
            # Get card data to determine colors and release meta
            card_data_lookup = get_card_id_card_data_lookup()
            card_data = card_data_lookup.get(card_id)
            if not card_data:
                return ft.Div("Card not found", cls="text-red-400")
            
            # Get release meta and subsequent metas (last 10)
            release_meta = card_data.meta_format
            start_meta = release_meta if release_meta != MetaFormat.OP01 else MetaFormat.OP02
            meta_formats = MetaFormat.to_list()[MetaFormat.to_list().index(start_meta):]
            meta_formats = meta_formats[-10:]  # Last 10 meta formats
            
            # Get leaders of the same color
            leaders_of_same_color = {
                cid: cdata for cid, cdata in card_data_lookup.items() 
                if (cdata.card_category == OPTcgCardCatagory.LEADER and 
                    any(c in cdata.colors for c in card_data.colors))
            }
            
            # Get tournament decklist data
            decklist_data = get_tournament_decklist_data(
                meta_formats, 
                leader_ids=list(leaders_of_same_color.keys())
            )
            
            # Initialize occurrence count dictionary
            init_lid2card_occ_dict = {lid: 0 for lid in leaders_of_same_color.keys()}
            meta_leader_id2card_occurrence_count = {
                mf: init_lid2card_occ_dict.copy() for mf in meta_formats
            }
            
            # Count card occurrences by meta format and leader
            for ddata in decklist_data:
                if (ddata.meta_format in meta_leader_id2card_occurrence_count and 
                    card_id in ddata.decklist):
                    meta_leader_id2card_occurrence_count[ddata.meta_format][ddata.leader_id] += 1
            
            # Get top N leaders by occurrence across last 3 meta formats
            top_n_leaders = 5
            leader_id_to_highest_value = {}
            last_3_metas = meta_formats[-3:] if len(meta_formats) >= 3 else meta_formats
            
            for meta in last_3_metas:
                for lid, occurrence in meta_leader_id2card_occurrence_count[meta].items():
                    if lid not in leader_id_to_highest_value:
                        leader_id_to_highest_value[lid] = occurrence
                    elif leader_id_to_highest_value[lid] < occurrence:
                        leader_id_to_highest_value[lid] = occurrence
            
            most_occurring_leader_ids = [
                k for k, v in sorted(
                    leader_id_to_highest_value.items(), 
                    key=lambda item: item[1], 
                    reverse=True
                )
            ][:top_n_leaders]
            
            # Prepare chart data - only include leaders with occurrences > 0
            chart_data = []
            for meta in meta_formats:
                meta_data = {}
                for lid in most_occurring_leader_ids:
                    occ_count = meta_leader_id2card_occurrence_count[meta][lid]
                    if occ_count > 0:  # Only include leaders with occurrences
                        leader_name = lid_to_name_and_lid(lid)
                        meta_data[leader_name] = occ_count
                chart_data.append(meta_data)
            
            # Create the streaming chart
            return create_card_occurrence_streaming_chart(
                container_id=f"card-occurrence-chart-{card_id}",
                data=chart_data,
                meta_formats=[str(mf) for mf in meta_formats],
                card_name=card_data.name,
                normalized=normalized
            )
            
        except Exception as e:
            return ft.Div(f"Error loading chart: {str(e)}", cls="text-red-400") 