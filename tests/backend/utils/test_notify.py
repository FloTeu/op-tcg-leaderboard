from unittest.mock import Mock, patch

import requests

from op_tcg.backend.utils.notify import notify_job_result


def test_notify_job_result_noop_without_topic(monkeypatch):
    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    with patch("op_tcg.backend.utils.notify.requests.post") as mock_post:
        notify_job_result("test-job", success=True, summary="42 rows")
    mock_post.assert_not_called()


def test_notify_job_result_success_posts_expected_payload(monkeypatch):
    monkeypatch.setenv("NTFY_TOPIC", "my-secret-topic")
    monkeypatch.delenv("SCRAPER_PROXY", raising=False)
    with patch("op_tcg.backend.utils.notify.requests.post") as mock_post:
        notify_job_result("test-job", success=True, summary="42 rows updated")

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "https://ntfy.sh/my-secret-topic"
    assert kwargs["data"] == b"42 rows updated"
    assert kwargs["headers"]["Title"] == "test-job: OK"
    assert kwargs["headers"]["Tags"] == "white_check_mark"
    assert kwargs["headers"]["Priority"] == "default"
    assert kwargs["proxies"] is None


def test_notify_job_result_routes_through_scraper_proxy_when_set(monkeypatch):
    monkeypatch.setenv("NTFY_TOPIC", "my-secret-topic")
    monkeypatch.setenv("SCRAPER_PROXY", "http://user:pass@proxy.webshare.io:80")
    with patch("op_tcg.backend.utils.notify.requests.post") as mock_post:
        notify_job_result("test-job", success=True, summary="ok")

    args, kwargs = mock_post.call_args
    assert kwargs["proxies"] == {
        "http": "http://user:pass@proxy.webshare.io:80",
        "https": "http://user:pass@proxy.webshare.io:80",
    }


def test_notify_job_result_failure_includes_error(monkeypatch):
    monkeypatch.setenv("NTFY_TOPIC", "my-secret-topic")
    monkeypatch.delenv("SCRAPER_PROXY", raising=False)
    with patch("op_tcg.backend.utils.notify.requests.post") as mock_post:
        notify_job_result("test-job", success=False, summary="", error="boom")

    args, kwargs = mock_post.call_args
    assert kwargs["data"] == b"Error: boom"
    assert kwargs["headers"]["Title"] == "test-job: FAILED"
    assert kwargs["headers"]["Tags"] == "rotating_light,warning"
    assert kwargs["headers"]["Priority"] == "urgent"


def test_notify_job_result_swallows_request_exceptions(monkeypatch):
    monkeypatch.setenv("NTFY_TOPIC", "my-secret-topic")
    with patch(
        "op_tcg.backend.utils.notify.requests.post",
        side_effect=requests.exceptions.ConnectionError("network down"),
    ):
        notify_job_result("test-job", success=True, summary="ok")  # must not raise


def test_notify_job_result_retries_on_429_then_succeeds(monkeypatch):
    monkeypatch.setenv("NTFY_TOPIC", "my-secret-topic")
    rate_limited = Mock(status_code=429, headers={"Retry-After": "1"})
    ok = Mock(status_code=200, headers={})
    with patch("op_tcg.backend.utils.notify.requests.post", side_effect=[rate_limited, ok]) as mock_post, \
         patch("op_tcg.backend.utils.notify.time.sleep") as mock_sleep:
        notify_job_result("test-job", success=True, summary="ok")

    assert mock_post.call_count == 2
    mock_sleep.assert_called_once_with(1.0)


def test_notify_job_result_gives_up_after_max_retries_on_429(monkeypatch):
    monkeypatch.setenv("NTFY_TOPIC", "my-secret-topic")
    rate_limited = Mock(status_code=429, headers={})
    with patch("op_tcg.backend.utils.notify.requests.post", return_value=rate_limited) as mock_post, \
         patch("op_tcg.backend.utils.notify.time.sleep") as mock_sleep:
        notify_job_result("test-job", success=True, summary="ok")  # must not raise

    assert mock_post.call_count == 3  # initial attempt + 2 retries
    assert mock_sleep.call_count == 2
