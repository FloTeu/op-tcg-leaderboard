from fasthtml import ft
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.frontend.components.loading import create_loading_spinner, create_loading_overlay
from op_tcg.frontend.components.tournament_charts import (
    create_decklist_popularity_section,
    create_leader_popularity_section,
)

FILTER_HX_ATTRS = {
    "hx_get": "/api/tournament-content",
    "hx_trigger": "change",
    "hx_target": "#tournament-content",
    "hx_include": "[name='meta_format'],[name='region'],[name='min_matches'],[name='max_matches']"
}


def _styles() -> ft.Style:
    return ft.Style("""
.tp-page { font-family: 'Barlow', sans-serif; }

/* Shared design-token panel/select/label classes (mirrors meta.py until design-system.css) */
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

.meta-toggle-group {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px;
    background: #080e1c;
    border: 1px solid #1a2540;
    border-radius: 24px;
    flex-shrink: 0;
}

.meta-toggle-btn {
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.08em;
    font-size: 0.72rem;
    padding: 4px 16px;
    border-radius: 20px;
    border: 1px solid transparent;
    background: transparent;
    color: #475569;
    cursor: pointer;
    transition: all 0.12s;
    white-space: nowrap;
}
.meta-toggle-btn:hover { color: #64748b; }
.meta-toggle-btn.active {
    background: rgba(56,189,248,0.1);
    color: #38bdf8;
    border-color: rgba(56,189,248,0.3);
}

.meta-chart-area {
    background: #080e1c;
    border: 1px solid #1a2540;
    border-radius: 8px;
    overflow: hidden;
    padding: 8px;
}

.slider-values {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.8rem;
    color: #38bdf8;
}

/* Prevent chart tooltips from causing horizontal overflow */
#chartjs-tooltip {
    max-width: 90vw !important;
    box-sizing: border-box !important;
}
""")


def create_filter_components(selected_meta_formats=None, selected_region: MetaFormatRegion | None = None):
    latest_meta = MetaFormat.latest_meta_format()

    if not selected_meta_formats:
        selected_meta_formats = [latest_meta]

    selected_region = selected_region or MetaFormatRegion.ALL

    meta_format_select = ft.Div(
        ft.Span("Meta Formats", cls="meta-section-label"),
        ft.Select(
            *[ft.Option(mf, value=mf, selected=(mf in selected_meta_formats))
              for mf in reversed(MetaFormat.to_list(region=MetaFormatRegion.ALL))],
            id="meta-formats-select",
            name="meta_format",
            multiple=True,
            size=1,
            cls="meta-select multiselect",
            **FILTER_HX_ATTRS,
        ),
    )

    region_select = ft.Div(
        ft.Span("Region", cls="meta-section-label"),
        ft.Select(
            *[ft.Option(r, value=r, selected=(r == selected_region))
              for r in MetaFormatRegion.to_list()],
            id="region-select",
            name="region",
            cls="meta-select styled-select",
            **FILTER_HX_ATTRS,
        ),
    )

    return ft.Div(meta_format_select, region_select, cls="space-y-4")


def create_tournament_content():
    return ft.Div(
        # ── Tournament Analytics ──────────────────────────────────────────────
        ft.Div(
            ft.Div(
                ft.H1("TOURNAMENTS",
                      style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:2rem; color:#f1f5f9; line-height:1; margin-bottom:6px;"),
                ft.P(
                    "Analytics and results for competitive One Piece TCG tournaments.",
                    style="font-family:'Barlow',sans-serif; font-size:0.875rem; color:#334155;",
                ),
                cls="mb-6",
                style="padding-bottom:16px; border-bottom:1px solid #111d30;",
            ),
            ft.Div(
                ft.Div(create_decklist_popularity_section(id_prefix="tournament-"), cls="w-full"),
                ft.Div(create_leader_popularity_section(id_prefix="tournament-"), cls="w-full"),
                cls="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6",
            ),
            cls="mb-6",
        ),

        # ── Tournament Explorer ───────────────────────────────────────────────
        ft.Div(
            ft.Div(
                ft.Span("Tournament Explorer", cls="meta-panel-title", style="font-size:1.3rem;"),
                ft.Span("Browse and filter all recorded tournaments.", cls="meta-panel-sub"),
                cls="mb-5",
                style="padding-bottom:14px; border-bottom:1px solid #1a2540;",
            ),
            ft.Div(
                create_loading_overlay(id="tournament-list-loading", size="w-8 h-8"),
                ft.Div(
                    id="tournament-list-container",
                    hx_get="/api/tournaments/all",
                    hx_trigger="load",
                    hx_include="[name='meta_format'],[name='region'],[name='min_matches'],[name='max_matches']",
                    hx_indicator="#tournament-list-loading",
                    cls="w-full h-full",
                ),
                cls="meta-chart-area relative overflow-x-auto",
                style="min-height:200px;",
            ),
            cls="meta-panel",
        ),

        cls="tp-page bg-deep-navy px-4 py-4 md:px-6 md:py-6 min-h-screen",
        style="max-width:1280px; margin:0 auto;",
        id="tournament-content",
    )


def tournaments_page():
    return ft.Div(
        _styles(),
        create_tournament_content(),
    )
