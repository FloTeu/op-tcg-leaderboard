from fasthtml import ft

from op_tcg.backend.models.cards import CardCurrency
from op_tcg.backend.models.input import MetaFormat
from op_tcg.frontend.components.loading import create_loading_spinner
from op_tcg.frontend.components.filters import create_leader_select_component
from op_tcg.frontend.utils.extract import get_leader_extended
from typing import List, Dict
from pydantic import BaseModel

# Common CSS classes for select components
SELECT_CLS = "w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"

# Common HTMX attributes for filter components
HX_INCLUDE = "[name='meta_format'],[name='leader_id']"
FILTER_HX_ATTRS = {
    "hx_get": "/api/card-movement-content",
    "hx_trigger": "change",
    "hx_target": "#card-movement-content",
    "hx_include": HX_INCLUDE,
    "hx_indicator": "#card-movement-loading-indicator"
}

class CardFrequencyChange(BaseModel):
    """Data class for tracking card frequency changes between meta formats"""
    card_id: str
    card_name: str
    card_image_url: str
    current_frequency: float  # 0.0 to 1.0
    previous_frequency: float  # 0.0 to 1.0
    frequency_change: float  # difference in percentage points
    current_avg_count: float  # average copies in deck
    previous_avg_count: float  # average copies in deck
    change_type: str  # "increased", "decreased", "new", "disappeared", "stable"

def create_filter_components(selected_meta_format=None, selected_leader_id=None):
    """Create filter components for the card movement page using HTMX and API routes"""
    latest_meta = MetaFormat.latest_meta_format()
    
    # If no selected format provided, default to latest
    if not selected_meta_format:
        selected_meta_format = latest_meta
    
    # Meta format select
    meta_format_select = ft.Select(
        label="Current Meta Format",
        id="meta-format-select",
        name="meta_format",
        cls=SELECT_CLS + " styled-select",
        *[ft.Option(mf, value=mf, selected=mf == selected_meta_format) for mf in reversed(MetaFormat.to_list())],
        **{
            "hx_get": "/api/leader-select-generic",
            "hx_target": "#leader-select-wrapper",
            "hx_include": HX_INCLUDE,
            "hx_trigger": "change",
            "hx_swap": "innerHTML",
            "hx_params": "*",
            "hx_vals": '{"select_name": "leader_id", "label": "Leader Card", "wrapper_id": "leader-select-wrapper", "select_id": "leader-select", "auto_select_top": "true"}'
        }
    )

    # Add a hidden div that will trigger the content update
    content_trigger = ft.Div(
        id="content-trigger",
        **FILTER_HX_ATTRS,
        style="display: none;"
    )

    # Add JavaScript to trigger the content update after leader select is updated
    trigger_script = ft.Script("""
        document.addEventListener('htmx:afterSettle', function(evt) {
            if (evt.target.id === 'leader-select-wrapper') {
                // Trigger content update after leader select is ready
                htmx.trigger('#content-trigger', 'change');
            }
        });
        
        // Also trigger initial load if we have default leader selections
        document.addEventListener('DOMContentLoaded', function() {
            // Small delay to ensure all elements are ready
            setTimeout(function() {
                const leaderSelect = document.querySelector('[name="leader_id"]');
                if (leaderSelect && leaderSelect.value) {
                    htmx.trigger('#content-trigger', 'change');
                }
            }, 100);
        });
    """)

    # Leader select wrapper with initial content loaded via HTMX
    leader_select_wrapper = ft.Div(
        # Initial loading spinner
        create_loading_spinner(
            id="leader-select-loading",
            size="w-6 h-6",
            container_classes="min-h-[60px]"
        ),
        # Load the initial component via HTMX
        hx_get="/api/leader-select-generic",
        hx_trigger="load",
        hx_include=HX_INCLUDE,
        hx_target="this",
        hx_swap="innerHTML",
        hx_indicator="#leader-select-loading",
        hx_vals='{"select_name": "leader_id", "label": "Leader Card", "wrapper_id": "leader-select-wrapper", "select_id": "leader-select", "auto_select_top": "true"}',
        id="leader-select-wrapper",
        cls="relative"
    )

    return ft.Div(
        meta_format_select,
        leader_select_wrapper,
        content_trigger,
        trigger_script,
        cls="space-y-4"
    )

def create_card_frequency_section(cards: List[CardFrequencyChange], title: str, color_class: str, 
                                 description: str, current_meta: MetaFormat, show_change: bool = True) -> ft.Div:
    """Create a section showing cards with frequency changes"""
    if not cards:
        return ft.Div(
            ft.H4(f"{title} (0)", cls=f"text-lg font-semibold {color_class} mb-4"),
            ft.P("No cards in this category", cls="text-gray-400 text-center py-4"),
            cls="mb-8"
        )
    
    card_elements = []
    for card in cards:
        # Create change indicator
        if show_change and card.change_type in ["increased", "decreased"]:
            change_text = f"{card.frequency_change:+.1f}pp"  # pp for percentage points
            change_color = "text-green-400" if card.frequency_change > 0 else "text-red-400"
        elif card.change_type == "new":
            change_text = "NEW"
            change_color = "text-blue-400"
        elif card.change_type == "disappeared":
            change_text = "GONE"
            change_color = "text-gray-400"
        else:
            change_text = f"{card.current_frequency*100:.1f}%"
            change_color = "text-yellow-400"
        
        # Determine which frequencies to show
        if card.change_type == "disappeared":
            freq_display = ft.P(f"Previous: {card.previous_frequency*100:.1f}%", 
                              cls="text-xs text-gray-300 text-center")
        elif card.change_type == "new":
            freq_display = ft.P(f"Current: {card.current_frequency*100:.1f}%", 
                              cls="text-xs text-gray-300 text-center")
        elif card.change_type == "stable":
            freq_display = ft.Div(
                ft.P(f"Current: {card.current_frequency*100:.1f}%", 
                     cls="text-xs text-gray-300 text-center"),
                ft.P(f"Previous: {card.previous_frequency*100:.1f}%", 
                     cls="text-xs text-gray-300 text-center")
            )
        else:  # increased/decreased
            freq_display = ft.Div(
                ft.P(f"Current: {card.current_frequency*100:.1f}%", 
                     cls="text-xs text-gray-300 text-center"),
                ft.P(f"Previous: {card.previous_frequency*100:.1f}%", 
                     cls="text-xs text-gray-300 text-center")
            )
        
        card_elements.append(
            ft.Div(
                # Card image with modal trigger
                ft.Div(
                    ft.Img(
                        src=card.card_image_url,
                        alt=card.card_name,
                        cls="w-full h-auto rounded-lg shadow-lg hover:shadow-xl transition-all duration-200 cursor-pointer hover:scale-105",
                        hx_get=f"/api/card-modal?card_id={card.card_id}&meta_format={current_meta}&currency={CardCurrency.EURO}",
                        hx_target="body",
                        hx_swap="beforeend"
                    ),
                    cls="relative aspect-[2.5/3.5] overflow-hidden"
                ),
                # Card info
                ft.Div(
                    ft.Div(
                        ft.P(card.card_name[:25] + ("..." if len(card.card_name) > 25 else ""), 
                             cls="font-semibold text-sm text-white text-center"),
                        freq_display,
                        cls="mb-2"
                    ),
                    ft.Div(
                        ft.Span(change_text, cls=f"text-sm font-bold {change_color}"),
                        cls="text-center"
                    ),
                    cls="mt-2"
                ),
                cls="bg-gray-800 p-3 rounded-lg hover:bg-gray-700 transition-colors duration-200"
            )
        )
    
    return ft.Div(
        ft.H4(f"{title} ({len(cards)})", cls=f"text-lg font-semibold {color_class} mb-4"),
        ft.P(description, cls="text-gray-300 mb-6"),
        ft.Div(
            *card_elements,
            cls="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4"
        ),
        cls="mb-12"
    )

def create_tab_view(analysis: Dict, current_meta: MetaFormat, previous_meta: MetaFormat):
    """Create a tabbed interface for the card movement content with preloaded data."""
    
    return ft.Div(
        # Tab buttons
        ft.Div(
            ft.Button(
                "✨ New Cards",
                cls="tab-button active bg-gray-700 text-white px-4 py-2 rounded-t-lg",
                onclick="switchTab(event, 'new-tab')",
                id="new-button"
            ),
            ft.Button(
                "📈 Increased Usage",
                cls="tab-button bg-gray-600 text-gray-300 px-4 py-2 rounded-t-lg ml-1",
                onclick="switchTab(event, 'increased-tab')",
                id="increased-button"
            ),
            ft.Button(
                "📉 Decreased Usage",
                cls="tab-button bg-gray-600 text-gray-300 px-4 py-2 rounded-t-lg ml-1",
                onclick="switchTab(event, 'decreased-tab')",
                id="decreased-button"
            ),
            ft.Button(
                "⚖️ Staples",
                cls="tab-button bg-gray-600 text-gray-300 px-4 py-2 rounded-t-lg ml-1",
                onclick="switchTab(event, 'stable-tab')",
                id="stable-button"
            ),
            ft.Button(
                "💀 Disappeared",
                cls="tab-button bg-gray-600 text-gray-300 px-4 py-2 rounded-t-lg ml-1",
                onclick="switchTab(event, 'disappeared-tab')",
                id="disappeared-button"
            ),
            cls="flex border-b border-gray-700 overflow-x-auto"
        ),
        
        # Tab content - all preloaded
        ft.Div(
            # New Cards Tab (shown by default)
            ft.Div(
                create_card_frequency_section(
                    analysis["new_cards"],
                    "✨ New Cards",
                    "text-blue-400",
                    "Cards that appeared in the current meta but weren't played in the previous meta.",
                    current_meta,
                    show_change=False
                ),
                cls="tab-pane p-6",
                id="new-tab",
                style="display: block;"  # Show this tab by default
            ),
            
            # Increased Usage Tab
            ft.Div(
                create_card_frequency_section(
                    analysis["increased_cards"],
                    "📈 Increased Usage",
                    "text-green-400",
                    "Cards that are played significantly more often in the current meta.",
                    current_meta
                ),
                cls="tab-pane p-6",
                id="increased-tab"
            ),
            
            # Decreased Usage Tab
            ft.Div(
                create_card_frequency_section(
                    analysis["decreased_cards"],
                    "📉 Decreased Usage",
                    "text-red-400",
                    "Cards that are played significantly less often in the current meta.",
                    current_meta
                ),
                cls="tab-pane p-6",
                id="decreased-tab"
            ),

            # Stable Staples Tab
            ft.Div(
                create_card_frequency_section(
                    analysis["stable_cards"],
                    "⚖️ Staples",
                    "text-yellow-400",
                    "Cards with consistently high usage across both metas.",
                    current_meta,
                    show_change=False
                ),
                cls="tab-pane p-6",
                id="stable-tab"
            ),

            # Disappeared Cards Tab
            ft.Div(
                create_card_frequency_section(
                    analysis["disappeared_cards"],
                    "💀 Disappeared Cards",
                    "text-gray-400",
                    "Cards that were played in the previous meta but don't appear in current decklists.",
                    current_meta,
                    show_change=False
                ),
                cls="tab-pane p-6",
                id="disappeared-tab"
            ),
            
            cls="bg-gray-800 rounded-lg shadow-xl w-full"
        ),
        
        # JavaScript for tab switching
        ft.Script("""
            function switchTab(event, tabId) {
                // Remove active class from all buttons
                document.querySelectorAll('.tab-button').forEach(button => {
                    button.classList.remove('active', 'bg-gray-700');
                    button.classList.add('bg-gray-600', 'text-gray-300');
                });
                
                // Add active class to clicked button
                event.target.classList.remove('bg-gray-600', 'text-gray-300');
                event.target.classList.add('active', 'bg-gray-700', 'text-white');
                
                // Hide all tab content
                document.querySelectorAll('.tab-pane').forEach(pane => {
                    pane.style.display = 'none';
                });
                
                // Show selected tab content
                document.getElementById(tabId).style.display = 'block';
            }
        """),
        
        # CSS for tabs
        ft.Style("""
            .tab-button.active {
                border-bottom: 2px solid #4299e1;
            }
            .tab-pane {
                display: none;
            }
        """),
        
        cls="w-full"
    )

def create_card_movement_content(leader_id: str, current_meta: MetaFormat):
    """Create the main content showing leader card frequency analysis"""
    if not leader_id:
        return ft.Div(
            ft.P("Please select a leader to view card movement analysis.", cls="text-gray-300 text-center"),
            cls="text-center py-8"
        )
    
    # Get leader data from extended data - filter by current meta format to get correct ELO and D-Score
    leaders = get_leader_extended(meta_formats=[current_meta])
    leader = next((l for l in leaders if l.id == leader_id), None)
    
    if not leader:
        return ft.Div(
            ft.P("Leader not found.", cls="text-red-400 text-center"),
            cls="text-center py-8"
        )
    
    # Get previous meta format
    meta_formats_list = MetaFormat.to_list()
    current_meta_index = meta_formats_list.index(current_meta)
    previous_meta = meta_formats_list[current_meta_index - 1] if current_meta_index > 0 else current_meta
    
    return ft.Div(
        # Leader Image and Basic Info in responsive layout
        ft.Div(
            # Left column - Leader image
            ft.Div(
                ft.Img(
                    src=leader.aa_image_url if leader.aa_image_url else leader.image_url,
                    alt=f"{leader.name}",
                    cls="w-full h-auto rounded-lg shadow-lg"
                ),
                cls="w-full md:w-1/3 flex-shrink-0 mb-6 md:mb-0 md:pr-6"
            ),
            
            # Right column - Leader info
            ft.Div(
                ft.H2(f"{leader.name} ({leader.id})", cls="text-2xl font-bold text-white mb-4"),
                ft.Div(
                    ft.Div(
                        ft.P("Life", cls="text-sm text-gray-400 mb-1"),
                        ft.P(f"{leader.life}", cls="text-xl font-bold text-white"),
                        cls="bg-gray-800 p-4 rounded-lg text-center"
                    ),
                    ft.Div(
                        ft.P("Power", cls="text-sm text-gray-400 mb-1"),
                        ft.P(f"{leader.power:,}", cls="text-xl font-bold text-white"),
                        cls="bg-gray-800 p-4 rounded-lg text-center"
                    ),
                    ft.Div(
                        ft.P("D-Score", cls="text-sm text-gray-400 mb-1"),
                        ft.P(f"{leader.d_score:.2f}" if leader.d_score else "N/A", cls="text-xl font-bold text-blue-400"),
                        cls="bg-gray-800 p-4 rounded-lg text-center"
                    ),
                    ft.Div(
                        ft.P("ELO", cls="text-sm text-gray-400 mb-1"),
                        ft.P(f"{leader.elo:.0f}" if leader.elo else "N/A", cls="text-xl font-bold text-green-400"),
                        cls="bg-gray-800 p-4 rounded-lg text-center"
                    ),
                    cls="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6"
                ),
                ft.P(f"Comparing {previous_meta} → {current_meta}", cls="text-blue-400 text-center md:text-left"),
                cls="w-full md:w-2/3 flex flex-col justify-center"
            ),
            cls="flex flex-col md:flex-row items-start mb-8"
        ),
        
        # Summary Section (above tabs)
        ft.Div(
            ft.H3("Card Play Frequency Analysis", cls="text-xl font-bold text-white mb-4 text-center"),
            ft.P("Track which cards are played more or less often compared to the previous meta format.", 
                 cls="text-gray-300 text-center mb-8"),
            
            # Summary content loaded via HTMX
            ft.Div(
                create_loading_spinner(
                    id="summary-loading-indicator",
                    size="w-8 h-8",
                    container_classes="min-h-[100px]"
                ),
                hx_get="/api/card-movement-summary",
                hx_trigger="load",
                hx_include="[name='meta_format'],[name='leader_id']",
                hx_target="this",
                hx_swap="innerHTML",
                hx_indicator="#summary-loading-indicator",
                id="summary-content",
                cls="mb-8"
            ),
            cls="mb-8"
        ),
        
        # Tab View Section (with preloaded data)
        ft.Div(
            create_loading_spinner(
                id="tabs-loading-indicator",
                size="w-8 h-8",
                container_classes="min-h-[300px]"
            ),
            hx_get="/api/card-movement-tabs",
            hx_trigger="load",
            hx_include="[name='meta_format'],[name='leader_id']",
            hx_target="this",
            hx_swap="innerHTML",
            hx_indicator="#tabs-loading-indicator",
            id="tabs-content",
            cls="mt-4"
        ),
        cls=""
    )

def create_summary_content(leader_id: str, current_meta: MetaFormat, analysis: Dict):
    """Create the summary content (above tabs)"""
    if "error" in analysis:
        return ft.Div(
            ft.P(analysis["error"], cls="text-red-400 text-center py-8"),
            cls="text-center"
        )
    
    # Create summary stats
    summary_cards = [
        ft.Div(
            ft.P("New Cards", cls="text-sm text-gray-400 mb-1"),
            ft.P(f"{analysis['summary']['total_new']}", cls="text-2xl font-bold text-blue-400"),
            cls="bg-gray-800 p-4 rounded-lg text-center"
        ),
        ft.Div(
            ft.P("Increased Usage", cls="text-sm text-gray-400 mb-1"),
            ft.P(f"{analysis['summary']['total_increased']}", cls="text-2xl font-bold text-green-400"),
            cls="bg-gray-800 p-4 rounded-lg text-center"
        ),
        ft.Div(
            ft.P("Decreased Usage", cls="text-sm text-gray-400 mb-1"),
            ft.P(f"{analysis['summary']['total_decreased']}", cls="text-2xl font-bold text-red-400"),
            cls="bg-gray-800 p-4 rounded-lg text-center"
        ),
        ft.Div(
            ft.P("Disappeared", cls="text-sm text-gray-400 mb-1"),
            ft.P(f"{analysis['summary']['total_disappeared']}", cls="text-2xl font-bold text-gray-400"),
            cls="bg-gray-800 p-4 rounded-lg text-center"
        ),
        ft.Div(
            ft.P("Stable Cards", cls="text-sm text-gray-400 mb-1"),
            ft.P(f"{analysis['summary']['total_stable']}", cls="text-2xl font-bold text-yellow-400"),
            cls="bg-gray-800 p-4 rounded-lg text-center"
        ),
        ft.Div(
            ft.P(f"{current_meta} Decklists", cls="text-sm text-gray-400 mb-1"),
            ft.P(f"{analysis['current_decklists_count']}", cls="text-2xl font-bold text-white"),
            cls="bg-gray-800 p-4 rounded-lg text-center"
        ),
        ft.Div(
            ft.P(f"{analysis['previous_meta']} Decklists", cls="text-sm text-gray-400 mb-1"),
            ft.P(f"{analysis['previous_decklists_count']}", cls="text-2xl font-bold text-white"),
            cls="bg-gray-800 p-4 rounded-lg text-center"
        )
    ]
    
    return ft.Div(
        *summary_cards,
        cls="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-7 gap-4"
    )

def create_tabs_content(leader_id: str, current_meta: MetaFormat, analysis: Dict):
    """Create the tabs content with all data preloaded"""
    if "error" in analysis:
        return ft.Div(
            ft.P(analysis["error"], cls="text-red-400 text-center py-8"),
            cls="text-center"
        )
    
    return create_tab_view(analysis, current_meta, analysis['previous_meta'])

def card_movement_page():
    """Create the card movement page with HTMX-driven content loading"""
    return ft.Div(
        # Header Section
        ft.Div(
            ft.H1("Card Movement", cls="text-3xl font-bold text-white"),
            ft.P("Track card play frequency changes of cards between meta formats.", cls="text-gray-300 mt-2"),
            cls="mb-8"
        ),

        # Loading Spinner for dynamic content
        create_loading_spinner(
            id="card-movement-loading-indicator",
            size="w-8 h-8",
            container_classes="min-h-[100px]"
        ),

        # Content container that will be populated after leader selection
        ft.Div(
            # Initially empty - will be populated via HTMX after leader selection
            ft.Div(
                ft.P("Please select a leader to view card movement analysis", cls="text-gray-400 text-center py-8"),
                cls="text-center"
            ),
            id="card-movement-content",
            cls="w-full"
        ),
        cls="min-h-screen p-4 md:p-6 w-full"
    ) 