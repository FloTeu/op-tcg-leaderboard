from collections import defaultdict
from datetime import timedelta

from fasthtml import ft
from pydantic import BaseModel, field_validator
from starlette.requests import Request

from op_tcg.backend.models.cards import OPTcgColor
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.frontend.utils.api import get_query_params_as_dict
from op_tcg.frontend.utils.extract import get_leader_extended, get_all_tournament_extened_data
from op_tcg.frontend.utils.charts import create_card_occurrence_streaming_chart

META_SHARE_THRESHOLD = 0.05  # leaders below 5% in a given meta are excluded for that meta
META_DETAIL_THRESHOLD = 0.02  # leaders below 3% total wins in the selected meta are excluded


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


class MetaDetailParams(BaseModel):
    region: MetaFormatRegion = MetaFormatRegion.ALL
    detail_meta_format: MetaFormat | None = None
    detail_view_mode: str = "leaders"

    @field_validator("region", mode="before")
    def validate_region(cls, v):
        if isinstance(v, list) and v:
            v = v[0]
        if isinstance(v, str):
            return MetaFormatRegion(v)
        return v

    @field_validator("detail_meta_format", mode="before")
    def validate_meta_format(cls, v):
        if isinstance(v, list) and v:
            v = v[0]
        if isinstance(v, str):
            try:
                return MetaFormat(v)
            except ValueError:
                return None
        return v

    @field_validator("detail_view_mode", mode="before")
    def validate_view_mode(cls, v):
        if isinstance(v, list) and v:
            v = v[0]
        return v if v in ("leaders", "colors") else "leaders"


def _week_key(dt) -> str:
    """Return ISO week end (Sunday) as YYYY-MM-DD string."""
    d = dt.date() if hasattr(dt, "date") else dt
    sunday = d + timedelta(days=6 - d.weekday())
    return sunday.isoformat()


def _compute_meta_detail_share(region: MetaFormatRegion, meta_format: MetaFormat | None, view_mode: str):
    all_metas = MetaFormat.to_list()
    if meta_format is None:
        meta_format = all_metas[-1]

    tournaments = get_all_tournament_extened_data(meta_formats=[meta_format])
    if region != MetaFormatRegion.ALL:
        tournaments = [t for t in tournaments if t.meta_format_region == region]

    tournaments.sort(key=lambda t: t.tournament_timestamp)

    # Group tournament wins by ISO week and leader
    wins_by_week: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for t in tournaments:
        if not t.leader_ids_placings:
            continue
        wk = _week_key(t.tournament_timestamp)
        for lid, placings in t.leader_ids_placings.items():
            if 1 in placings:
                wins_by_week[wk][lid] += 1

    if not wins_by_week:
        return [], [], [], [], []

    from datetime import date
    current_week = _week_key(date.today())
    weeks = [wk for wk in sorted(wins_by_week.keys()) if wk < current_week]

    if not weeks:
        return [], [], [], [], []

    # Total wins per leader across all weeks for threshold filtering
    total_per_leader: dict[str, int] = defaultdict(int)
    for wk in weeks:
        for lid, cnt in wins_by_week[wk].items():
            total_per_leader[lid] += cnt

    grand_total = sum(total_per_leader.values())
    if grand_total == 0:
        return [], [], [], [], []

    included_leaders = {lid for lid, cnt in total_per_leader.items() if cnt / grand_total > META_DETAIL_THRESHOLD}
    if not included_leaders:
        return [], [], [], [], []

    leaders = get_leader_extended(meta_formats=[meta_format])

    if view_mode == "colors":
        lid2colors: dict[str, list] = {l.id: l.colors for l in leaders if l.id}
        color_wins_by_week: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for wk in weeks:
            for lid, cnt in wins_by_week[wk].items():
                lcolors = lid2colors.get(lid, [])
                if not lcolors:
                    continue
                weight = 1.0 / len(lcolors)
                for color in lcolors:
                    color_wins_by_week[wk][str(color)] += cnt * weight

        all_colors: set[str] = set()
        for wk in weeks:
            all_colors.update(color_wins_by_week[wk].keys())

        color_order = [str(c) for c in OPTcgColor]
        color_names = [c for c in color_order if c in all_colors]
        color_hexes = [OPTcgColor(c).to_hex_color() for c in color_names]
        chart_data = [
            {color: color_wins_by_week[wk].get(color, 0.0) for color in color_names}
            for wk in weeks
        ]
        return chart_data, weeks, color_names, color_hexes, [None] * len(color_names)

    sorted_leaders = sorted(included_leaders, key=lambda l: total_per_leader[l], reverse=True)

    lid2name: dict[str, str] = {l.id: l.name for l in leaders if l.name}
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
    color_pairs = [
        pair if (pair := lid2color_pair.get(lid)) and len(pair) == 2 else None
        for lid in sorted_leaders
    ]

    chart_data = [
        {name: wins_by_week[wk].get(lid, 0) for lid, name in zip(sorted_leaders, display_names)}
        for wk in weeks
    ]
    return chart_data, weeks, display_names, colors, color_pairs


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
        return create_card_occurrence_streaming_chart(
            container_id="meta-share-stream",
            data=chart_data,
            meta_formats=meta_formats,
            card_name="Meta Share",
            normalized=True,
            colors=colors,
            color_pairs=color_pairs,
            show_title=False,
        )

    @rt("/api/meta-detail-chart")
    def get_meta_detail_chart(request: Request):
        params = MetaDetailParams(**get_query_params_as_dict(request))
        chart_data, weeks, series_names, colors, color_pairs = _compute_meta_detail_share(
            params.region, params.detail_meta_format, params.detail_view_mode
        )

        if not chart_data:
            return ft.Div(
                ft.P(
                    "No data available for the selected filters.",
                    cls="text-gray-400 text-center py-8",
                ),
                cls="w-full",
            )

        return create_card_occurrence_streaming_chart(
            container_id="meta-detail-stream",
            data=chart_data,
            meta_formats=weeks,
            card_name="Meta Detail",
            normalized=True,
            colors=colors,
            color_pairs=color_pairs,
            show_title=False,
        )
