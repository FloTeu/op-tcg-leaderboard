from collections import defaultdict

from fasthtml import ft
from pydantic import BaseModel, field_validator
from starlette.requests import Request

from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.frontend.utils.api import get_query_params_as_dict
from op_tcg.frontend.utils.extract import get_tournament_decklist_data
from op_tcg.frontend.utils.leader_data import get_lid2ldata_dict_cached
from op_tcg.frontend.utils.charts import create_card_occurrence_streaming_chart

META_SHARE_THRESHOLD = 0.05  # leaders below 5% in a given meta are excluded for that meta


class MetaParams(BaseModel):
    region: MetaFormatRegion = MetaFormatRegion.ALL

    @field_validator("region", mode="before")
    def validate_region(cls, v):
        if isinstance(v, list) and v:
            v = v[0]
        if isinstance(v, str):
            return MetaFormatRegion(v)
        return v


def _compute_meta_share(region: MetaFormatRegion):
    meta_formats = MetaFormat.to_list()
    lid2ldata = get_lid2ldata_dict_cached()

    decklists = get_tournament_decklist_data(
        meta_formats=meta_formats,
        meta_format_region=region,
    )

    leader_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    total_per_meta: dict[str, int] = defaultdict(int)

    for dl in decklists:
        if not dl.leader_id or dl.leader_id not in lid2ldata:
            continue
        meta_key = str(dl.meta_format)
        leader_counts[meta_key][dl.leader_id] += 1
        total_per_meta[meta_key] += 1

    active_metas = [mf for mf in meta_formats if total_per_meta.get(mf, 0) > 0]
    if not active_metas:
        return [], [], []

    # For each meta, compute proportions and determine which leaders exceed threshold
    # Leaders below 5% in a specific meta are zeroed out for that meta only
    per_meta_proportions: dict[str, dict[str, float]] = {}
    all_included_leaders: set[str] = set()

    for meta in active_metas:
        total = total_per_meta[meta]
        meta_props: dict[str, float] = {}
        for lid, count in leader_counts[meta].items():
            prop = count / total
            if prop > META_SHARE_THRESHOLD:
                meta_props[lid] = prop
                all_included_leaders.add(lid)
        per_meta_proportions[meta] = meta_props

    if not all_included_leaders:
        return [], [], []

    # Sort leaders by total raw count descending for consistent series ordering
    leader_totals = {
        lid: sum(leader_counts[meta].get(lid, 0) for meta in active_metas)
        for lid in all_included_leaders
    }
    sorted_leaders = sorted(all_included_leaders, key=lambda l: leader_totals[l], reverse=True)

    def _display_name(lid: str) -> str:
        ldata = lid2ldata.get(lid)
        return f"{ldata.name} ({lid})" if ldata and ldata.name else lid

    display_names = [_display_name(lid) for lid in sorted_leaders]

    # Build chart data: per-meta proportions, zero for leaders below threshold in that meta.
    # Passing proportions with normalized=True causes the chart to re-normalize included
    # (non-zero) leaders to 100%, so each meta fills the full chart height.
    chart_data = [
        {
            name: per_meta_proportions[meta].get(lid, 0.0)
            for lid, name in zip(sorted_leaders, display_names)
        }
        for meta in active_metas
    ]

    return chart_data, active_metas, display_names


def setup_api_routes(rt):
    @rt("/api/meta-share-chart")
    def get_meta_share_chart(request: Request):
        params = MetaParams(**get_query_params_as_dict(request))
        chart_data, meta_formats, leaders = _compute_meta_share(params.region)

        if not chart_data:
            return ft.Div(
                ft.P(
                    "No data available for the selected filters.",
                    cls="text-gray-400 text-center py-8",
                ),
                cls="w-full",
            )

        return create_card_occurrence_streaming_chart(
            container_id="meta-share-stream",
            data=chart_data,
            meta_formats=meta_formats,
            card_name="Meta Share",
            normalized=True,
        )
