from starlette.requests import Request
from op_tcg.frontend_fasthtml.pages.leader import create_leader_select
from op_tcg.frontend_fasthtml.api.models import LeaderSelectParams
from op_tcg.frontend_fasthtml.utils.api import get_query_params_as_dict

def setup_api_routes(rt):
    @rt("/api/leader-select")
    def get_leader_select(request: Request):
        # Parse params using Pydantic model
        params = LeaderSelectParams(**get_query_params_as_dict(request))
        
        # Create and return the updated leader select
        return create_leader_select(params.meta_format, params.lid) 