from fasthtml import ft
from op_tcg.frontend.components.sidebar import sidebar

def layout(content, filter_component=None, current_path="/", persist_query=None):
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
            ft.H3("Filters", cls="px-4 py-2 text-sm font-semibold text-gray-400 uppercase"),
            filter_component,
            cls="mt-6"
        )

    # Main layout
    return ft.Div(
        # Include external CSS files
        ft.Link(rel="stylesheet", href="public/css/leaderboard.css"),
        
        # Top bar that appears when sidebar is collapsed
        ft.Div(
            ft.Div(
                ft.Button(
                    ft.Div(
                        ft.Div(cls="w-6 h-0.5 bg-white mb-1.5 transition-all duration-300"),
                        ft.Div(cls="w-6 h-0.5 bg-white mb-1.5 transition-all duration-300"),
                        ft.Div(cls="w-6 h-0.5 bg-white transition-all duration-300"),
                        cls="flex flex-col justify-center items-center"
                    ),
                    cls="text-white hover:bg-gray-700 z-50 bg-gray-800 rounded-md p-2",
                    onclick="toggleSidebar()",
                    id="burger-menu"
                ),
                cls="flex items-center h-16 px-4"
            ),
            cls="fixed top-0 left-0 right-0 bg-gray-900 z-40 shadow-md",
            id="top-bar",
            style="display: block;"  # Start with top bar visible (mobile state)
        ),
        sidebar(filter_component, current_path, persist_query),
        ft.Div(
            content,
            cls="p-4 min-h-screen bg-gray-900 transition-all duration-300 ease-in-out mt-16 relative",
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
                    if (p.meta_format_region) params.set('region', p.meta_format_region); else params.delete('region');
                    // carry one meta_format for cross-page consistency
                    if (p.meta_format) params.set('meta_format', p.meta_format); else params.delete('meta_format');
                } else {
                    // On non-leader pages, prefer standard region, but fall back to leader's meta_format_region
                    const effRegion = p.region || p.meta_format_region;
                    if (effRegion) params.set('region', effRegion); else params.delete('region');
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
                            if (p.region || p.meta_format_region) qp.set('region', p.meta_format_region || p.region);
                        } else {
                            if (p.meta_format) qp.set('meta_format', p.meta_format);
                            const effRegion = p.region || p.meta_format_region;
                            if (effRegion) qp.set('region', effRegion);
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
        cls="relative bg-gray-900"
    ) 