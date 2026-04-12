from collections import defaultdict

from fasthtml import ft
from pydantic import BaseModel, field_validator
from starlette.requests import Request

from op_tcg.backend.models.cards import OPTcgColor
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.frontend.utils.api import get_query_params_as_dict
from op_tcg.frontend.utils.extract import get_leader_extended
from op_tcg.frontend.utils.charts import create_card_occurrence_streaming_chart

META_SHARE_THRESHOLD = 0.05  # leaders below 5% in a given meta are excluded for that meta


class MetaParams(BaseModel):
    region: MetaFormatRegion = MetaFormatRegion.ALL
    from_meta_idx: int | None = None
    to_meta_idx: int | None = None
    meta_view_mode: str = "leaders"

    @field_validator("region", mode="before")
    def validate_region(cls, v):
        if isinstance(v, list) and v:
            v = v[0]
        if isinstance(v, str):
            return MetaFormatRegion(v)
        return v

    @field_validator("from_meta_idx", "to_meta_idx", mode="before")
    def validate_int(cls, v):
        if isinstance(v, list) and v:
            v = v[0]
        if isinstance(v, str):
            return int(v)
        return v

    @field_validator("meta_view_mode", mode="before")
    def validate_view_mode(cls, v):
        if isinstance(v, list) and v:
            v = v[0]
        return v if v in ("leaders", "colors") else "leaders"


def _compute_color_share(wins: dict, active_metas: list, leaders) -> tuple:
    """Aggregate tournament wins by OPTcgColor across active metas."""
    lid2colors: dict[str, list] = {}
    for l in leaders:
        if l.id and l.id not in lid2colors:
            lid2colors[l.id] = l.colors  # list[OPTcgColor]

    color_wins: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for meta in active_metas:
        for lid, count in wins[meta].items():
            lcolors = lid2colors.get(lid, [])
            if not lcolors:
                continue
            weight = 1.0 / len(lcolors)
            for color in lcolors:
                color_wins[meta][str(color)] += count * weight

    all_colors_present: set[str] = set()
    for meta in active_metas:
        all_colors_present.update(color_wins[meta].keys())

    if not all_colors_present:
        return [], [], [], []

    # Preserve canonical OP TCG color order
    color_order = [str(c) for c in OPTcgColor]
    color_names = [c for c in color_order if c in all_colors_present]

    chart_data = [
        {color: color_wins[meta].get(color, 0.0) for color in color_names}
        for meta in active_metas
    ]
    color_hexes = [OPTcgColor(c).to_hex_color() for c in color_names]

    return chart_data, active_metas, color_names, color_hexes


def _compute_meta_share(region: MetaFormatRegion, from_meta_idx: int | None = None, to_meta_idx: int | None = None, view_mode: str = "leaders"):
    all_meta_formats = MetaFormat.to_list()
    n = len(all_meta_formats)
    # Apply range defaults: last 4 if not specified
    if from_meta_idx is None:
        from_meta_idx = max(0, n - 4)
    if to_meta_idx is None:
        to_meta_idx = n - 1
    from_meta_idx = max(0, min(from_meta_idx, n - 1))
    to_meta_idx = max(from_meta_idx, min(to_meta_idx, n - 1))
    meta_formats = all_meta_formats[from_meta_idx: to_meta_idx + 1]

    leaders = get_leader_extended(meta_format_region=region)

    # Sum tournament_wins per leader per meta
    wins: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    total_wins: dict[str, int] = defaultdict(int)

    for l in leaders:
        if not l.id or not l.meta_format or not l.tournament_wins:
            continue
        meta_key = str(l.meta_format)
        wins[meta_key][l.id] += l.tournament_wins
        total_wins[meta_key] += l.tournament_wins

    active_metas = [mf for mf in meta_formats if total_wins.get(mf, 0) > 0]
    if not active_metas:
        return [], [], [], []

    if view_mode == "colors":
        chart_data, active_metas, color_names, color_hexes = _compute_color_share(wins, active_metas, leaders)
        return chart_data, active_metas, color_names, color_hexes, [None] * len(color_names)

    # Per-meta proportions; leaders below threshold are zeroed out for that meta only
    per_meta_proportions: dict[str, dict[str, float]] = {}
    all_included_leaders: set[str] = set()

    for meta in active_metas:
        total = total_wins[meta]
        meta_props: dict[str, float] = {}
        for lid, count in wins[meta].items():
            prop = count / total
            if prop > META_SHARE_THRESHOLD:
                meta_props[lid] = prop
                all_included_leaders.add(lid)
        per_meta_proportions[meta] = meta_props

    if not all_included_leaders:
        return [], [], [], []

    # Sort by total wins across all metas for consistent series ordering
    leader_totals = {
        lid: sum(wins[meta].get(lid, 0) for meta in active_metas)
        for lid in all_included_leaders
    }
    sorted_leaders = sorted(all_included_leaders, key=lambda l: leader_totals[l], reverse=True)

    # Use leader name and color from the extended data itself
    lid2name: dict[str, str] = {l.id: l.name for l in leaders if l.name}
    # Use the most-recent entry per leader for the color (they share the same colors across metas)
    lid2color: dict[str, str] = {}
    lid2color_pair: dict[str, list[str]] = {}
    for l in leaders:
        if l.id and l.id not in lid2color:
            try:
                lid2color[l.id] = l.to_hex_color()
                lid2color_pair[l.id] = [c.to_hex_color() for c in l.colors]
            except Exception:
                pass

    def _display_name(lid: str) -> str:
        name = lid2name.get(lid)
        return f"{name} ({lid})" if name else lid

    display_names = [_display_name(lid) for lid in sorted_leaders]
    colors = [lid2color.get(lid, "#6B7280") for lid in sorted_leaders]
    # None for mono-color leaders, [hex1, hex2] for duo-color leaders
    color_pairs = [
        pair if (pair := lid2color_pair.get(lid)) and len(pair) == 2 else None
        for lid in sorted_leaders
    ]

    # Build chart data: per-meta proportions, zero for leaders below threshold in that meta.
    # normalized=True causes the chart to re-normalize included leaders to 100% per meta.
    chart_data = [
        {
            name: per_meta_proportions[meta].get(lid, 0.0)
            for lid, name in zip(sorted_leaders, display_names)
        }
        for meta in active_metas
    ]

    return chart_data, active_metas, display_names, colors, color_pairs


def setup_api_routes(rt):
    @rt("/api/meta-share-chart")
    def get_meta_share_chart(request: Request):
        params = MetaParams(**get_query_params_as_dict(request))
        chart_data, meta_formats, series_names, colors, color_pairs = _compute_meta_share(
            params.region, params.from_meta_idx, params.to_meta_idx, params.meta_view_mode
        )

        if not chart_data:
            return ft.Div(
                ft.P(
                    "No data available for the selected filters.",
                    cls="text-gray-400 text-center py-8",
                ),
                cls="w-full",
            )

        is_colors = params.meta_view_mode == "colors"
        title = (
            "Meta Index (Color Tournament Win Share)"
            if is_colors
            else "Meta Index (Leader Tournament Win Share)"
        )
        title_tooltip = None if is_colors else "Only leaders with more than 5% tournament win share are shown."
        return create_card_occurrence_streaming_chart(
            container_id="meta-share-stream",
            data=chart_data,
            meta_formats=meta_formats,
            card_name="Meta Share",
            normalized=True,
            title=title,
            colors=colors,
            title_tooltip=title_tooltip,
            color_pairs=color_pairs,
        )
