import re
from types import SimpleNamespace
from unittest.mock import MagicMock

from google.api_core.exceptions import NotFound

from op_tcg.backend.etl.views import MANAGED_VIEWS, SQL_VIEWS_DIR, ensure_managed_views, load_view_sql
from op_tcg.backend.models.bq_enums import BQDataset

_DATASETS = "|".join(d.value for d in BQDataset)
_TABLE_REF = re.compile(rf"\b({_DATASETS})\.(\w+)\b")


def test_every_sql_file_is_managed_and_vice_versa():
    files = {p.stem for p in SQL_VIEWS_DIR.glob("*.sql")}
    managed = {f"{dataset}.{view_name}" for dataset, view_name in MANAGED_VIEWS}
    assert files == managed


def test_views_are_ordered_after_their_view_dependencies():
    managed = [f"{dataset}.{view_name}" for dataset, view_name in MANAGED_VIEWS]
    for i, view in enumerate(managed):
        dataset, view_name = view.split(".")
        refs = {".".join(m) for m in _TABLE_REF.findall(load_view_sql(BQDataset(dataset), view_name))}
        for ref in refs & set(managed):
            assert managed.index(ref) < i, f"{view} references {ref}, which must be created first"


def test_view_sql_is_project_independent():
    for dataset, view_name in MANAGED_VIEWS:
        assert "op-tcg-leaderboard" not in load_view_sql(dataset, view_name)


def _fake_client(existing: dict[str, str]):
    client = MagicMock(project="proj")

    def get_table(view_id):
        if view_id not in existing:
            raise NotFound(view_id)
        return SimpleNamespace(view_query=existing[view_id])

    client.get_table.side_effect = get_table
    return client


def _all_views_in_sync() -> dict[str, str]:
    return {f"proj.{d}.{v}": load_view_sql(d, v) + ";\n" for d, v in MANAGED_VIEWS}


def test_unchanged_views_are_skipped():
    client = _fake_client(_all_views_in_sync())
    assert ensure_managed_views(client) == []
    client.query.assert_not_called()


def test_changed_and_missing_views_are_replaced():
    existing = _all_views_in_sync()
    existing["proj.leaders.leader_extended"] = "SELECT 1"
    del existing["proj.cards.card_popularity"]
    client = _fake_client(existing)

    changed = ensure_managed_views(client)

    assert changed == ["proj.leaders.leader_extended", "proj.cards.card_popularity"]
    queries = [c.args[0] for c in client.query.call_args_list]
    assert queries[0].startswith("CREATE OR REPLACE VIEW `proj.leaders.leader_extended` AS\n")
    assert queries[0].endswith(load_view_sql(BQDataset.LEADERS, "leader_extended"))


def test_dry_run_reports_without_changing():
    existing = _all_views_in_sync()
    existing["proj.matches.leader_win_rate"] = "SELECT 1"
    client = _fake_client(existing)

    assert ensure_managed_views(client, dry_run=True) == ["proj.matches.leader_win_rate"]
    client.query.assert_not_called()
