import logging
import os

import requests

_logger = logging.getLogger("notify")

_DEFAULT_NTFY_URL = "https://ntfy.sh"


def notify_job_result(job_name: str, *, success: bool, summary: str, error: str | None = None) -> None:
    """Push a one-line job-result notification to ntfy.sh.

    No-ops if NTFY_TOPIC is not set, and never raises - a notification failure
    must not fail the underlying job.
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

    try:
        requests.post(
            f"{base_url}/{topic}",
            data=body.encode("utf-8"),
            headers={"Title": title, "Tags": tags, "Priority": priority},
            timeout=5,
        )
    except requests.exceptions.RequestException as e:
        _logger.warning("Failed to send ntfy notification for %s: %s", job_name, e)
