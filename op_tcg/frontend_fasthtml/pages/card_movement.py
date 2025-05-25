from fasthtml import ft
from op_tcg.backend.models.input import MetaFormat
from op_tcg.frontend_fasthtml.components.loading import create_loading_spinner

# Common CSS classes for select components
SELECT_CLS = "w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"

# Common HTMX attributes for filter components
HX_INCLUDE = "[name='meta_format'],[name='leader_id']"
FILTER_HX_ATTRS = {
    "hx_get": "/api/card-movement-leader-select",
    "hx_trigger": "change",
    "hx_target": "#leader-select-wrapper",
    "hx_include": HX_INCLUDE,
    "hx_indicator": "#card-movement-loading-indicator"
}

def create_filter_components():
    """Create filter components for the card movement page"""
    latest_meta = MetaFormat.latest_meta_format()
    
    # Meta format select
    meta_format_select = ft.Select(
        label="Current Meta Format",
        id="meta-format-select",
        name="meta_format",
        cls=SELECT_CLS + " styled-select",
        *[ft.Option(mf, value=mf, selected=mf == latest_meta) for mf in reversed(MetaFormat.to_list())],
        **FILTER_HX_ATTRS
    )
    
    # Leader select wrapper (will be populated via HTMX)
    leader_select_wrapper = ft.Div(
        ft.Label("Leader Card", cls="text-white font-medium block mb-2"),
        ft.Select(
            ft.Option("Select a leader...", value="", selected=True),
            id="leader-select",
            name="leader_id",
            cls=SELECT_CLS + " styled-select",
            **{
                "hx_get": "/api/card-movement-content",
                "hx_trigger": "change",
                "hx_target": "#card-movement-content",
                "hx_include": HX_INCLUDE,
                "hx_indicator": "#card-movement-loading-indicator"
            }
        ),
        id="leader-select-wrapper"
    )
    
    return ft.Div(
        meta_format_select,
        leader_select_wrapper,
        cls="space-y-4"
    )

def card_movement_page():
    """Create the card movement page with filters and content area"""
    return ft.Div(
        ft.H1("Card Movement", cls="text-3xl font-bold text-white mb-6"),
        ft.P("Track price changes of leader cards between meta formats.", cls="text-gray-300 mb-8"),
        
        # Loading indicator
        ft.Div(
            create_loading_spinner(),
            id="card-movement-loading-indicator",
            cls="htmx-indicator"
        ),
        
        # Main content area
        ft.Div(
            ft.Div(
                ft.P("Select a meta format and leader to view price movement analysis.", cls="text-gray-300 text-center"),
                cls="text-center py-12"
            ),
            id="card-movement-content",
            cls="mt-8"
        ),
        
        # Initialize leader select on page load
        ft.Script("""
            document.addEventListener('DOMContentLoaded', function() {
                // Wait for HTMX to be ready
                setTimeout(function() {
                    // Trigger initial load of leader select
                    const metaSelect = document.getElementById('meta-format-select');
                    if (metaSelect) {
                        htmx.trigger(metaSelect, 'change');
                    }
                }, 100);
            });
            
            // Also trigger when HTMX settles after any content swap
            document.body.addEventListener('htmx:afterSettle', function(evt) {
                if (evt.target.id === 'leader-select-wrapper') {
                    // Re-initialize styled select for the new leader dropdown
                    const leaderSelect = document.getElementById('leader-select');
                    if (leaderSelect && window.initializeSelect) {
                        window.initializeSelect('leader-select');
                    }
                }
            });
        """),
        
        cls="min-h-screen"
    ) 