from fasthtml import ft
from starlette.requests import Request
from op_tcg.backend.models.input import MetaFormat
from op_tcg.frontend_fasthtml.utils.api import get_query_params_as_dict
from op_tcg.frontend_fasthtml.components.filters import create_leader_select_component, create_leader_multiselect_component
from op_tcg.frontend_fasthtml.api.models import LeaderDataParams, MatchupParams

def setup_api_routes(rt):
    @rt("/api/leader-select")
    async def get_leader_select(request: Request):
        # Parse params using Pydantic model
        query_params = get_query_params_as_dict(request)
        
        # Set defaults for leader page if not provided
        if not query_params.get('meta_format'):
            query_params['meta_format'] = [MetaFormat.latest_meta_format()]
        
        if 'only_official' not in query_params:
            query_params['only_official'] = True
            
        params = LeaderDataParams(**query_params)
        
        # Check if the current leader is available in the new meta format
        # This will be handled by the component itself, but we pass the selected_leader_id
        # The component will auto-select the top leader if the current one is not available
        
        # Use the modular leader select component
        return create_leader_select_component(
            selected_meta_formats=params.meta_format,
            selected_leader_id=params.lid,
            only_official=params.only_official,
            auto_select_top=True,  # Auto-select top leader if current one is not available
            htmx_attrs={
                "hx_get": "/api/leader-data",
                "hx_trigger": "change", 
                "hx_target": "#leader-content",
                "hx_include": "[name='meta_format'],[name='lid'],[name='only_official']",
                "hx_indicator": "#loading-indicator"
            }
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
        
        # Set defaults if not provided
        if not query_params.get('meta_format'):
            query_params['meta_format'] = [MetaFormat.latest_meta_format()]
        
        if 'only_official' not in query_params:
            query_params['only_official'] = True
        
        # Parse params using Pydantic model
        params = LeaderDataParams(**query_params)
        
        # Get additional customization parameters
        wrapper_id = request.query_params.get("wrapper_id", "leader-select-wrapper")
        select_id = request.query_params.get("select_id", "leader-select")
        select_name = request.query_params.get("select_name", "lid")
        label = request.query_params.get("label", "Leader")
        auto_select_top = request.query_params.get("auto_select_top", "true").lower() == "true"
        include_label = request.query_params.get("include_label", "true").lower() == "true"
        
        # Determine HTMX attributes based on select_name (page context)
        if select_name == "leader_id":  # Card movement page
            htmx_attrs = {
                "hx_get": "/api/card-movement-content",
                "hx_trigger": "change",
                "hx_target": "#card-movement-content",
                "hx_include": "[name='meta_format'],[name='leader_id']",
                "hx_indicator": "#card-movement-loading-indicator"
            }
        else:  # Default to leader page
            htmx_attrs = {
                "hx_get": "/api/leader-data",
                "hx_trigger": "change", 
                "hx_target": "#leader-content",
                "hx_include": "[name='meta_format'],[name='lid'],[name='only_official']",
                "hx_indicator": "#loading-indicator"
            }
        
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
            include_label=include_label,
            htmx_attrs=htmx_attrs
        )

    @rt("/api/leader-multiselect")
    async def get_leader_multiselect(request: Request):
        """Generic leader multi-select endpoint that can be customized via query parameters."""
        # Parse params using MatchupParams model which supports leader_ids
        query_params = get_query_params_as_dict(request)
        
        # Set defaults for matchups page if not provided
        if not query_params.get('meta_format'):
            query_params['meta_format'] = [MetaFormat.latest_meta_format()]
        
        if 'only_official' not in query_params:
            query_params['only_official'] = True
            
        params = MatchupParams(**query_params)
        
        # Get additional customization parameters
        wrapper_id = request.query_params.get("wrapper_id", "leader-multiselect-wrapper")
        select_id = request.query_params.get("select_id", "leader-multiselect")
        select_name = request.query_params.get("select_name", "leader_ids")
        label = request.query_params.get("label", "Leaders")
        auto_select_top = int(request.query_params.get("auto_select_top", "5"))
        include_label = request.query_params.get("include_label", "true").lower() == "true"
        use_win_rate_filtering = request.query_params.get("use_win_rate_filtering", "true").lower() == "true"
        
        # Use the modular leader multi-select component with custom parameters
        return create_leader_multiselect_component(
            selected_meta_formats=params.meta_format,
            selected_leader_ids=params.leader_ids,
            only_official=params.only_official,
            wrapper_id=wrapper_id,
            select_id=select_id,
            select_name=select_name,
            label=label,
            htmx_attrs={
                "hx_get": "/api/matchup-content",
                "hx_trigger": "change",
                "hx_target": "#matchup-content",
                "hx_include": "[name='meta_format'],[name='only_official'],[name='leader_ids']",
                "hx_indicator": "#matchup-loading-indicator"
            },
            auto_select_top=auto_select_top,
            include_label=include_label,
            use_win_rate_filtering=use_win_rate_filtering
        ) 