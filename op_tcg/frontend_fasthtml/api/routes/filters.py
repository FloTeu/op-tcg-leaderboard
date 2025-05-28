from fasthtml import ft
from starlette.requests import Request
from op_tcg.frontend_fasthtml.utils.api import get_query_params_as_dict
from op_tcg.frontend_fasthtml.components.filters import create_leader_select_component
from op_tcg.frontend_fasthtml.api.models import LeaderDataParams

def setup_api_routes(rt):
    @rt("/api/leader-select")
    async def get_leader_select(request: Request):
        # Parse params using Pydantic model
        params = LeaderDataParams(**get_query_params_as_dict(request))
        
        # Check if the current leader is available in the new meta format
        # This will be handled by the component itself, but we pass the selected_leader_id
        # The component will auto-select the top leader if the current one is not available
        
        # Use the modular leader select component
        return create_leader_select_component(
            selected_meta_formats=params.meta_format,
            selected_leader_id=params.lid,
            only_official=params.only_official,
            auto_select_top=True  # Auto-select top leader if current one is not available
        )
    
    @rt("/api/leader-select-generic")
    async def get_leader_select_generic(request: Request):
        """Generic leader select endpoint that can be customized via query parameters."""
        # Get query params as dict
        query_params = get_query_params_as_dict(request)
        
        # Handle both 'lid' and 'leader_id' parameter names for compatibility
        leader_id = query_params.get('lid') or query_params.get('leader_id')
        if leader_id and 'lid' not in query_params:
            query_params['lid'] = leader_id
        
        # Parse params using Pydantic model
        params = LeaderDataParams(**query_params)
        
        # Get additional customization parameters
        wrapper_id = request.query_params.get("wrapper_id", "leader-select-wrapper")
        select_id = request.query_params.get("select_id", "leader-select")
        select_name = request.query_params.get("select_name", "lid")
        label = request.query_params.get("label", "Leader")
        auto_select_top = request.query_params.get("auto_select_top", "true").lower() == "true"
        include_label = request.query_params.get("include_label", "true").lower() == "true"
        
        # Use the modular leader select component with custom parameters
        return create_leader_select_component(
            selected_meta_formats=params.meta_format,
            selected_leader_id=params.lid,  # This now contains the leader_id if that was passed
            only_official=params.only_official,
            wrapper_id=wrapper_id,
            select_id=select_id,
            select_name=select_name,
            label=label,
            auto_select_top=auto_select_top,
            include_label=include_label
        ) 