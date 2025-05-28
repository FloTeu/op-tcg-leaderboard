from fasthtml import ft
from op_tcg.backend.models.input import MetaFormat
from op_tcg.frontend_fasthtml.components.loading import create_loading_spinner
from op_tcg.frontend_fasthtml.components.filters import create_leader_select_component

# Common CSS classes for select components
SELECT_CLS = "w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"

# Common HTMX attributes for filter components
HX_INCLUDE = "[name='meta_format'],[name='leader_id']"

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
        **{
            "hx_get": "/api/leader-select-generic",
            "hx_trigger": "change",
            "hx_target": "#leader-select-wrapper",
            "hx_include": HX_INCLUDE,
            "hx_indicator": "#card-movement-loading-indicator",
            "hx_vals": '{"select_name": "leader_id", "label": "Leader Card", "wrapper_id": "leader-select-wrapper", "select_id": "leader-select"}'
        }
    )
    
    # Leader select wrapper - create initial component without HTMX attrs
    # HTMX attrs will be added after the component is updated via meta format change
    leader_select_wrapper = ft.Div(
        create_leader_select_component(
            selected_meta_formats=[latest_meta],
            select_name="leader_id",
            label="Leader Card",
            wrapper_id="leader-select-wrapper",
            select_id="leader-select",
            # Don't add HTMX attrs here - they'll be added via JavaScript after updates
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
        
        # Main content area with initial load trigger
        ft.Div(
            ft.Div(
                ft.P("Loading card movement analysis...", cls="text-gray-300 text-center"),
                cls="text-center py-12"
            ),
            id="card-movement-content",
            cls="mt-8"
        ),
        
        # JavaScript to handle interactions and HTMX setup
        ft.Script("""
            // Function to add HTMX attributes to leader select
            function setupLeaderSelectHTMX() {
                const leaderSelect = document.getElementById('leader-select');
                if (leaderSelect) {
                    // Add HTMX attributes for content loading
                    leaderSelect.setAttribute('hx-get', '/api/card-movement-content');
                    leaderSelect.setAttribute('hx-trigger', 'change');
                    leaderSelect.setAttribute('hx-target', '#card-movement-content');
                    leaderSelect.setAttribute('hx-include', '[name="meta_format"],[name="leader_id"]');
                    leaderSelect.setAttribute('hx-indicator', '#card-movement-loading-indicator');
                    
                    // Process the new HTMX attributes
                    if (window.htmx) {
                        htmx.process(leaderSelect);
                    }
                }
            }
            
            // Function to trigger content load
            function loadContent() {
                const leaderSelect = document.getElementById('leader-select');
                if (leaderSelect && leaderSelect.value && leaderSelect.value !== '') {
                    // Trigger content load
                    if (window.htmx) {
                        htmx.ajax('GET', '/api/card-movement-content', {
                            target: '#card-movement-content',
                            source: leaderSelect,
                            indicator: '#card-movement-loading-indicator'
                        });
                    }
                }
            }
            
            document.addEventListener('DOMContentLoaded', function() {
                // Setup initial HTMX attributes
                setupLeaderSelectHTMX();
                
                // Load initial content
                setTimeout(function() {
                    loadContent();
                }, 100);
                
                // Trigger initial load of leader select
                setTimeout(function() {
                    const metaSelect = document.getElementById('meta-format-select');
                    if (metaSelect) {
                        htmx.trigger(metaSelect, 'change');
                    }
                }, 200);
            });
            
            // Handle leader select updates after meta format changes
            document.body.addEventListener('htmx:afterSettle', function(evt) {
                if (evt.target.id === 'leader-select-wrapper') {
                    // Re-setup HTMX attributes for the new leader dropdown
                    setupLeaderSelectHTMX();
                    
                    // Re-initialize styled select for the new leader dropdown
                    const leaderSelect = document.getElementById('leader-select');
                    if (leaderSelect && window.initializeSelect) {
                        window.initializeSelect('leader-select');
                    }
                    
                    // Load content with the selected leader (preserve selection or use new top leader)
                    setTimeout(function() {
                        loadContent();
                    }, 50);
                }
            });
        """),
        
        cls="min-h-screen"
    ) 