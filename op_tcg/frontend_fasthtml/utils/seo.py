import os
from typing import Optional

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


def write_static_sitemap() -> None:
    """Generate public/sitemap.xml for static serving via FastHTML static_path."""
    import datetime as _dt
    try:
        base = _sitemap_base_url()
        urls = [
            f"{base}/",
            f"{base}/leader",
            f"{base}/tournaments",
            f"{base}/card-movement",
            f"{base}/matchups",
            f"{base}/card-popularity",
            f"{base}/prices",
            f"{base}/bug-report",
        ]
        lastmod = _dt.datetime.utcnow().date().isoformat()
        lines = [
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
            "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">",
        ]
        for u in urls:
            lines.extend([
                "  <url>",
                f"    <loc>{u}</loc>",
                f"    <lastmod>{lastmod}</lastmod>",
                "    <changefreq>daily</changefreq>",
                "    <priority>0.7</priority>",
                "  </url>",
            ])
        lines.append("</urlset>")
        os.makedirs("public", exist_ok=True)
        with open("public/sitemap.xml", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception:
        # Swallow errors to avoid blocking startup; logs should be handled by caller if desired
        pass


