from dotenv import load_dotenv
load_dotenv()

from fasthtml import ft
from fasthtml.common import fast_app, serve
from op_tcg.frontend_fasthtml.components.layout import layout
from op_tcg.frontend_fasthtml.pages.home import home_page, create_filter_components as home_filters
from op_tcg.frontend_fasthtml.pages.leader import leader_page, create_filter_components as leader_filters
from op_tcg.frontend_fasthtml.pages.tournaments import tournaments_page
from op_tcg.frontend_fasthtml.pages.card_movement import card_movement_page
from op_tcg.frontend_fasthtml.pages.matchups import matchups_page
from op_tcg.frontend_fasthtml.pages.card_popularity import card_popularity_page
from op_tcg.frontend_fasthtml.pages.bug_report import bug_report_page
from op_tcg.frontend_fasthtml.api.routes.main import setup_api_routes
from op_tcg.backend.models.input import MetaFormat
from starlette.requests import Request

# Create main app
app, rt = fast_app(
    pico=False,
    hdrs=[
        ft.Style(':root { --pico-font-size: 100%; }'),
        ft.Style('body { background-color: rgb(17, 24, 39); }'),
        ft.Link(
            href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css",
            rel="stylesheet"
        ),
        ft.Link(
            href="/static/css/loading.css",
            rel="stylesheet"
        ),
        ft.Link(
            href="/static/css/multiselect.css",
            rel="stylesheet"
        ),
        ft.Link(
            href="/static/css/double_range_slider.css",
            rel="stylesheet"
        ),
        ft.Link(
            href="/static/css/tooltip.css",
            rel="stylesheet"
        ),
        ft.Script(src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"),
        # Core utilities and libraries
        ft.Script(src="/static/js/multiselect.js"),  # Base select functionality
        # Page utilities
        ft.Script(src="/static/js/sidebar.js"),
    ],
    static_path='op_tcg/frontend_fasthtml/'
)

# Setup API routes
setup_api_routes(rt)

# Leader pages
@rt("/")
def home():
    return ft.Div(
        ft.Div(
            hx_trigger="load",
            hx_swap="none"
        ),
        layout(home_page(), filter_component=home_filters())
    )

@rt("/leader")
def leader_default(request: Request):
    # Get selected meta formats from query params (can be multiple)
    selected_meta_format = request.query_params.getlist("meta_format")
    leader_id = request.query_params.get("lid")
    
    # Convert to MetaFormat enum if present
    if selected_meta_format:
        selected_meta_format = [MetaFormat(mf) for mf in selected_meta_format]
    
    # Pass to leader_page which will handle HTMX loading
    return layout(
        leader_page(leader_id, selected_meta_format=selected_meta_format),
        filter_component=leader_filters(selected_meta_formats=selected_meta_format, selected_leader_id=leader_id)
    )

@rt("/tournaments")
def tournaments():
    return layout(tournaments_page(), filter_component=None)

@rt("/card-movement")
def card_movement():
    return layout(card_movement_page(), filter_component=None)

@rt("/matchups")
def matchups():
    return layout(matchups_page(), filter_component=None)

# Card pages
@rt("/card-popularity")
def card_popularity():
    return layout(card_popularity_page(), filter_component=None)

# Support pages
@rt("/bug-report")
def bug_report():
    return layout(bug_report_page(), filter_component=None)

if __name__ == "__main__":
    serve()
