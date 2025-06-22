from dotenv import load_dotenv
load_dotenv()

from fasthtml import ft
from fasthtml.common import fast_app, serve
from contextlib import asynccontextmanager
from op_tcg.frontend_fasthtml.components.layout import layout
from op_tcg.frontend_fasthtml.pages.home import home_page, create_filter_components as home_filters
from op_tcg.frontend_fasthtml.pages.leader import leader_page, create_filter_components as leader_filters
from op_tcg.frontend_fasthtml.pages.tournaments import tournaments_page, create_filter_components as tournament_filters
from op_tcg.frontend_fasthtml.pages.card_movement import card_movement_page, create_filter_components as card_movement_filters
from op_tcg.frontend_fasthtml.pages.matchups import matchups_page, create_filter_components as matchups_filters
from op_tcg.frontend_fasthtml.pages.card_popularity import card_popularity_page, create_filter_components as card_popularity_filters
from op_tcg.frontend_fasthtml.pages.bug_report import bug_report_page
from op_tcg.frontend_fasthtml.api.routes.main import setup_api_routes
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from starlette.requests import Request
from op_tcg.frontend_fasthtml.utils.cache_warmer import start_cache_warming, stop_cache_warming, warm_cache_now
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app):
    """Application lifespan manager - runs in the same process as request handlers"""
    logger.info("Starting OP TCG Leaderboard application...")
    
    try:
        # Start background cache warming in the worker process
        start_cache_warming()
        logger.info("Cache warming started successfully")
    except Exception as e:
        logger.error(f"Failed to start cache warming: {e}")
    
    yield  # Application runs here
    
    # Cleanup on shutdown
    logger.info("Shutting down OP TCG Leaderboard application...")
    try:
        stop_cache_warming()
        logger.info("Cache warming stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping cache warming: {e}")

# Create main app with lifespan manager
app, rt = fast_app(
    pico=False,
    lifespan=lifespan,  # Add lifespan manager here
    hdrs=[
        ft.Style(':root { --pico-font-size: 100%; }'),
        ft.Style('body { background-color: rgb(17, 24, 39); }'),
        ft.Link(
            href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css",
            rel="stylesheet"
        ),
        ft.Link(
            href="/public/css/loading.css",
            rel="stylesheet"
        ),
        ft.Link(
            href="/public/css/multiselect.css",
            rel="stylesheet"
        ),
        ft.Link(
            href="/public/css/double_range_slider.css",
            rel="stylesheet"
        ),
        ft.Link(
            href="/public/css/tooltip.css",
            rel="stylesheet"
        ),
        # GoatCounter script
        ft.Script(data_goatcounter="https://op-leaderboard.goatcounter.com/count", src="//gc.zgo.at/count.js"),
        ft.Script(src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"),
        # Core utilities and libraries
        ft.Script(src="/public/js/utils.js"),  # Global utilities
        ft.Script(src="/public/js/multiselect.js"),  # Base select functionality
        # Page utilities
        ft.Script(src="/public/js/sidebar.js"),
    ],
    #static_path=''
)

# Setup API routes
setup_api_routes(rt)

@rt("/api/cache/status")
def cache_status():
    """Get cache warmer status"""
    from op_tcg.frontend_fasthtml.utils.cache_warmer import get_cache_warmer
    warmer = get_cache_warmer()
    return {
        "is_running": warmer.is_running,
        "warm_interval_hours": warmer.warm_interval_hours
    }

@rt("/api/cache/stats")
def cache_stats():
    """Get cache performance statistics"""
    from op_tcg.frontend_fasthtml.utils.cache_monitor import get_cache_summary
    return get_cache_summary()

@rt("/api/cache/warm")
def warm_cache_manual():
    """Manually trigger cache warming"""
    try:
        warm_cache_now()
        return {"status": "success", "message": "Cache warming initiated"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@rt("/api/cache/clear")
def clear_cache():
    """Clear all caches"""
    try:
        from op_tcg.frontend_fasthtml.utils.cache import clear_all_caches
        clear_all_caches()
        return {"status": "success", "message": "All caches cleared"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Leader pages
@rt("/")
def home():
    return layout(home_page(), filter_component=home_filters(), current_path="/")

@rt("/leader")
def leader_default(request: Request):
    # Get selected meta formats from query params (can be multiple)
    selected_meta_format = request.query_params.getlist("meta_format")
    leader_id = request.query_params.get("lid")
    selected_meta_format_region = request.query_params.get("meta_format_region")
    
    # Convert to MetaFormat enum if present
    if selected_meta_format:
        selected_meta_format = [MetaFormat(mf) for mf in selected_meta_format]
    
    # Convert to MetaFormatRegion enum if present
    if selected_meta_format_region:
        selected_meta_format_region = MetaFormatRegion(selected_meta_format_region)
    
    # Pass to leader_page which will handle HTMX loading
    return layout(
        leader_page(leader_id, selected_meta_format=selected_meta_format),
        filter_component=leader_filters(
            selected_meta_formats=selected_meta_format, 
            selected_leader_id=leader_id,
            selected_meta_format_region=selected_meta_format_region
        ),
        current_path="/leader"
    )

@rt("/tournaments")
def tournaments():
    return layout(tournaments_page(), filter_component=tournament_filters(), current_path="/tournaments")

@rt("/card-movement")
def card_movement(request: Request):
    # Get selected meta format and leader ID from query params
    selected_meta_format = request.query_params.get("meta_format")
    selected_leader_id = request.query_params.get("leader_id")
    
    # Convert to MetaFormat enum if present
    if selected_meta_format:
        selected_meta_format = MetaFormat(selected_meta_format)
    
    # Pass to card_movement_page which will handle HTMX loading
    return layout(
        card_movement_page(), 
        filter_component=card_movement_filters(
            selected_meta_format=selected_meta_format,
            selected_leader_id=selected_leader_id
        ), 
        current_path="/card-movement"
    )

@rt("/matchups")
def matchups(request: Request):
    # Get selected meta formats from query params (can be multiple)
    selected_meta_formats = request.query_params.getlist("meta_format")
    selected_leader_ids = request.query_params.getlist("leader_ids")
    only_official = request.query_params.get("only_official", "true").lower() in ("true", "on", "1", "yes")
    
    # Convert to MetaFormat enum if present
    if selected_meta_formats:
        selected_meta_formats = [MetaFormat(mf) for mf in selected_meta_formats]
    
    # Pass to matchups_page which will handle HTMX loading
    return layout(
        matchups_page(), 
        filter_component=matchups_filters(
            selected_meta_formats=selected_meta_formats,
            selected_leader_ids=selected_leader_ids,
            only_official=only_official
        ), 
        current_path="/matchups"
    )

# Card pages
@rt("/card-popularity")
def card_popularity():
    return layout(card_popularity_page(), filter_component=card_popularity_filters(), current_path="/card-popularity")

# Support pages
@rt("/bug-report")
def bug_report():
    return layout(bug_report_page(), filter_component=None, current_path="/bug-report")

if __name__ == "__main__":
    # Start background tasks
    serve()
