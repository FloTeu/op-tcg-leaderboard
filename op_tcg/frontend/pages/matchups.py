from fasthtml import ft
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.frontend.components.loading import create_loading_spinner, create_loading_overlay
from op_tcg.frontend.utils.api import detect_no_match_data
from op_tcg.frontend.utils.extract import get_leader_extended

HX_INCLUDE = "[name='meta_format'],[name='leader_ids']"
FILTER_HX_ATTRS = {
    "hx_get": "/api/matchup-content",
    "hx_trigger": "change",
    "hx_target": "#matchup-content",
    "hx_include": HX_INCLUDE,
}


def _styles() -> ft.Style:
    return ft.Style("""
.mu-page { font-family: 'Barlow', sans-serif; }

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
    color: #334155;
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
    color: #334155;
    margin-top: 4px;
    display: block;
}

.meta-chart-area {
    background: #080e1c;
    border: 1px solid #1a2540;
    border-radius: 8px;
    overflow: hidden;
    padding: 8px;
}
""")


def create_filter_components(selected_meta_formats=None, selected_leader_ids=None, only_official=True):
    """Create filter components for the matchups page using HTMX and API routes."""
    leader_extended_data: list[LeaderExtended] = get_leader_extended(
        meta_formats=[MetaFormat.latest_meta_format()])
    contains_no_match_data = detect_no_match_data(leader_extended_data)
    latest_with_match_data = MetaFormatRegion.WEST if contains_no_match_data else MetaFormatRegion.ALL

    latest_meta = MetaFormat.latest_meta_format(region=latest_with_match_data)
    available_meta_formats = MetaFormat.to_list(region=latest_with_match_data)

    if not selected_meta_formats or all(
        mf not in available_meta_formats for mf in selected_meta_formats
    ):
        selected_meta_formats = [latest_meta]

    meta_format_select = ft.Div(
        ft.Span("Meta Formats", cls="meta-section-label"),
        ft.Select(
            *[ft.Option(mf, value=mf, selected=(mf in selected_meta_formats))
              for mf in reversed(available_meta_formats)],
            id="meta-formats-select",
            name="meta_format",
            multiple=True,
            size=1,
            cls="meta-select multiselect",
            **{
                "hx_get": "/api/leader-multiselect",
                "hx_target": "#leader-multiselect-wrapper",
                "hx_include": HX_INCLUDE,
                "hx_trigger": "change",
                "hx_swap": "innerHTML",
                "hx_params": "*",
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
            if (evt.target.id === 'leader-multiselect-wrapper') {
                htmx.trigger('#content-trigger', 'change');
            }
        });
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(function() {
                const leaderSelect = document.querySelector('[name="leader_ids"]');
                if (leaderSelect && leaderSelect.value) {
                    htmx.trigger('#content-trigger', 'change');
                }
            }, 100);
        });
    """)

    leader_multiselect_wrapper = ft.Div(
        create_loading_spinner(id="leader-multiselect-loading", size="w-6 h-6",
                               container_classes="min-h-[60px]"),
        hx_get="/api/leader-multiselect",
        hx_trigger="load",
        hx_include=HX_INCLUDE,
        hx_target="this",
        hx_swap="innerHTML",
        hx_indicator="#leader-multiselect-loading",
        id="leader-multiselect-wrapper",
        cls="relative"
    )

    return ft.Div(
        meta_format_select,
        leader_multiselect_wrapper,
        content_trigger,
        trigger_script,
        cls="space-y-4"
    )


def create_matchup_content(selected_meta_formats=None, selected_leader_ids=None, only_official=True):
    """Create the matchup charts and tables content that will be loaded via HTMX."""
    return ft.Div(
        # Radar chart panel
        ft.Div(
            ft.Div(
                ft.Span("Matchup Radar Chart", cls="meta-panel-title"),
                cls="mb-5",
                style="padding-bottom:14px; border-bottom:1px solid #1a2540;",
            ),
            ft.Div(
                create_loading_overlay(id="matchup-chart-loading", size="w-8 h-8"),
                ft.Div(
                    id="matchup-chart-container",
                    hx_get="/api/matchups/chart",
                    hx_trigger="load",
                    hx_indicator="#matchup-chart-loading",
                    hx_include=HX_INCLUDE,
                    cls="w-full h-full",
                ),
                cls="meta-chart-area relative",
                style="min-height:500px;",
            ),
            cls="meta-panel mb-4",
        ),

        # Details table panel
        ft.Div(
            ft.Div(
                ft.Span("Matchup Details", cls="meta-panel-title"),
                cls="mb-5",
                style="padding-bottom:14px; border-bottom:1px solid #1a2540;",
            ),
            ft.Div(
                create_loading_overlay(id="matchup-table-loading", size="w-8 h-8"),
                ft.Div(
                    id="matchup-table-container",
                    hx_get="/api/matchups/table",
                    hx_trigger="load",
                    hx_indicator="#matchup-table-loading",
                    hx_include=HX_INCLUDE,
                    cls="w-full h-full",
                ),
                cls="meta-chart-area overflow-x-auto relative",
                style="min-height:300px;",
            ),
            cls="meta-panel",
        ),

        cls="space-y-0",
    )


def matchups_page():
    """Create the main matchups page with HTMX-driven content loading."""
    return ft.Div(
        _styles(),
        ft.Div(
            ft.Div(
                ft.H1("LEADER MATCHUPS",
                      style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:2rem; color:#f1f5f9; line-height:1; margin-bottom:6px;"),
                ft.P(
                    "Analyze matchups between different leaders across meta formats.",
                    style="font-family:'Barlow',sans-serif; font-size:0.875rem; color:#334155;",
                ),
                cls="mb-6",
                style="padding-bottom:16px; border-bottom:1px solid #111d30;",
            ),
            ft.Div(
                ft.Div(
                    ft.P("Select leaders to view matchup analysis.",
                         style="font-family:'Barlow',sans-serif; color:#334155; text-align:center; padding:32px 0;"),
                ),
                id="matchup-content",
                cls="w-full",
            ),
            cls="mu-page bg-deep-navy px-4 py-4 md:px-6 md:py-6 min-h-screen",
            style="max-width:1280px; margin:0 auto;",
        ),
    )
