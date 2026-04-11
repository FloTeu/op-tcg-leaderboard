"""Server-side OG image generation for social media previews."""

import os
import time
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

_OG_META_PATH = "public/og-meta.png"
_OG_LEADER_PATH = "public/og-leader.png"
_CACHE_TTL_SECONDS = 4 * 3600  # Regenerate at most every 4 hours

# OG image dimensions (standard Open Graph)
_WIDTH_IN = 12.0
_HEIGHT_IN = 6.3
_DPI = 100  # → 1200×630 px

_BG_DARK = "#111827"
_BG_CARD = "#1F2937"
_TEXT_PRIMARY = "#F9FAFB"
_TEXT_MUTED = "#9CA3AF"
_GRID_COLOR = "#374151"


def _render_meta_chart() -> bytes:
    """Render the meta index stacked bar chart as PNG bytes using matplotlib."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    from op_tcg.backend.models.input import MetaFormatRegion
    from op_tcg.frontend.api.routes.meta import _compute_meta_share

    chart_data, meta_formats, display_names, colors = _compute_meta_share(
        region=MetaFormatRegion.ALL,
        view_mode="leaders",
    )

    fig, ax = plt.subplots(figsize=(_WIDTH_IN, _HEIGHT_IN))
    fig.patch.set_facecolor(_BG_DARK)
    ax.set_facecolor(_BG_CARD)

    if not chart_data or not meta_formats:
        ax.text(
            0.5, 0.5, "No data available",
            ha="center", va="center", color=_TEXT_MUTED, fontsize=14,
            transform=ax.transAxes,
        )
    else:
        n = len(meta_formats)
        x = np.arange(n)
        bar_width = min(0.65, 4 / n)  # Narrower bars when many metas

        # Re-normalize each meta column so bars fill to 100 %
        norm: list[dict[str, float]] = []
        for meta_idx in range(n):
            raw = {name: chart_data[meta_idx].get(name, 0.0) for name in display_names}
            total = sum(raw.values())
            norm.append({k: (v / total * 100) if total else 0.0 for k, v in raw.items()})

        bottoms = np.zeros(n)
        for name, color in zip(display_names, colors):
            values = np.array([norm[i].get(name, 0.0) for i in range(n)])
            ax.bar(x, values, bottom=bottoms, color=color, alpha=0.88, width=bar_width)
            bottoms += values

        ax.set_xticks(x)
        ax.set_xticklabels(meta_formats, color=_TEXT_PRIMARY, fontsize=11, rotation=30, ha="right")
        ax.set_ylim(0, 108)
        ax.set_ylabel("Win Share (%)", color=_TEXT_MUTED, fontsize=11)
        ax.tick_params(axis="y", colors=_TEXT_MUTED, labelsize=10)
        ax.tick_params(axis="x", length=0)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        for spine in ("bottom", "left"):
            ax.spines[spine].set_color(_GRID_COLOR)
        ax.grid(axis="y", color=_GRID_COLOR, linewidth=0.8, linestyle="--", alpha=0.7)
        ax.set_axisbelow(True)

    ax.set_title(
        "Meta Index – Leader Tournament Win Share",
        color=_TEXT_PRIMARY, fontsize=16, fontweight="bold", pad=14, loc="left",
    )
    fig.text(0.98, 0.015, "op-tcg-leaderboard.com", ha="right", va="bottom",
             color=_TEXT_MUTED, fontsize=9)

    fig.tight_layout(rect=(0, 0.02, 1, 1))

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=_DPI, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _render_leader_chart() -> bytes:
    """Render a horizontal bar chart of top leaders by tournament wins as PNG bytes."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
    from op_tcg.frontend.utils.extract import get_leader_extended

    latest = MetaFormat.latest_meta_format()
    leaders = get_leader_extended(
        meta_formats=[latest],
        meta_format_region=MetaFormatRegion.ALL,
        only_official=False,
    )

    # Deduplicate by leader id, keeping the entry with the most tournament wins
    seen: dict = {}
    for l in leaders:
        if not l.id:
            continue
        wins = l.tournament_wins or 0
        if l.id not in seen or wins > (seen[l.id].tournament_wins or 0):
            seen[l.id] = l

    candidates = [l for l in seen.values() if (l.tournament_wins or 0) >= 1]
    candidates.sort(key=lambda l: l.tournament_wins or 0, reverse=True)
    top = candidates[:12]

    fig, ax = plt.subplots(figsize=(_WIDTH_IN, _HEIGHT_IN))
    fig.patch.set_facecolor(_BG_DARK)
    ax.set_facecolor(_BG_CARD)

    if not top:
        ax.text(0.5, 0.5, "No data available",
                ha="center", va="center", color=_TEXT_MUTED, fontsize=14,
                transform=ax.transAxes)
    else:
        # Reverse so highest wins ends up at the top of the chart
        top = top[::-1]
        labels = [f"{l.name} ({l.id})" if l.name else l.id for l in top]
        values = [l.tournament_wins or 0 for l in top]
        colors = []
        for l in top:
            try:
                colors.append(l.to_hex_color())
            except Exception:
                colors.append("#6B7280")

        y = np.arange(len(top))
        bars = ax.barh(y, values, color=colors, alpha=0.88, height=0.6)

        # Win count labels beside each bar
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_width() + max(values) * 0.01, bar.get_y() + bar.get_height() / 2,
                str(val),
                va="center", ha="left", color=_TEXT_PRIMARY, fontsize=9,
            )

        ax.set_yticks(y)
        ax.set_yticklabels(labels, color=_TEXT_PRIMARY, fontsize=10)
        ax.set_xlabel("Tournament Wins", color=_TEXT_MUTED, fontsize=11)
        ax.tick_params(axis="x", colors=_TEXT_MUTED, labelsize=9)
        ax.tick_params(axis="y", length=0)
        ax.set_xlim(0, max(values) * 1.18)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        for spine in ("bottom", "left"):
            ax.spines[spine].set_color(_GRID_COLOR)
        ax.grid(axis="x", color=_GRID_COLOR, linewidth=0.8, linestyle="--", alpha=0.7)
        ax.set_axisbelow(True)

    ax.set_title(
        f"Leader Tournament Wins – {latest}",
        color=_TEXT_PRIMARY, fontsize=16, fontweight="bold", pad=14, loc="left",
    )
    fig.text(0.98, 0.015, "op-tcg-leaderboard.com", ha="right", va="bottom",
             color=_TEXT_MUTED, fontsize=9)

    fig.tight_layout(rect=(0, 0.02, 1, 1))

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=_DPI, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _get_cached(path: str, render_fn) -> bytes | None:
    """Generic file-cache helper: return cached bytes or regenerate."""
    try:
        if os.path.exists(path):
            if time.time() - os.path.getmtime(path) < _CACHE_TTL_SECONDS:
                with open(path, "rb") as f:
                    return f.read()
        png = render_fn()
        os.makedirs("public", exist_ok=True)
        with open(path, "wb") as f:
            f.write(png)
        return png
    except Exception:
        logger.exception("Failed to generate OG image: %s", path)
        return None


def get_leader_og_image_bytes() -> bytes | None:
    return _get_cached(_OG_LEADER_PATH, _render_leader_chart)


def warm_leader_og_image() -> None:
    try:
        get_leader_og_image_bytes()
        logger.info("Leader OG image generated: %s", _OG_LEADER_PATH)
    except Exception:
        logger.exception("Leader OG image warm-up failed")


def get_meta_og_image_bytes() -> bytes | None:
    return _get_cached(_OG_META_PATH, _render_meta_chart)


def warm_meta_og_image() -> None:
    try:
        get_meta_og_image_bytes()
        logger.info("Meta OG image generated: %s", _OG_META_PATH)
    except Exception:
        logger.exception("Meta OG image warm-up failed")
