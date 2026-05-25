from fasthtml import ft

from op_tcg.backend.models.cards import CardCurrency
from op_tcg.backend.models.input import MetaFormat
from op_tcg.frontend.components.loading import create_loading_spinner
from op_tcg.frontend.components.filters import create_leader_select_component
from op_tcg.frontend.utils.extract import get_leader_extended
from typing import List, Dict
from pydantic import BaseModel

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


def _styles() -> ft.Style:
    return ft.Style("""
.cm-page { font-family: 'Barlow', sans-serif; }

/* Shared design-token panel/select/label classes (mirrors meta.py) */
.meta-panel {
    background: #0d1424;
    border: 1px solid #1a2540;
    border-radius: 12px;
    padding: 20px;
}
@media (min-width: 768px) { .meta-panel { padding: 24px 28px; } }

.meta-select {
    width: 100%;
    background: #080e1c;
    color: #f1f5f9;
    border: 1px solid #1a2540;
    border-radius: 8px;
    padding: 8px 12px;
    font-family: 'Barlow', sans-serif;
    font-size: 0.875rem;
    outline: none;
    cursor: pointer;
    transition: border-color 0.15s, box-shadow 0.15s;
}
.meta-select:focus { border-color: #38bdf8; box-shadow: 0 0 0 2px rgba(56,189,248,0.08); }

.meta-section-label {
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.1em;
    color: #475569;
    font-size: 0.65rem;
    text-transform: uppercase;
    display: block;
    margin-bottom: 6px;
}

.meta-panel-title {
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.12em;
    font-size: 1.15rem;
    color: #f1f5f9;
    line-height: 1;
    display: block;
}

.meta-panel-sub {
    font-family: 'Barlow', sans-serif;
    font-size: 0.7rem;
    color: #475569;
    margin-top: 4px;
    display: block;
}

/* Tab bar */
.cm-tab-bar {
    display: flex;
    border-bottom: 1px solid #1a2540;
    overflow-x: auto;
    scrollbar-width: none;
}
.cm-tab-bar::-webkit-scrollbar { display: none; }

.cm-tab-btn {
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.08em;
    font-size: 0.75rem;
    padding: 10px 18px;
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    color: #475569;
    cursor: pointer;
    transition: color 0.12s, border-color 0.12s;
    white-space: nowrap;
    flex-shrink: 0;
    margin-bottom: -1px;
}
.cm-tab-btn:hover { color: #94a3b8; }
.cm-tab-btn.active { color: #38bdf8; border-bottom-color: #38bdf8; }

/* Card item */
.cm-card-item {
    background: #0d1424;
    border: 1px solid #1a2540;
    border-radius: 8px;
    padding: 10px;
    transition: border-color 0.15s, background 0.15s;
    cursor: pointer;
}
.cm-card-item:hover { border-color: #2d3f5a; background: #111d2e; }

/* Stat card */
.cm-stat-card {
    background: #0d1424;
    border: 1px solid #1a2540;
    border-radius: 8px;
    padding: 14px 10px;
    text-align: center;
}
.cm-stat-label {
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.1em;
    color: #475569;
    font-size: 0.6rem;
    text-transform: uppercase;
    display: block;
    margin-bottom: 6px;
}
.cm-stat-value {
    font-family: 'Share Tech Mono', monospace;
    font-size: 1.35rem;
    line-height: 1;
    display: block;
}
""")


def create_filter_components(selected_meta_format=None, selected_leader_id=None):
    """Create filter components for the card movement page using HTMX and API routes"""
    if not selected_meta_format:
        selected_meta_format = MetaFormat.latest_meta_format()

    meta_format_select = ft.Div(
        ft.Span("Meta Format", cls="meta-section-label"),
        ft.Select(
            *[ft.Option(mf, value=mf, selected=mf == selected_meta_format)
              for mf in reversed(MetaFormat.to_list())],
            id="meta-format-select",
            name="meta_format",
            cls="meta-select styled-select",
            **{
                "hx_get": "/api/leader-select-generic",
                "hx_target": "#leader-select-wrapper",
                "hx_include": HX_INCLUDE,
                "hx_trigger": "change",
                "hx_swap": "innerHTML",
                "hx_params": "*",
                "hx_vals": '{"select_name": "leader_id", "label": "Leader Card", "wrapper_id": "leader-select-wrapper", "select_id": "leader-select", "auto_select_top": "true"}'
            }
        ),
    )

    content_trigger = ft.Div(
        id="content-trigger",
        **FILTER_HX_ATTRS,
        style="display: none;"
    )

    trigger_script = ft.Script("""
        document.addEventListener('htmx:afterSettle', function(evt) {
            if (evt.target.id === 'leader-select-wrapper') {
                htmx.trigger('#content-trigger', 'change');
            }
        });
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(function() {
                const leaderSelect = document.querySelector('[name="leader_id"]');
                if (leaderSelect && leaderSelect.value) {
                    htmx.trigger('#content-trigger', 'change');
                }
            }, 100);
        });
    """)

    leader_select_wrapper = ft.Div(
        create_loading_spinner(id="leader-select-loading", size="w-6 h-6", container_classes="min-h-[60px]"),
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


def create_card_frequency_section(cards: List[CardFrequencyChange], title: str, color: str,
                                  description: str, current_meta: MetaFormat,
                                  show_change: bool = True) -> ft.Div:
    """Create a section showing cards with frequency changes"""
    if not cards:
        return ft.Div(
            ft.H4(f"{title} (0)",
                  style=f"font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:1.1rem; color:{color}; margin-bottom:16px;"),
            ft.P("No cards in this category",
                 style="font-family:'Barlow',sans-serif; color:#475569; text-align:center; padding:16px 0;"),
            cls="mb-8"
        )

    card_elements = []
    for card in cards:
        if show_change and card.change_type in ["increased", "decreased"]:
            change_text = f"{card.frequency_change:+.1f}pp"
            change_color = "#10b981" if card.frequency_change > 0 else "#ef4444"
        elif card.change_type == "new":
            change_text = "NEW"
            change_color = "#38bdf8"
        elif card.change_type == "disappeared":
            change_text = "GONE"
            change_color = "#475569"
        else:
            change_text = f"{card.current_frequency * 100:.1f}%"
            change_color = "#f59e0b"

        if card.change_type == "disappeared":
            freq_display = ft.P(
                f"Prev: {card.previous_frequency * 100:.1f}%",
                style="font-family:'Share Tech Mono',monospace; font-size:0.68rem; color:#475569; text-align:center;"
            )
        elif card.change_type == "new":
            freq_display = ft.P(
                f"Cur: {card.current_frequency * 100:.1f}%",
                style="font-family:'Share Tech Mono',monospace; font-size:0.68rem; color:#475569; text-align:center;"
            )
        else:
            freq_display = ft.Div(
                ft.P(f"Cur: {card.current_frequency * 100:.1f}%",
                     style="font-family:'Share Tech Mono',monospace; font-size:0.68rem; color:#475569; text-align:center;"),
                ft.P(f"Prev: {card.previous_frequency * 100:.1f}%",
                     style="font-family:'Share Tech Mono',monospace; font-size:0.68rem; color:#475569; text-align:center;"),
            )

        card_elements.append(
            ft.Div(
                ft.Div(
                    ft.Img(
                        src=card.card_image_url,
                        alt=card.card_name,
                        cls="w-full h-auto",
                        style="border-radius:4px;",
                        hx_get=f"/api/card-modal?card_id={card.card_id}&meta_format={current_meta}&currency={CardCurrency.EURO}",
                        hx_target="body",
                        hx_swap="beforeend"
                    ),
                    cls="relative aspect-[2.5/3.5] overflow-hidden",
                    style="border-radius:4px;",
                ),
                ft.Div(
                    ft.P(card.card_name[:22] + ("\u2026" if len(card.card_name) > 22 else ""),
                         style="font-family:'Barlow',sans-serif; font-weight:500; font-size:0.72rem; color:#94a3b8; text-align:center; margin-bottom:4px;"),
                    freq_display,
                    ft.Div(
                        ft.Span(change_text,
                                style=f"font-family:'Bebas Neue',sans-serif; letter-spacing:0.08em; font-size:0.85rem; color:{change_color};"),
                        style="text-align:center; margin-top:4px;",
                    ),
                    cls="mt-2",
                ),
                cls="cm-card-item",
            )
        )

    return ft.Div(
        ft.H4(f"{title} ({len(cards)})",
              style=f"font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:1.1rem; color:{color}; margin-bottom:10px;"),
        ft.P(description,
             style="font-family:'Barlow',sans-serif; font-size:0.8rem; color:#475569; margin-bottom:18px;"),
        ft.Div(
            *card_elements,
            cls="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3",
        ),
        cls="mb-10"
    )


def create_tab_view(analysis: Dict, current_meta: MetaFormat, previous_meta: MetaFormat):
    """Create a tabbed interface for the card movement content with preloaded data."""
    return ft.Div(
        ft.Div(
            ft.Button("NEW", cls="cm-tab-btn active", onclick="cmSwitchTab(event,'new-tab')", id="new-button"),
            ft.Button("INCREASED", cls="cm-tab-btn", onclick="cmSwitchTab(event,'increased-tab')", id="increased-button"),
            ft.Button("DECREASED", cls="cm-tab-btn", onclick="cmSwitchTab(event,'decreased-tab')", id="decreased-button"),
            ft.Button("STAPLES", cls="cm-tab-btn", onclick="cmSwitchTab(event,'stable-tab')", id="stable-button"),
            ft.Button("DISAPPEARED", cls="cm-tab-btn", onclick="cmSwitchTab(event,'disappeared-tab')", id="disappeared-button"),
            cls="cm-tab-bar",
        ),
        ft.Div(
            ft.Div(
                create_card_frequency_section(
                    analysis["new_cards"], "New Cards", "#38bdf8",
                    "Cards that appeared in the current meta but weren't played in the previous meta.",
                    current_meta, show_change=False
                ),
                cls="tab-pane p-4 md:p-6", id="new-tab", style="display:block;",
            ),
            ft.Div(
                create_card_frequency_section(
                    analysis["increased_cards"], "Increased Usage", "#10b981",
                    "Cards that are played significantly more often in the current meta.",
                    current_meta
                ),
                cls="tab-pane p-4 md:p-6", id="increased-tab",
            ),
            ft.Div(
                create_card_frequency_section(
                    analysis["decreased_cards"], "Decreased Usage", "#ef4444",
                    "Cards that are played significantly less often in the current meta.",
                    current_meta
                ),
                cls="tab-pane p-4 md:p-6", id="decreased-tab",
            ),
            ft.Div(
                create_card_frequency_section(
                    analysis["stable_cards"], "Staples", "#f59e0b",
                    "Cards with consistently high usage across both metas.",
                    current_meta, show_change=False
                ),
                cls="tab-pane p-4 md:p-6", id="stable-tab",
            ),
            ft.Div(
                create_card_frequency_section(
                    analysis["disappeared_cards"], "Disappeared Cards", "#475569",
                    "Cards that were played in the previous meta but don't appear in current decklists.",
                    current_meta, show_change=False
                ),
                cls="tab-pane p-4 md:p-6", id="disappeared-tab",
            ),
            style="background:#080e1c;",
        ),
        ft.Script("""
            function cmSwitchTab(event, tabId) {
                document.querySelectorAll('.cm-tab-btn').forEach(function(btn) {
                    btn.classList.remove('active');
                });
                event.currentTarget.classList.add('active');
                document.querySelectorAll('.tab-pane').forEach(function(pane) {
                    pane.style.display = 'none';
                });
                document.getElementById(tabId).style.display = 'block';
            }
        """),
        ft.Style(".tab-pane { display: none; }"),
        cls="meta-panel w-full",
        style="padding:0; overflow:hidden;",
    )


def create_card_movement_content(leader_id: str, current_meta: MetaFormat):
    """Create the main content showing leader card frequency analysis"""
    if not leader_id:
        return ft.Div(
            ft.P("Please select a leader to view card movement analysis.",
                 style="font-family:'Barlow',sans-serif; color:#475569; text-align:center;"),
            cls="py-8 text-center"
        )

    leaders = get_leader_extended(meta_formats=[current_meta])
    leader = next((l for l in leaders if l.id == leader_id), None)

    if not leader:
        return ft.Div(
            ft.P("Leader not found.",
                 style="font-family:'Barlow',sans-serif; color:#ef4444; text-align:center;"),
            cls="py-8 text-center"
        )

    meta_formats_list = MetaFormat.to_list()
    current_meta_index = meta_formats_list.index(current_meta)
    previous_meta = meta_formats_list[current_meta_index - 1] if current_meta_index > 0 else current_meta

    return ft.Div(
        # Leader info panel
        ft.Div(
            ft.Div(
                ft.Img(
                    src=leader.aa_image_url if leader.aa_image_url else leader.image_url,
                    alt=leader.name,
                    cls="w-full h-auto",
                    style="border-radius:8px;",
                ),
                cls="w-full md:w-44 flex-shrink-0 mb-4 md:mb-0",
            ),
            ft.Div(
                ft.H2(leader.name,
                      style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:1.6rem; color:#f1f5f9; margin-bottom:2px;"),
                ft.Span(leader.id,
                        style="font-family:'Share Tech Mono',monospace; font-size:0.72rem; color:#475569; display:block; margin-bottom:14px;"),
                ft.Div(
                    ft.Div(
                        ft.Span("LIFE", cls="cm-stat-label"),
                        ft.Span(f"{leader.life}", cls="cm-stat-value", style="color:#f1f5f9;"),
                        cls="cm-stat-card",
                    ),
                    ft.Div(
                        ft.Span("POWER", cls="cm-stat-label"),
                        ft.Span(f"{leader.power:,}", cls="cm-stat-value", style="color:#f1f5f9;"),
                        cls="cm-stat-card",
                    ),
                    ft.Div(
                        ft.Span("D-SCORE", cls="cm-stat-label"),
                        ft.Span(f"{leader.d_score:.2f}" if leader.d_score else "N/A",
                                cls="cm-stat-value", style="color:#38bdf8;"),
                        cls="cm-stat-card",
                    ),
                    ft.Div(
                        ft.Span("ELO", cls="cm-stat-label"),
                        ft.Span(f"{leader.elo:.0f}" if leader.elo else "N/A",
                                cls="cm-stat-value", style="color:#10b981;"),
                        cls="cm-stat-card",
                    ),
                    cls="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4",
                ),
                ft.Span(f"{previous_meta}  \u2192  {current_meta}",
                        style="font-family:'Share Tech Mono',monospace; font-size:0.72rem; color:#38bdf8;"),
                cls="flex-1",
            ),
            cls="flex flex-col md:flex-row gap-6 items-start",
        ),

        # Summary section
        ft.Div(
            ft.Span("Card Play Frequency Analysis", cls="meta-panel-title",
                    style="font-size:1.2rem; margin-bottom:4px;"),
            ft.Span("Track which cards are played more or less often compared to the previous meta format.",
                    cls="meta-panel-sub", style="margin-bottom:18px; display:block;"),
            ft.Div(
                create_loading_spinner(id="summary-loading-indicator", size="w-8 h-8",
                                       container_classes="min-h-[100px]"),
                hx_get="/api/card-movement-summary",
                hx_trigger="load",
                hx_include="[name='meta_format'],[name='leader_id']",
                hx_target="this",
                hx_swap="innerHTML",
                hx_indicator="#summary-loading-indicator",
                id="summary-content",
                cls="mb-4",
            ),
            cls="mt-6",
        ),

        # Tabs section
        ft.Div(
            create_loading_spinner(id="tabs-loading-indicator", size="w-8 h-8",
                                   container_classes="min-h-[300px]"),
            hx_get="/api/card-movement-tabs",
            hx_trigger="load",
            hx_include="[name='meta_format'],[name='leader_id']",
            hx_target="this",
            hx_swap="innerHTML",
            hx_indicator="#tabs-loading-indicator",
            id="tabs-content",
            cls="mt-4",
        ),
    )


def create_summary_content(leader_id: str, current_meta: MetaFormat, analysis: Dict):
    """Create the summary content (above tabs)"""
    if "error" in analysis:
        return ft.Div(
            ft.P(analysis["error"],
                 style="font-family:'Barlow',sans-serif; color:#ef4444; text-align:center; padding:32px 0;"),
        )

    summary_cards = [
        ft.Div(
            ft.Span("New Cards", cls="cm-stat-label"),
            ft.Span(f"{analysis['summary']['total_new']}", cls="cm-stat-value", style="color:#38bdf8;"),
            cls="cm-stat-card",
        ),
        ft.Div(
            ft.Span("Increased", cls="cm-stat-label"),
            ft.Span(f"{analysis['summary']['total_increased']}", cls="cm-stat-value", style="color:#10b981;"),
            cls="cm-stat-card",
        ),
        ft.Div(
            ft.Span("Decreased", cls="cm-stat-label"),
            ft.Span(f"{analysis['summary']['total_decreased']}", cls="cm-stat-value", style="color:#ef4444;"),
            cls="cm-stat-card",
        ),
        ft.Div(
            ft.Span("Disappeared", cls="cm-stat-label"),
            ft.Span(f"{analysis['summary']['total_disappeared']}", cls="cm-stat-value", style="color:#475569;"),
            cls="cm-stat-card",
        ),
        ft.Div(
            ft.Span("Stable Cards", cls="cm-stat-label"),
            ft.Span(f"{analysis['summary']['total_stable']}", cls="cm-stat-value", style="color:#f59e0b;"),
            cls="cm-stat-card",
        ),
        ft.Div(
            ft.Span(f"{current_meta} Decks", cls="cm-stat-label"),
            ft.Span(f"{analysis['current_decklists_count']}", cls="cm-stat-value", style="color:#f1f5f9;"),
            cls="cm-stat-card",
        ),
        ft.Div(
            ft.Span(f"{analysis['previous_meta']} Decks", cls="cm-stat-label"),
            ft.Span(f"{analysis['previous_decklists_count']}", cls="cm-stat-value", style="color:#f1f5f9;"),
            cls="cm-stat-card",
        ),
    ]

    return ft.Div(
        *summary_cards,
        cls="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3",
    )


def create_tabs_content(leader_id: str, current_meta: MetaFormat, analysis: Dict):
    """Create the tabs content with all data preloaded"""
    if "error" in analysis:
        return ft.Div(
            ft.P(analysis["error"],
                 style="font-family:'Barlow',sans-serif; color:#ef4444; text-align:center; padding:32px 0;"),
        )
    return create_tab_view(analysis, current_meta, analysis['previous_meta'])


def card_movement_page():
    """Create the card movement page with HTMX-driven content loading"""
    return ft.Div(
        _styles(),
        ft.Div(
            ft.Div(
                ft.H1("CARD MOVEMENT",
                      style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:2rem; color:#f1f5f9; line-height:1; margin-bottom:6px;"),
                ft.P(
                    "Track card play frequency changes between meta formats.",
                    style="font-family:'Barlow',sans-serif; font-size:0.875rem; color:#475569;",
                ),
                cls="mb-6",
                style="padding-bottom:16px; border-bottom:1px solid #111d30;",
            ),
            create_loading_spinner(id="card-movement-loading-indicator", size="w-8 h-8",
                                   container_classes="min-h-[100px]"),
            ft.Div(
                ft.Div(
                    ft.P("Select a leader to view card movement analysis.",
                         style="font-family:'Barlow',sans-serif; color:#475569; text-align:center; padding:32px 0;"),
                ),
                id="card-movement-content",
                cls="w-full",
            ),
            cls="cm-page bg-deep-navy px-4 py-4 md:px-6 md:py-6 min-h-screen",
            style="max-width:1280px; margin:0 auto;",
        ),
    )
