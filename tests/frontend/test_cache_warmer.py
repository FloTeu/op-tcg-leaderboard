from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion, SideMetaFormat
from op_tcg.frontend.utils import cache_warmer
from op_tcg.frontend.utils.cache_warmer import CacheWarmer


def test_side_meta_format_leaderboard_is_warmed_right_after_leader_extended(monkeypatch):
    calls = []
    monkeypatch.setattr(cache_warmer.MetaFormat, "latest_meta_format", classmethod(lambda cls, **_: MetaFormat.OP17))
    monkeypatch.setattr(cache_warmer, "released_side_meta_format",
                        lambda mf, region: SideMetaFormat.EB05 if mf == MetaFormat.OP17 else None)
    monkeypatch.setattr(cache_warmer, "get_side_meta_format_leader_extended", lambda *args: calls.append(args))

    tasks = CacheWarmer(warm_interval_hours=1).get_cache_warming_tasks()
    for task in tasks[1:4]:
        task()

    assert calls == [(MetaFormat.OP17, SideMetaFormat.EB05, MetaFormatRegion(region)) for region in MetaFormatRegion.to_list()]


def test_no_side_meta_format_tasks_without_released_side_meta_format(monkeypatch):
    monkeypatch.setattr(cache_warmer, "released_side_meta_format", lambda mf, region: None)
    tasks = CacheWarmer(warm_interval_hours=1).get_cache_warming_tasks()
    # leader_extended is followed directly by the static leader data
    assert tasks[1].__code__.co_names == ("get_leader_data",)


def test_periodic_warming_disabled_with_non_positive_interval(monkeypatch):
    warmer = CacheWarmer(warm_interval_hours=0)
    cycles = []
    monkeypatch.setattr(warmer, "warm_cache_sync", lambda: cycles.append(1))

    warmer.start_background_warming()
    warmer.executor.shutdown(wait=True)

    # No background thread was started, so no cycle ran and the loop could not spin
    assert not warmer.is_running
    assert cycles == []


def test_background_warming_waits_for_interval_before_first_cycle(monkeypatch):
    # The initial warm-up runs synchronously at app startup, so the loop must not repeat it
    warmer = CacheWarmer(warm_interval_hours=1)
    cycles = []
    monkeypatch.setattr(warmer, "warm_cache_sync", lambda: cycles.append(1))

    warmer.start_background_warming()
    warmer.stop_background_warming()

    assert cycles == []


def _patch_token_claims(monkeypatch, claims=None, error=None):
    def verify(token, request, audience):
        if error:
            raise error
        assert (token, audience) == ("tok", "https://svc.run.app")
        return claims
    monkeypatch.setattr(cache_warmer.id_token, "verify_oauth2_token", verify)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "proj")


def test_warm_request_authorized_for_scheduler_service_account(monkeypatch):
    _patch_token_claims(monkeypatch, {"email": "cloud-function-sa@proj.iam.gserviceaccount.com", "email_verified": True})
    assert cache_warmer.is_authorized_warm_request("Bearer tok", "https://svc.run.app")


def test_warm_request_rejected_for_other_service_account(monkeypatch):
    _patch_token_claims(monkeypatch, {"email": "attacker@evil.iam.gserviceaccount.com", "email_verified": True})
    assert not cache_warmer.is_authorized_warm_request("Bearer tok", "https://svc.run.app")


def test_warm_request_rejected_for_invalid_token(monkeypatch):
    _patch_token_claims(monkeypatch, error=ValueError("Token has wrong audience"))
    assert not cache_warmer.is_authorized_warm_request("Bearer tok", "https://svc.run.app")


def test_warm_request_rejected_without_bearer_token():
    assert not cache_warmer.is_authorized_warm_request(None, "https://svc.run.app")
    assert not cache_warmer.is_authorized_warm_request("Basic abc", "https://svc.run.app")
