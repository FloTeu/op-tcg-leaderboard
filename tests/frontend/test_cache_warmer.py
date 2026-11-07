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
