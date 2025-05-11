from fasthtml import ft
from starlette.requests import Request
from op_tcg.backend.models.input import MetaFormat
from op_tcg.frontend_fasthtml.utils.colors import ChartColors
from op_tcg.frontend_fasthtml.utils.extract import get_leader_extended
from op_tcg.frontend_fasthtml.utils.charts import create_line_chart, create_leader_win_rate_radar_chart
from op_tcg.frontend_fasthtml.utils.win_rate import get_radar_chart_data
from op_tcg.frontend_fasthtml.utils.api import get_filtered_leaders


def setup_api_routes(rt):

    @rt("/api/leader-chart/{leader_id}")
    def leader_line_chart(request: Request, leader_id: str):
        # Get query parameters
        all_meta_formats = MetaFormat.to_list()
        meta_format = MetaFormat(request.query_params.get("meta_format", MetaFormat.latest_meta_format()))
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
        leader_id = request.query_params.get("lid")
        
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
        
        # Get leader data to determine color
        leader_data = get_leader_extended(leader_ids=[leader_id])
        if not leader_data:
            return ft.Div(ft.P("Leader data not found", cls="text-red-400"))
            
        # Get filtered leader data
        leader = next((l for l in leader_data if l.meta_format in meta_formats), None)
        if not leader:
            return ft.Div(ft.P("Leader not found in selected meta format", cls="text-red-400"))
        
        # Get radar chart data
        radar_data = get_radar_chart_data([leader_id], meta_formats, only_official)
        if not radar_data:
            return ft.Div(ft.P("No matchup data available", cls="text-gray-400"))
        
        # Create a unique ID for this chart instance to avoid conflicts
        chart_id = f"radar-chart-{leader_id}-{hash(str(meta_formats))}"
        
        # Create radar chart
        return create_leader_win_rate_radar_chart(
            container_id=chart_id,
            data=radar_data,
            leader_ids=[leader_id],
            colors=[leader.to_hex_color()],
            show_legend=False,
        )