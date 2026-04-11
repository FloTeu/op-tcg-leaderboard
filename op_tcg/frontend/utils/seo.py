import json
import os
from typing import Optional

from fasthtml import ft
from starlette.requests import Request

# Environment-driven canonical configuration
CANONICAL_HOST: Optional[str] = os.environ.get("CANONICAL_HOST")
CANONICAL_SCHEME: str = os.environ.get("CANONICAL_SCHEME", "https")


def canonical_base(request: Request) -> str:
    """Build canonical base URL from request or env.

    - Respects X-Forwarded-Proto when present
    - Uses CANONICAL_HOST when set, otherwise the incoming Host header
    """
    forwarded_proto = request.headers.get("x-forwarded-proto")
    scheme = (forwarded_proto or request.url.scheme or CANONICAL_SCHEME or "https").split(",")[0].strip()
    host = CANONICAL_HOST or request.headers.get("host") or request.url.netloc
    host = (host or "").strip()
    return f"{scheme}://{host}"


def _sitemap_base_url() -> str:
    """Base URL for generating static files at startup (no request context)."""
    if CANONICAL_HOST:
        return f"{CANONICAL_SCHEME}://{CANONICAL_HOST}"
    port = os.environ.get("PORT", "8080")
    return f"http://localhost:{port}"


_OG_IMAGE_PATH = "/public/favicon32x23.png"


def page_head(
    title: str,
    description: str,
    canonical_url: str,
    keywords: str,
    base_url: str,
    json_ld_about: str = "One Piece TCG Competitive Data",
    og_image_url: Optional[str] = None,
) -> tuple:
    """Return a tuple of <head> elements shared by every page route.

    Covers: title, description, keywords, Open Graph, Twitter Card,
    canonical link, and JSON-LD WebPage structured data.
    """
    og_image = og_image_url or f"{base_url}{_OG_IMAGE_PATH}"
    json_ld = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "description": description,
        "url": canonical_url,
        "isPartOf": {"@type": "WebSite", "name": "OP TCG Leaderboard", "url": base_url},
        "about": {"@type": "Thing", "name": json_ld_about},
    }
    return (
        ft.Title(title),
        ft.Meta(name="description", content=description),
        ft.Meta(name="keywords", content=keywords),
        ft.Meta(property="og:title", content=title),
        ft.Meta(property="og:description", content=description),
        ft.Meta(property="og:url", content=canonical_url),
        ft.Meta(property="og:image", content=og_image),
        ft.Meta(name="twitter:title", content=title),
        ft.Meta(name="twitter:description", content=description),
        ft.Meta(name="twitter:image", content=og_image),
        ft.Link(rel="canonical", href=canonical_url),
        ft.Script(type="application/ld+json", content=json.dumps(json_ld)),
    )


def write_static_sitemap() -> None:
    """Generate public/sitemap.xml for static serving via FastHTML static_path."""
    import datetime as _dt
    try:
        base = _sitemap_base_url()
        urls = [
            (f"{base}/", "0.9"),
            (f"{base}/leader", "0.8"),
            (f"{base}/meta", "0.8"),
            (f"{base}/tournaments", "0.8"),
            (f"{base}/matchups", "0.7"),
            (f"{base}/card-movement", "0.7"),
            (f"{base}/card-popularity", "0.6"),
            (f"{base}/prices", "0.6"),
            (f"{base}/bug-report", "0.3"),
        ]
        lastmod = _dt.datetime.utcnow().date().isoformat()
        lines = [
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
            "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">",
        ]
        for u, priority in urls:
            lines.extend([
                "  <url>",
                f"    <loc>{u}</loc>",
                f"    <lastmod>{lastmod}</lastmod>",
                "    <changefreq>daily</changefreq>",
                f"    <priority>{priority}</priority>",
                "  </url>",
            ])
        lines.append("</urlset>")
        os.makedirs("public", exist_ok=True)
        with open("public/sitemap.xml", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception:
        # Swallow errors to avoid blocking startup; logs should be handled by caller if desired
        pass


