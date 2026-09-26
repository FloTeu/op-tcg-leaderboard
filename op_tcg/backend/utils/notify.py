import logging
import os
import time

import requests

_logger = logging.getLogger("notify")

_DEFAULT_NTFY_URL = "https://ntfy.sh"
_MAX_RETRIES = 2
_DEFAULT_RETRY_AFTER_SECONDS = 5
_MAX_RETRY_AFTER_SECONDS = 10


def notify_job_result(job_name: str, *, success: bool, summary: str, error: str | None = None) -> None:
    """Push a one-line job-result notification to ntfy.sh.

    No-ops if NTFY_TOPIC is not set, and never raises - a notification failure
    must not fail the underlying job.

    ntfy.sh rate-limits publish requests per source IP (a small burst bucket
    that refills at 1 request/5s), and explicitly shares that budget across
    everyone behind the same IP - which includes Cloud Run/Cloud Functions'
    pooled egress IPs. Routed through SCRAPER_PROXY (the same Webshare proxy
    already used for anti-bot crawling) when set, so this leaves via a
    non-shared IP instead. A 429 is also retried a couple of times honoring
    ntfy's `Retry-After` header, since these are single end-of-job pings
    where a short delay costs nothing.
    """
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        _logger.debug("NTFY_TOPIC not set, skipping notification for %s", job_name)
        return

    base_url = os.environ.get("NTFY_URL", _DEFAULT_NTFY_URL).rstrip("/")
    title = f"{job_name}: {'OK' if success else 'FAILED'}"
    body = summary or ""
    if error:
        body = f"{body}\n\nError: {error}" if body else f"Error: {error}"
    tags = "white_check_mark" if success else "rotating_light,warning"
    priority = "default" if success else "urgent"

    url = f"{base_url}/{topic}"
    headers = {"Title": title, "Tags": tags, "Priority": priority}
    proxy_url = os.environ.get("SCRAPER_PROXY")
    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None

    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = requests.post(url, data=body.encode("utf-8"), headers=headers, timeout=5, proxies=proxies)
        except requests.exceptions.RequestException as e:
            _logger.warning("Failed to send ntfy notification for %s: %s", job_name, e)
            return

        if response.status_code != 429:
            return

        if attempt == _MAX_RETRIES:
            _logger.warning(
                "ntfy notification for %s rate-limited (429) after %d retries, giving up",
                job_name, _MAX_RETRIES,
            )
            return

        retry_after = response.headers.get("Retry-After", "")
        wait_seconds = float(retry_after) if retry_after.isdigit() else _DEFAULT_RETRY_AFTER_SECONDS
        time.sleep(min(wait_seconds, _MAX_RETRY_AFTER_SECONDS))
