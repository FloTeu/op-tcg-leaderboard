from dotenv import load_dotenv
load_dotenv()

from fasthtml import ft
from fasthtml.common import fast_app, serve
from starlette.responses import FileResponse
from contextlib import asynccontextmanager
from op_tcg.backend.utils.environment import is_debug
from op_tcg.frontend_fasthtml.utils.scripts import create_decklist_deep_link_script
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
from op_tcg.frontend_fasthtml.utils.seo import canonical_base, write_static_sitemap
from op_tcg.frontend_fasthtml.utils.middleware import canonical_redirect_middleware
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
        # Generate static sitemap on startup so /sitemap.xml is always available
        write_static_sitemap()
        logger.info("Static sitemap.xml generated successfully")
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
        # Favicon
        ft.Link(rel="icon", type="image/png", href="/public/favicon32x23.png"),
        # Impact site verification
        ft.Meta(name="impact-site-verification", content="42884b40-0e25-4302-9ead-e1bd322b1ed8"),
        # Basic SEO defaults (can be overridden per-route)
        ft.Meta(name="viewport", content="width=device-width, initial-scale=1"),
        ft.Meta(name="theme-color", content="#111827"),
        ft.Meta(property="og:site_name", content="OP TCG Leaderboard"),
        ft.Meta(property="og:type", content="website"),
        ft.Meta(name="twitter:card", content="summary_large_image"),
        ft.Meta(name="twitter:site", content="@op_leaderboard"),
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
        ft.Link(
            href="/public/css/decklist.css",
            rel="stylesheet"
        ),
        # GoatCounter script
        ft.Script(data_goatcounter="https://op-leaderboard.goatcounter.com/count", src="//gc.zgo.at/count.js"),
        ft.Script(src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"),
        # Core utilities and libraries
        ft.Script(src="/public/js/htmx-loader.js"),  # Conditionally load htmx if not already present
        ft.Script(src="/public/js/utils.js"),
        ft.Script(src="/public/js/charts.js"),
        ft.Script(src="/public/js/multiselect.js"),
        ft.Script(src="/public/js/double_range_slider.js"),
        ft.Script(src="/public/js/sidebar.js"),
    ],
    #static_path='public'
)



# Sitemap works reliably 
@rt("/sitemap.xml")
async def serve_sitemap():
    return FileResponse("public/sitemap.xml", media_type="application/xml")



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


@app.middleware("http")
async def enforce_canonical_host(request, call_next):
    return await canonical_redirect_middleware(request, call_next)

@rt("/")
def home(request: Request):
    # Add canonical link to head for home page using incoming host
    canonical_url = canonical_base(request)
    title = "OP TCG Leaderboard – Meta, Decklists, Prices & Matchups"
    description = "Track One Piece TCG leaders, meta trends, decklists, prices, and matchups. Updated regularly with official and community results."
    # Build persisted query object for navigation links
    persist_query = {
        "meta_format": request.query_params.get("meta_format"),
        "region": request.query_params.get("region")
    }
    
    # Determine selected values for filters
    selected_meta_format = request.query_params.get("meta_format")
    selected_region = request.query_params.get("region")
    selected_meta_format_enum = MetaFormat(selected_meta_format) if selected_meta_format else None
    selected_region_enum = MetaFormatRegion(selected_region) if selected_region else None
    
    return (
        ft.Title(title),
        ft.Meta(name="description", content=description),
        ft.Meta(property="og:title", content=title),
        ft.Meta(property="og:description", content=description),
        ft.Meta(property="og:url", content=canonical_url),
        ft.Link(rel="canonical", href=canonical_url),
        layout(
            home_page(),
            filter_component=home_filters(selected_meta_format=selected_meta_format_enum, selected_region=selected_region_enum),
            current_path="/",
            persist_query=persist_query
        )
    )



@rt("/leader")
def leader_default(request: Request):
    # Get selected meta formats from query params (can be multiple)
    selected_meta_format = request.query_params.getlist("meta_format")
    leader_id = request.query_params.get("lid")
    selected_meta_format_region = request.query_params.get("region")
    
    # Convert to MetaFormat enum if present
    if selected_meta_format:
        selected_meta_format = [MetaFormat(mf) for mf in selected_meta_format]
    
    # Convert to MetaFormatRegion enum if present
    if selected_meta_format_region:
        selected_meta_format_region = MetaFormatRegion(selected_meta_format_region)
    
    # Add canonical link to head based on incoming host
    canonical_url = f"{canonical_base(request)}/leader"
    title = "Leader Meta & Performance – OP TCG Leaderboard"
    description = "Explore leader performance across formats, with meta share, win rates, and top decklists."
    
    # Pass to leader_page which will handle HTMX loading
    persist_query = {
        "meta_format": request.query_params.get("meta_format"),
        "region": request.query_params.get("region")
    }
    return (
        ft.Title(title),
        ft.Meta(name="description", content=description),
        ft.Meta(property="og:title", content=title),
        ft.Meta(property="og:description", content=description),
        ft.Meta(property="og:url", content=canonical_url),
        ft.Link(rel="canonical", href=canonical_url),
        # Shared deep-linking functionality for decklist modals
        create_decklist_deep_link_script(),
        layout(
            leader_page(leader_id, selected_meta_format=selected_meta_format),
            filter_component=leader_filters(
                selected_meta_formats=selected_meta_format, 
                selected_leader_id=leader_id,
                selected_region=selected_meta_format_region
            ),
            current_path="/leader",
            persist_query=persist_query
        )
    )

@rt("/tournaments")
def tournaments(request: Request):
    # Add canonical link to head based on incoming host
    canonical_url = f"{canonical_base(request)}/tournaments"
    title = "Tournaments – Results & Decklists – OP TCG Leaderboard"
    description = "Browse tournament results, standings, and decklists across regions and formats."
    
    persist_query = {
        "meta_format": request.query_params.get("meta_format"),
        "region": request.query_params.get("region")
    }
    # Parse selections
    selected_meta_formats = request.query_params.getlist("meta_format")
    selected_meta_formats = [MetaFormat(mf) for mf in selected_meta_formats] if selected_meta_formats else None
    selected_region = request.query_params.get("region")
    selected_region_enum = MetaFormatRegion(selected_region) if selected_region else None
    return (
        ft.Title(title),
        ft.Meta(name="description", content=description),
        ft.Meta(property="og:title", content=title),
        ft.Meta(property="og:description", content=description),
        ft.Meta(property="og:url", content=canonical_url),
        ft.Link(rel="canonical", href=canonical_url),
        # Shared deep-linking functionality for decklist modals
        create_decklist_deep_link_script(),
        layout(tournaments_page(), filter_component=tournament_filters(selected_meta_formats=selected_meta_formats, selected_region=selected_region_enum), current_path="/tournaments", persist_query=persist_query)
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
    canonical_url = f"{canonical_base(request)}/card-movement"
    title = "Card Movement – Prices & Popularity – OP TCG Leaderboard"
    description = "Track card price trends and popularity changes to spot rising staples and value."
    
    # Pass to card_movement_page which will handle HTMX loading
    persist_query = {
        "meta_format": request.query_params.get("meta_format"),
        "region": request.query_params.get("region")
    }
    return (
        ft.Title(title),
        ft.Meta(name="description", content=description),
        ft.Meta(property="og:title", content=title),
        ft.Meta(property="og:description", content=description),
        ft.Meta(property="og:url", content=canonical_url),
        ft.Link(rel="canonical", href=canonical_url),
        layout(card_movement_page(), filter_component=card_movement_filters(selected_meta_format=selected_meta_format, selected_leader_id=selected_leader_id), current_path="/card-movement", persist_query=persist_query)
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
    canonical_url = f"{canonical_base(request)}/matchups"
    title = "Leader Matchups – Win Rates & Counters – OP TCG Leaderboard"
    description = "Analyze leader vs leader matchups, win rates, and counter picks across formats."
    
    # Pass to matchups_page which will handle HTMX loading
    persist_query = {
        "meta_format": request.query_params.get("meta_format"),
        "region": request.query_params.get("region")
    }
    return (
        ft.Title(title),
        ft.Meta(name="description", content=description),
        ft.Meta(property="og:title", content=title),
        ft.Meta(property="og:description", content=description),
        ft.Meta(property="og:url", content=canonical_url),
        ft.Link(rel="canonical", href=canonical_url),
        layout(matchups_page(), filter_component=matchups_filters(selected_meta_formats=selected_meta_formats, selected_leader_ids=selected_leader_ids, only_official=only_official), current_path="/matchups", persist_query=persist_query)
    )

# Card pages
@rt("/card-popularity")
def card_popularity(request: Request):
    # Add canonical link to head based on incoming host
    canonical_url = f"{canonical_base(request)}/card-popularity"
    title = "Card Popularity – Usage & Trends – OP TCG Leaderboard"
    description = "Discover the most played cards and shifting usage trends across formats and leaders."
    
    persist_query = {
        "meta_format": request.query_params.get("meta_format"),
        "region": request.query_params.get("region")
    }
    # Parse selections
    selected_meta_format = request.query_params.get("meta_format")
    selected_meta_format_enum = MetaFormat(selected_meta_format) if selected_meta_format else None
    from op_tcg.backend.models.cards import CardCurrency
    selected_currency = request.query_params.get("currency")
    selected_currency_enum = CardCurrency(selected_currency) if selected_currency else None
    return (
        ft.Title(title),
        ft.Meta(name="description", content=description),
        ft.Meta(property="og:title", content=title),
        ft.Meta(property="og:description", content=description),
        ft.Meta(property="og:url", content=canonical_url),
        ft.Link(rel="canonical", href=canonical_url),
        layout(card_popularity_page(), filter_component=card_popularity_filters(selected_meta_format=selected_meta_format_enum, currency=selected_currency_enum), current_path="/card-popularity", persist_query=persist_query)
    )

# Prices page
@rt("/prices")
def prices(request: Request):
    canonical_url = f"{canonical_base(request)}/prices"
    title = "Card Prices – Market Trends – OP TCG Leaderboard"
    description = "See current OP TCG card prices and market movement with historical trends."
    return (
        ft.Title(title),
        ft.Meta(name="description", content=description),
        ft.Meta(property="og:title", content=title),
        ft.Meta(property="og:description", content=description),
        ft.Meta(property="og:url", content=canonical_url),
        ft.Link(rel="canonical", href=canonical_url),
        layout(prices_page(), filter_component=prices_filters(), current_path="/prices")
    )

# Support pages
@rt("/bug-report")
def bug_report(request: Request):
    # Add canonical link to head based on incoming host
    canonical_url = f"{canonical_base(request)}/bug-report"
    title = "Report a Bug – OP TCG Leaderboard"
    description = "Spotted an issue? Report bugs and help us improve OP TCG Leaderboard."
    
    persist_query = {
        "meta_format": request.query_params.get("meta_format"),
        "region": request.query_params.get("region")
    }
    return (
        ft.Title(title),
        ft.Meta(name="description", content=description),
        ft.Meta(property="og:title", content=title),
        ft.Meta(property="og:description", content=description),
        ft.Meta(property="og:url", content=canonical_url),
        ft.Link(rel="canonical", href=canonical_url),
        layout(bug_report_page(), filter_component=None, current_path="/bug-report", persist_query=persist_query)
    )

if __name__ == "__main__":
    # Start background tasks
    serve()
