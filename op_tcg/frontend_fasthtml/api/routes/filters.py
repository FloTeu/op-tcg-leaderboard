from starlette.requests import Request
from op_tcg.frontend_fasthtml.utils.api import get_query_params_as_dict
from op_tcg.frontend_fasthtml.api.models import LeaderSelectParams
from op_tcg.frontend_fasthtml.pages.leader import create_leader_select

def setup_api_routes(rt):
    @rt("/api/leader-select")
    async def get_leader_select(request: Request):
        # Parse params using Pydantic model
        params = LeaderSelectParams(**get_query_params_as_dict(request))
        
        # Create and return the leader select component
        return create_leader_select(params.meta_format) 