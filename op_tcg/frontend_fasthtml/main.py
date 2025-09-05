import os
from dotenv import load_dotenv

from op_tcg.backend.utils.environment import is_debug
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
from op_tcg.frontend_fasthtml.pages.prices import prices_page, create_filter_components as prices_filters
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
        if not is_debug():
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
        # Impact site verification
        ft.Meta(name="impact-site-verification", value="42884b40-0e25-4302-9ead-e1bd322b1ed8"),
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
CANONICAL_HOST = os.environ.get("CANONICAL_HOST")  # e.g., "op-leaderboard.com" or "www.op-leaderboard.com"

def _canonical_base(request: Request) -> str:
    """Return canonical base using incoming host and scheme.

    Preserves www vs non-www based on the Host header and respects proxies via X-Forwarded-Proto.
    """
    # Prefer X-Forwarded-Proto when deployed behind a proxy (e.g., Cloud Run, Nginx)
    forwarded_proto = request.headers.get("x-forwarded-proto")
    scheme = (forwarded_proto or request.url.scheme or "https").split(",")[0].strip()
    # On Cloud Run, Host header will be the custom domain if mapped; allow override via env
    host = CANONICAL_HOST or request.headers.get("host") or request.url.netloc
    # Normalize host casing
    host = host.strip()
    return f"{scheme}://{host}"

# Middleware-like redirect: enforce single host if CANONICAL_HOST is set
@app.middleware("http")
async def enforce_canonical_host(request, call_next):
    if CANONICAL_HOST:
        request_host = (request.headers.get("host") or request.url.netloc or "").strip()
        if request_host and request_host.lower() != CANONICAL_HOST.lower():
            forwarded_proto = request.headers.get("x-forwarded-proto")
            scheme = (forwarded_proto or request.url.scheme or "https").split(",")[0].strip()
            destination = f"{scheme}://{CANONICAL_HOST}{request.url.path}"
            if request.url.query:
                destination += f"?{request.url.query}"
            from starlette.responses import RedirectResponse
            # 308 preserves method and body; best for SEO permanence
            return RedirectResponse(url=destination, status_code=308)
    return await call_next(request)

@rt("/")
def home(request: Request):
    # Add canonical link to head for home page using incoming host
    canonical_url = _canonical_base(request)
    return (
        ft.Link(rel="canonical", href=canonical_url),
        layout(home_page(), filter_component=home_filters(), current_path="/")
    )

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
    
    # Add canonical link to head based on incoming host
    canonical_url = f"{_canonical_base(request)}/leader"
    
    # Pass to leader_page which will handle HTMX loading
    return (
        ft.Link(rel="canonical", href=canonical_url),
        layout(
            leader_page(leader_id, selected_meta_format=selected_meta_format),
            filter_component=leader_filters(
                selected_meta_formats=selected_meta_format, 
                selected_leader_id=leader_id,
                selected_meta_format_region=selected_meta_format_region
            ),
            current_path="/leader"
        )
    )

@rt("/tournaments")
def tournaments(request: Request):
    # Add canonical link to head based on incoming host
    canonical_url = f"{_canonical_base(request)}/tournaments"
    
    return (
        ft.Link(rel="canonical", href=canonical_url),
        layout(tournaments_page(), filter_component=tournament_filters(), current_path="/tournaments")
    )

@rt("/card-movement")
def card_movement(request: Request):
    # Get selected meta format and leader ID from query params
    selected_meta_format = request.query_params.get("meta_format")
    selected_leader_id = request.query_params.get("leader_id")
    
    # Convert to MetaFormat enum if present
    if selected_meta_format:
        selected_meta_format = MetaFormat(selected_meta_format)
    
    # Add canonical link to head based on incoming host
    canonical_url = f"{_canonical_base(request)}/card-movement"
    
    # Pass to card_movement_page which will handle HTMX loading
    return (
        ft.Link(rel="canonical", href=canonical_url),
        layout(
            card_movement_page(), 
            filter_component=card_movement_filters(
                selected_meta_format=selected_meta_format,
                selected_leader_id=selected_leader_id
            ), 
            current_path="/card-movement"
        )
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
    
    # Add canonical link to head based on incoming host
    canonical_url = f"{_canonical_base(request)}/matchups"
    
    # Pass to matchups_page which will handle HTMX loading
    return (
        ft.Link(rel="canonical", href=canonical_url),
        layout(
            matchups_page(), 
            filter_component=matchups_filters(
                selected_meta_formats=selected_meta_formats,
                selected_leader_ids=selected_leader_ids,
                only_official=only_official
            ), 
            current_path="/matchups"
        )
    )

# Card pages
@rt("/card-popularity")
def card_popularity(request: Request):
    # Add canonical link to head based on incoming host
    canonical_url = f"{_canonical_base(request)}/card-popularity"
    
    return (
        ft.Link(rel="canonical", href=canonical_url),
        layout(card_popularity_page(), filter_component=card_popularity_filters(), current_path="/card-popularity")
    )

# Prices page
@rt("/prices")
def prices(request: Request):
    canonical_url = f"{_canonical_base(request)}/prices"
    return (
        ft.Link(rel="canonical", href=canonical_url),
        layout(prices_page(), filter_component=prices_filters(), current_path="/prices")
    )

# Support pages
@rt("/bug-report")
def bug_report(request: Request):
    # Add canonical link to head based on incoming host
    canonical_url = f"{_canonical_base(request)}/bug-report"
    
    return (
        ft.Link(rel="canonical", href=canonical_url),
        layout(bug_report_page(), filter_component=None, current_path="/bug-report")
    )

if __name__ == "__main__":
    # Start background tasks
    serve()
