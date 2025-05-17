from fasthtml import ft
from starlette.requests import Request
from op_tcg.frontend_fasthtml.utils.api import get_query_params_as_dict
from op_tcg.frontend_fasthtml.utils.extract import get_leader_extended
from op_tcg.frontend_fasthtml.utils.filter import filter_leader_extended
from op_tcg.frontend_fasthtml.pages.leader import create_leader_select
from op_tcg.frontend_fasthtml.api.models import LeaderDataParams

def setup_api_routes(rt):
    @rt("/api/leader-select")
    async def get_leader_select(request: Request):
        # Parse params using Pydantic model
        params = LeaderDataParams(**get_query_params_as_dict(request))
        
        # Get all leaders for the selected meta formats
        leader_data = get_leader_extended()
        filtered_leaders = filter_leader_extended(
            leaders=[l for l in leader_data if l.meta_format in params.meta_format],
            only_official=params.only_official
        )
        
        # Check if the current leader is available in the new meta format
        current_leader_available = any(l.id == params.lid for l in filtered_leaders) if params.lid else False
        
        # Create and return the leader select component
        # Pass the current leader ID only if it's available in the new meta format
        return create_leader_select(
            selected_meta_formats=params.meta_format,
            selected_leader_id=params.lid if current_leader_available else None
        ) 