from typing import Any

from fasthtml import ft
from op_tcg.frontend.components.sidebar import sidebar

_FLASH_BG = {
    "error": "bg-red-600",
    "success": "bg-green-600",
    "info": "bg-blue-600",
    "warning": "bg-yellow-500",
}

def _flash_toast(flash):
    if not flash:
        return None
    bg = _FLASH_BG.get(flash.get("type", "info"), "bg-blue-600")
    return ft.Div(
        ft.Div(
            ft.Span(flash["message"], cls="flex-1 text-sm"),
            ft.Button(
                "×",
                onclick="this.closest('#flash-toast').remove()",
                cls="ml-4 text-xl font-bold leading-none opacity-70 hover:opacity-100 cursor-pointer",
                type="button"
            ),
            cls=f"flex items-center {bg} text-white font-medium px-4 py-3 rounded-lg shadow-lg"
        ),
        ft.Script("setTimeout(function(){var t=document.getElementById('flash-toast');if(t)t.remove();},5000);"),
        cls="fixed top-20 right-4 z-50 max-w-sm w-full",
        id="flash-toast"
    )

def create_mobile_filter_button():
    """Create a button to toggle the sidebar on mobile devices."""
    return ft.Button(
        "Show Filters",
        type="button",
        cls="mobile-filter-btn md:hidden hide-on-sidebar-open text-sm text-gray-400 hover:text-white border border-gray-700 hover:border-gray-500 rounded-full px-4 py-2 transition-colors mb-8 relative z-10 cursor-pointer"
    )

def layout(content, filter_component=None, current_path="/", persist_query=None, user=None, flash=None):
    """
    Main layout component that includes the sidebar navigation and content area.
    
    Args:
        content: The main content to display
        filter_component: Optional filter component to show in the sidebar
        current_path: The current path of the page, used for highlighting active navigation items
    """
    
    # Create filter section if filter component is provided
    filter_section = None
    if filter_component:
        filter_section = ft.Div(
            ft.H3("Filters", style="font-family:'Bebas Neue',sans-serif;color:#475569;letter-spacing:.12em;font-size:.72rem;padding:6px 14px 4px;"),
            filter_component,
            cls="mt-6"
        )

    # Main layout
    if user:
        user_control = get_user_control_view(user, current_path)
    else:
        login_next = current_path if current_path and current_path != "/login" else "/"
        user_control = ft.A(
            ft.I(cls="fas fa-sign-in-alt mr-2"),
            "Sign In",
            href=f"/login?next={login_next}",
            cls="flex items-center rounded-lg px-4 py-2",
            style="background:#f59e0b;color:#000;font-family:'Bebas Neue',sans-serif;letter-spacing:.1em;font-size:.85rem;text-decoration:none;transition:background .12s,transform .1s;",
            onmouseover="this.style.background='#fbbf24';this.style.transform='translateY(-1px)'",
            onmouseout="this.style.background='#f59e0b';this.style.transform=''",
        )

    return ft.Div(
        # Include external CSS files
        ft.Link(rel="stylesheet", href="public/css/leaderboard.css"),
        # Synchronous script — runs before first paint so the sidebar appears in its correct
        # open/closed state with no slide-in animation on every page navigation.
        ft.Script("""(function(){try{var s=sessionStorage.getItem('sidebarOpen');var m=window.innerWidth<=768;if(!m&&s!=='false')document.documentElement.classList.add('sidebar-initially-open');}catch(e){}})();"""),
        
        # Top bar that appears when sidebar is collapsed
        ft.Div(
            ft.Div(
                ft.Button(
                    ft.Div(
                        ft.Div(style="width:20px;height:2px;background:#94a3b8;margin-bottom:5px;border-radius:1px;"),
                        ft.Div(style="width:20px;height:2px;background:#94a3b8;margin-bottom:5px;border-radius:1px;"),
                        ft.Div(style="width:20px;height:2px;background:#94a3b8;border-radius:1px;"),
                        style="display:flex;flex-direction:column;justify-content:center;align-items:center;",
                    ),
                    style="background:#1a2540;border:none;border-radius:6px;padding:8px;cursor:pointer;transition:background .15s;",
                    onmouseover="this.style.background='#2d3f5a'",
                    onmouseout="this.style.background='#1a2540'",
                    onclick="toggleSidebar()",
                    id="burger-menu",
                ),
                user_control,
                cls="flex justify-between items-center h-16 px-4"
            ),
            cls="fixed top-0 left-0 right-0 bg-deep-navy z-40 shadow-md",
            id="top-bar",
            style="display: block;"  # Start with top bar visible (mobile state)
        ),
        _flash_toast(flash),
        sidebar(filter_component, current_path, persist_query),
        ft.Div(
            content,
            ft.Footer(
                ft.Div(
                    ft.A("About", href="/about", style="color:#475569;font-size:.875rem;transition:color .15s;font-family:'Barlow',sans-serif;", onmouseover="this.style.color='#94a3b8'", onmouseout="this.style.color='#475569'"),
                    ft.A("Bug Report", href="/bug-report", style="color:#475569;font-size:.875rem;transition:color .15s;font-family:'Barlow',sans-serif;", onmouseover="this.style.color='#94a3b8'", onmouseout="this.style.color='#475569'"),
                    ft.A("Privacy Policy", href="/privacy", style="color:#475569;font-size:.875rem;transition:color .15s;font-family:'Barlow',sans-serif;", onmouseover="this.style.color='#94a3b8'", onmouseout="this.style.color='#475569'"),
                    ft.Span("© 2026 OP TCG Leaderboard", style="color:#334155;font-size:.875rem;font-family:'Barlow',sans-serif;"),
                    cls="flex flex-wrap items-center gap-6 justify-center"
                ),
                style="border-top:1px solid #1a2540;margin-top:64px;padding:32px 16px;",
            ),
            cls="p-4 min-h-screen bg-deep-navy transition-all duration-300 ease-in-out mt-16 relative",
            id="main-content",
            style="margin-left: 0;"  # Start with no left margin (mobile state)
        ),
        # Script to keep URL and sidebar links in sync with active filters
        ft.Script("""
            function getFilterParams() {
                const params = new URLSearchParams(window.location.search);
                // meta_format (prefer element value)
                let metaFormat = null;
                const mfEl = document.querySelector('[name="meta_format"]');
                if (mfEl) {
                    if (mfEl.multiple) {
                        const sel = Array.from(mfEl.selectedOptions).map(o => o.value).filter(Boolean);
                        if (sel.length > 0) metaFormat = sel[0];
                    } else {
                        metaFormat = mfEl.value || null;
                    }
                }
                if (!metaFormat) metaFormat = params.get('meta_format');
                // region (home and others)
                let region = null;
                const rEl = document.querySelector('[name="region"]');
                if (rEl) region = rEl.value || null;
                if (!region) region = params.get('region');
                // leader page region
                let metaFormatRegion = null;
                const rLeaderEl = document.querySelector('[name="region"]');
                if (rLeaderEl) metaFormatRegion = rLeaderEl.value || null;
                if (!metaFormatRegion) metaFormatRegion = params.get('region');
                // lid passthrough if present in URL
                const lid = params.get('lid');
                return { meta_format: metaFormat, region: region, meta_format_region: metaFormatRegion, lid: lid };
            }
            function updateCurrentURL() {
                const p = getFilterParams();
                const path = window.location.pathname;
                const params = new URLSearchParams(window.location.search);
                if (path === '/leader') {
                    // Keep lid if present
                    if (p.lid) params.set('lid', p.lid); else params.delete('lid');
                    const effRegionL = p.meta_format_region || p.region;
                    if (effRegionL && effRegionL !== 'all') params.set('region', effRegionL); else params.delete('region');
                    // carry one meta_format for cross-page consistency
                    if (p.meta_format) params.set('meta_format', p.meta_format); else params.delete('meta_format');
                } else {
                    // On non-leader pages, prefer standard region, but fall back to leader's meta_format_region
                    const effRegion = p.region || p.meta_format_region;
                    if (effRegion && effRegion !== 'all') params.set('region', effRegion); else params.delete('region');
                    if (p.meta_format) params.set('meta_format', p.meta_format); else params.delete('meta_format');
                }
                const newURL = path + (params.toString() ? '?' + params.toString() : '');
                window.history.replaceState({}, '', newURL);
            }
            function updateSidebarLinks() {
                const p = getFilterParams();
                const links = document.querySelectorAll('#sidebar a[href]');
                links.forEach(a => {
                    try {
                        const url = new URL(a.href, window.location.origin);
                        const basePath = url.pathname; // ignore existing query; rebuild
                        const qp = new URLSearchParams();
                        if (basePath === '/leader') {
                            if (p.meta_format) qp.set('meta_format', p.meta_format);
                            const effRegionL = p.meta_format_region || p.region;
                            if (effRegionL && effRegionL !== 'all') qp.set('region', effRegionL);
                        } else {
                            if (p.meta_format) qp.set('meta_format', p.meta_format);
                            const effRegion = p.region || p.meta_format_region;
                            if (effRegion && effRegion !== 'all') qp.set('region', effRegion);
                        }
                        a.href = basePath + (qp.toString() ? '?' + qp.toString() : '');
                    } catch (e) { /* no-op */ }
                });
            }
            function bindFilterSync() {
                const handler = () => { setTimeout(() => { updateCurrentURL(); updateSidebarLinks(); }, 50); };
                document.addEventListener('change', function(evt){
                    if (evt.target && (evt.target.matches('[name="meta_format"], [name="region"]'))) {
                        handler();
                    }
                });
                document.addEventListener('htmx:afterSettle', handler);
                handler();
            }
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', bindFilterSync);
            } else {
                bindFilterSync();
            }
        """),
        cls="relative bg-deep-navy"
    )


def get_user_control_view(user, current_path: str = "/") -> Any:
    user_name = user.get('name', 'User')
    user_img = user.get('picture', None)

    user_control = ft.Div(
        ft.Button(
            ft.Img(src=user_img, cls="w-8 h-8 rounded-full") if user_img else \
                ft.Div(user_name[0].upper(),
                       style="width:32px;height:32px;border-radius:50%;background:rgba(245,158,11,.2);border:1px solid rgba(245,158,11,.4);display:flex;align-items:center;justify-content:center;color:#f59e0b;font-family:'Barlow',sans-serif;font-weight:600;"),
            id="user-menu-button",
            onclick="var d=document.getElementById('user-dropdown');d.style.display=d.style.display==='block'?'none':'block';",
            style="display:flex;background:transparent;border:none;cursor:pointer;border-radius:50%;padding:0;",
            type="button"
        ),
        ft.Div(
            ft.Div(
                ft.Div(user_name, style="padding:12px 16px 4px;font-size:.875rem;color:#f1f5f9;font-family:'Barlow',sans-serif;font-weight:600;"),
                ft.Div(user.get('email', ''), style="padding:0 16px 12px;font-size:.75rem;color:#475569;font-family:'Barlow',sans-serif;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"),
                style="border-bottom:1px solid #1a2540;"
            ),
            ft.Ul(
                ft.Li(ft.A("Watchlist", href="/watchlist", style="display:block;padding:8px 16px;font-size:.875rem;color:#94a3b8;font-family:'Barlow',sans-serif;transition:background .12s,color .12s;", onmouseover="this.style.background='rgba(245,158,11,.08)';this.style.color='#f1f5f9'", onmouseout="this.style.background='';this.style.color='#94a3b8'")),
                ft.Li(ft.A("Settings", href="/settings", style="display:block;padding:8px 16px;font-size:.875rem;color:#94a3b8;font-family:'Barlow',sans-serif;transition:background .12s,color .12s;", onmouseover="this.style.background='rgba(245,158,11,.08)';this.style.color='#f1f5f9'", onmouseout="this.style.background='';this.style.color='#94a3b8'")),
                ft.Li(ft.A("Logout", href=f"/logout?next={current_path}", style="display:block;padding:8px 16px;font-size:.875rem;color:#94a3b8;font-family:'Barlow',sans-serif;transition:background .12s,color .12s;", onmouseover="this.style.background='rgba(239,68,68,.08)';this.style.color='#ef4444'", onmouseout="this.style.background='';this.style.color='#94a3b8'")),
                style="padding:6px 0;list-style:none;margin:0;"
            ),
            style="z-index:50;display:none;position:absolute;right:0;margin-top:8px;width:200px;background:#0d1424;border:1px solid #1a2540;border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,0.5);overflow:hidden;",
            id="user-dropdown"
        ),
        # Click outside to close (simple implementation)
        ft.Script("""
                window.addEventListener('click', function(e){
                    const dropdown = document.getElementById('user-dropdown');
                    const button = document.getElementById('user-menu-button');
                    // Check if click is outside dropdown AND outside button
                    if (dropdown && button && !dropdown.contains(e.target) && !button.contains(e.target) && dropdown.style.display === 'block') {
                        dropdown.style.display = 'none';
                    }
                });
            """),
        cls="relative"
    )
    return user_control