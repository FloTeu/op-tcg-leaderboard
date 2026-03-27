from dotenv import load_dotenv
load_dotenv()

from fasthtml import ft
from fasthtml.common import fast_app, serve
from starlette.responses import FileResponse, RedirectResponse
from contextlib import asynccontextmanager
from op_tcg.backend.utils.environment import is_debug
from op_tcg.frontend.utils.scripts import create_decklist_deep_link_script
from op_tcg.frontend.components.layout import layout
from op_tcg.frontend.pages.home import home_page, create_filter_components as home_filters
from op_tcg.frontend.pages.leader import leader_page, create_filter_components as leader_filters
from op_tcg.frontend.pages.tournaments import tournaments_page, create_filter_components as tournament_filters
from op_tcg.frontend.pages.card_movement import card_movement_page, create_filter_components as card_movement_filters
from op_tcg.frontend.pages.matchups import matchups_page, create_filter_components as matchups_filters
from op_tcg.frontend.pages.card_popularity import card_popularity_page, create_filter_components as card_popularity_filters
from op_tcg.frontend.pages.prices import prices_page, create_filter_components as prices_filters
from op_tcg.frontend.pages.watchlist import watchlist_page
from op_tcg.frontend.pages.settings import settings_content
from op_tcg.frontend.pages.register import register_content
from op_tcg.frontend.utils.csrf import get_csrf_token
from op_tcg.frontend.pages.bug_report import bug_report_page
from op_tcg.frontend.pages.about import about_page
from op_tcg.frontend.pages.privacy import privacy_page
from op_tcg.frontend.api.routes.main import setup_api_routes
from op_tcg.frontend.api.routes.auth import setup_auth_routes
from op_tcg.frontend.api.routes.settings import setup_settings_routes
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.cards import CardCurrency
from op_tcg.backend.db import get_user_settings
from starlette.requests import Request
from op_tcg.frontend.utils.cache_warmer import start_cache_warming, stop_cache_warming, warm_cache_now
from op_tcg.frontend.utils.seo import canonical_base, write_static_sitemap
from op_tcg.frontend.utils.middleware import canonical_redirect_middleware
from starlette.middleware.sessions import SessionMiddleware
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security: Load secret key from environment
SECRET_KEY = os.getenv("SESSION_MIDDLEWARE_SECRET_KEY", "dev_not_secure_key")


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
        ft.Link(
            href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css",
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
        ft.Script(src="/public/js/card-modal.js"),
        ft.Script(src="/public/js/decklist-modal.js"),
    ],
    #static_path='public'
)

# Add session middleware for authentication
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Sitemap works reliably 
@rt("/sitemap.xml")
async def serve_sitemap():
    return FileResponse("public/sitemap.xml", media_type="application/xml")



# Setup API routes
setup_api_routes(rt)
setup_auth_routes(rt)
setup_settings_routes(rt)

@rt("/api/cache/status")
def cache_status():
    """Get cache warmer status"""
    from op_tcg.frontend.utils.cache_warmer import get_cache_warmer
    warmer = get_cache_warmer()
    return {
        "is_running": warmer.is_running,
        "warm_interval_hours": warmer.warm_interval_hours
    }

@rt("/api/cache/stats")
def cache_stats():
    """Get cache performance statistics"""
    from op_tcg.frontend.utils.cache_monitor import get_cache_summary
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
        from op_tcg.frontend.utils.cache import clear_all_caches
        clear_all_caches()
        return {"status": "success", "message": "All caches cleared"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.middleware("http")
async def enforce_canonical_host(request, call_next):
    return await canonical_redirect_middleware(request, call_next)

def _user_setting_defaults(request: Request) -> dict:
    """Return the logged-in user's saved settings, or empty dict if not logged in / no settings."""
    user = request.session.get('user')
    if not user:
        return {}
    try:
        return get_user_settings(user['sub']) or {}
    except Exception:
        return {}


def _region_for_url(region: str | None) -> str | None:
    """Return region only when it is a non-default, non-neutral value worth encoding in a URL."""
    if not region or region == MetaFormatRegion.ALL:
        return None
    return region


@rt("/")
def home(request: Request):
    # Add canonical link to head for home page using incoming host
    canonical_url = canonical_base(request)
    title = "OP TCG Leaderboard – Meta, Decklists, Prices & Matchups"
    description = "Track One Piece TCG leaders, meta trends, decklists, prices, and matchups. Updated regularly with official and community results."
    # Determine selected values for filters (query param > user setting > code default)
    user_defaults = _user_setting_defaults(request)
    selected_meta_format = request.query_params.get("meta_format")
    selected_region = request.query_params.get("region") or user_defaults.get("region")

    persist_query = {
        "meta_format": selected_meta_format,
        "region": _region_for_url(selected_region),
    }
    selected_meta_format_enum = MetaFormat(selected_meta_format) if selected_meta_format else None
    selected_region_enum = MetaFormatRegion(selected_region) if selected_region else None

    user = request.session.get('user')
    flash = request.session.pop('flash', None)

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
            persist_query=persist_query,
            user=user,
            flash=flash,
        )
    )



@rt("/leader")
def leader_default(request: Request):
    # Get selected meta formats from query params (can be multiple)
    user_defaults = _user_setting_defaults(request)
    selected_meta_format = request.query_params.getlist("meta_format")
    leader_id = request.query_params.get("lid")
    selected_region_str = request.query_params.get("region") or user_defaults.get("region")

    # Convert to MetaFormat enum if present
    if selected_meta_format:
        selected_meta_format = [MetaFormat(mf) for mf in selected_meta_format]

    # Convert to MetaFormatRegion enum if present
    selected_meta_format_region = MetaFormatRegion(selected_region_str) if selected_region_str else None

    # Add canonical link to head based on incoming host
    canonical_url = f"{canonical_base(request)}/leader"
    title = "Leader Meta & Performance – OP TCG Leaderboard"
    description = "Explore leader performance across formats, with meta share, win rates, and top decklists."

    persist_query = {
        "meta_format": request.query_params.get("meta_format"),
        "region": _region_for_url(selected_region_str),
    }

    user = request.session.get('user')

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
            persist_query=persist_query,
            user=user
        )
    )

@rt("/tournaments")
def tournaments(request: Request):
    # Add canonical link to head based on incoming host
    canonical_url = f"{canonical_base(request)}/tournaments"
    title = "Tournaments – Results & Decklists – OP TCG Leaderboard"
    description = "Browse tournament results, standings, and decklists across regions and formats."
    
    # Parse selections (query param > user setting > code default)
    user_defaults = _user_setting_defaults(request)
    selected_meta_formats = request.query_params.getlist("meta_format")
    selected_meta_formats = [MetaFormat(mf) for mf in selected_meta_formats] if selected_meta_formats else None
    selected_region = request.query_params.get("region") or user_defaults.get("region")
    selected_region_enum = MetaFormatRegion(selected_region) if selected_region else None

    persist_query = {
        "meta_format": request.query_params.get("meta_format"),
        "region": _region_for_url(selected_region),
    }

    user = request.session.get('user')

    return (
        ft.Title(title),
        ft.Meta(name="description", content=description),
        ft.Meta(property="og:title", content=title),
        ft.Meta(property="og:description", content=description),
        ft.Meta(property="og:url", content=canonical_url),
        ft.Link(rel="canonical", href=canonical_url),
        # Shared deep-linking functionality for decklist modals
        create_decklist_deep_link_script(),
        layout(tournaments_page(), filter_component=tournament_filters(selected_meta_formats=selected_meta_formats, selected_region=selected_region_enum), current_path="/tournaments", persist_query=persist_query, user=user)
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
    
    user_defaults = _user_setting_defaults(request)
    persist_query = {
        "meta_format": request.query_params.get("meta_format"),
        "region": _region_for_url(request.query_params.get("region") or user_defaults.get("region")),
    }

    user = request.session.get('user')

    return (
        ft.Title(title),
        ft.Meta(name="description", content=description),
        ft.Meta(property="og:title", content=title),
        ft.Meta(property="og:description", content=description),
        ft.Meta(property="og:url", content=canonical_url),
        ft.Link(rel="canonical", href=canonical_url),
        layout(card_movement_page(), filter_component=card_movement_filters(selected_meta_format=selected_meta_format, selected_leader_id=selected_leader_id), current_path="/card-movement", persist_query=persist_query, user=user)
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
    
    user_defaults = _user_setting_defaults(request)
    persist_query = {
        "meta_format": request.query_params.get("meta_format"),
        "region": _region_for_url(request.query_params.get("region") or user_defaults.get("region")),
    }

    user = request.session.get('user')

    return (
        ft.Title(title),
        ft.Meta(name="description", content=description),
        ft.Meta(property="og:title", content=title),
        ft.Meta(property="og:description", content=description),
        ft.Meta(property="og:url", content=canonical_url),
        ft.Link(rel="canonical", href=canonical_url),
        layout(matchups_page(), filter_component=matchups_filters(selected_meta_formats=selected_meta_formats, selected_leader_ids=selected_leader_ids, only_official=only_official), current_path="/matchups", persist_query=persist_query, user=user)
    )

# Card pages
@rt("/card-popularity")
def card_popularity(request: Request):
    # Add canonical link to head based on incoming host
    canonical_url = f"{canonical_base(request)}/card-popularity"
    title = "Card Popularity – Usage & Trends – OP TCG Leaderboard"
    description = "Discover the most played cards and shifting usage trends across formats and leaders."
    
    # Parse selections (query param > user setting > code default)
    user_defaults = _user_setting_defaults(request)
    persist_query = {
        "meta_format": request.query_params.get("meta_format"),
        "region": _region_for_url(request.query_params.get("region") or user_defaults.get("region")),
    }
    selected_meta_format = request.query_params.get("meta_format")
    selected_meta_format_enum = MetaFormat(selected_meta_format) if selected_meta_format else None
    selected_currency = request.query_params.get("currency") or user_defaults.get("currency")
    selected_currency_enum = CardCurrency(selected_currency) if selected_currency else None

    user = request.session.get('user')

    return (
        ft.Title(title),
        ft.Meta(name="description", content=description),
        ft.Meta(property="og:title", content=title),
        ft.Meta(property="og:description", content=description),
        ft.Meta(property="og:url", content=canonical_url),
        ft.Link(rel="canonical", href=canonical_url),
        layout(card_popularity_page(), filter_component=card_popularity_filters(selected_meta_format=selected_meta_format_enum, currency=selected_currency_enum), current_path="/card-popularity", persist_query=persist_query, user=user)
    )

# Prices page
@rt("/card-prices")
def prices(request: Request):
    canonical_url = f"{canonical_base(request)}/prices"
    title = "Card Prices – Market Trends – OP TCG Leaderboard"
    description = "See current OP TCG card prices and market movement with historical trends."

    user_defaults = _user_setting_defaults(request)
    selected_currency = request.query_params.get("currency") or user_defaults.get("currency")
    selected_currency_enum = CardCurrency(selected_currency) if selected_currency else CardCurrency.EURO

    user = request.session.get('user')

    return (
        ft.Title(title),
        ft.Meta(name="description", content=description),
        ft.Meta(property="og:title", content=title),
        ft.Meta(property="og:description", content=description),
        ft.Meta(property="og:url", content=canonical_url),
        ft.Link(rel="canonical", href=canonical_url),
        layout(prices_page(), filter_component=prices_filters(selected_currency=selected_currency_enum), current_path="/prices", user=user)
    )

# Support pages
@rt("/bug-report")
def bug_report(request: Request):
    # Add canonical link to head based on incoming host
    canonical_url = f"{canonical_base(request)}/bug-report"
    title = "Report a Bug – OP TCG Leaderboard"
    description = "Spotted an issue? Report bugs and help us improve OP TCG Leaderboard."
    
    user_defaults = _user_setting_defaults(request)
    persist_query = {
        "meta_format": request.query_params.get("meta_format"),
        "region": _region_for_url(request.query_params.get("region") or user_defaults.get("region")),
    }

    user = request.session.get('user')

    return (
        ft.Title(title),
        ft.Meta(name="description", content=description),
        ft.Meta(property="og:title", content=title),
        ft.Meta(property="og:description", content=description),
        ft.Meta(property="og:url", content=canonical_url),
        ft.Link(rel="canonical", href=canonical_url),
        layout(bug_report_page(), filter_component=None, current_path="/bug-report", persist_query=persist_query, user=user)
    )

@rt("/about")
def about(request: Request):
    # Add canonical link to head based on incoming host
    canonical_url = f"{canonical_base(request)}/about"
    title = "About – OP TCG Leaderboard"
    description = "About the OP TCG Leaderboard project."

    user_defaults = _user_setting_defaults(request)
    persist_query = {
        "meta_format": request.query_params.get("meta_format"),
        "region": _region_for_url(request.query_params.get("region") or user_defaults.get("region")),
    }

    user = request.session.get('user')

    return (
        ft.Title(title),
        ft.Meta(name="description", content=description),
        ft.Meta(property="og:title", content=title),
        ft.Meta(property="og:description", content=description),
        ft.Meta(property="og:url", content=canonical_url),
        ft.Link(rel="canonical", href=canonical_url),
        layout(about_page(), filter_component=None, current_path="/about", persist_query=persist_query, user=user)
    )

@rt("/privacy")
def privacy(request: Request):
    canonical_url = f"{canonical_base(request)}/privacy"
    title = "Privacy Policy – OP TCG Leaderboard"
    description = "Privacy policy for OP TCG Leaderboard, covering data collection, Google OAuth, and your rights."

    user = request.session.get('user')

    return (
        ft.Title(title),
        ft.Meta(name="description", content=description),
        ft.Meta(property="og:title", content=title),
        ft.Meta(property="og:description", content=description),
        ft.Meta(property="og:url", content=canonical_url),
        ft.Link(rel="canonical", href=canonical_url),
        layout(privacy_page(), filter_component=None, current_path="/privacy", user=user)
    )

@rt("/watchlist")
def watchlist_route(request: Request):
    user = request.session.get('user')
    if not user:
        return ft.RedirectResponse(url="/login")

    # Add canonical link to head based on incoming host
    canonical_url = f"{canonical_base(request)}/watchlist"
    title = "My Watchlist – OP TCG Leaderboard"
    description = "View and manage your tracked One Piece TCG cards."

    return (
        ft.Title(title),
        ft.Meta(name="description", content=description),
        ft.Link(rel="canonical", href=canonical_url),
        layout(
            watchlist_page(request),
            current_path="/watchlist",
            user=user
        )
    )

@rt("/register")
def register(request: Request):
    pending = request.session.get('pending_registration')
    if not pending:
        return RedirectResponse(url='/', status_code=302)
    return (
        ft.Title("Create Account – OP TCG Leaderboard"),
        layout(
            register_content(pending_user=pending, csrf_token=get_csrf_token(request.session)),
            current_path="/register",
        )
    )


@rt("/settings")
def settings(request: Request):
    user = request.session.get('user')
    canonical_url = f"{canonical_base(request)}/settings"
    title = "Settings – OP TCG Leaderboard"
    description = "Manage your account settings and preferences."

    return (
        ft.Title(title),
        ft.Meta(name="description", content=description),
        ft.Link(rel="canonical", href=canonical_url),
        layout(
            settings_content(user=user, csrf_token=get_csrf_token(request.session)),
            current_path="/settings",
            user=user
        )
    )


if __name__ == "__main__":
    # Start background tasks
    serve()
