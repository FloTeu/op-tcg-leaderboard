from starlette.requests import Request
from starlette.responses import RedirectResponse
from op_tcg.backend.utils.environment import is_debug
from op_tcg.frontend_fasthtml.utils.seo import CANONICAL_HOST


async def canonical_redirect_middleware(request: Request, call_next):
    """Enforce a single canonical host unless local/debug.

    Skips redirects for sitemap/robots endpoints.
    """
    request_host = (request.headers.get("host") or request.url.netloc or "").strip()
    request_path = request.url.path or "/"

    # Skip in local/dev
    if request_host.startswith("localhost") or request_host.startswith("127.0.0.1") or is_debug():
        return await call_next(request)

    if CANONICAL_HOST:
        if request_host and request_host.lower() != CANONICAL_HOST.lower():
            forwarded_proto = request.headers.get("x-forwarded-proto")
            scheme = (forwarded_proto or request.url.scheme or "https").split(",")[0].strip()
            destination = f"{scheme}://{CANONICAL_HOST}{request_path}"
            if request.url.query:
                destination += f"?{request.url.query}"
            return RedirectResponse(url=destination, status_code=308)

    return await call_next(request)


