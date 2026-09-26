from unittest.mock import patch

import requests

from op_tcg.backend.utils.notify import notify_job_result


def test_notify_job_result_noop_without_topic(monkeypatch):
    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    with patch("op_tcg.backend.utils.notify.requests.post") as mock_post:
        notify_job_result("test-job", success=True, summary="42 rows")
    mock_post.assert_not_called()


def test_notify_job_result_success_posts_expected_payload(monkeypatch):
    monkeypatch.setenv("NTFY_TOPIC", "my-secret-topic")
    with patch("op_tcg.backend.utils.notify.requests.post") as mock_post:
        notify_job_result("test-job", success=True, summary="42 rows updated")

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "https://ntfy.sh/my-secret-topic"
    assert kwargs["data"] == b"42 rows updated"
    assert kwargs["headers"]["Title"] == "test-job: OK"
    assert kwargs["headers"]["Tags"] == "white_check_mark"
    assert kwargs["headers"]["Priority"] == "default"


def test_notify_job_result_failure_includes_error(monkeypatch):
    monkeypatch.setenv("NTFY_TOPIC", "my-secret-topic")
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
