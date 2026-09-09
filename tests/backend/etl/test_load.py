import json

from op_tcg.backend.etl.load import _batch_rows_for_insert


def test_batch_rows_for_insert_empty_list():
    assert _batch_rows_for_insert([]) == []


def test_batch_rows_for_insert_single_batch_when_under_limits():
    rows = [{"a": i} for i in range(5)]
    batches = _batch_rows_for_insert(rows, max_bytes=1_000_000, max_rows=1_000)
    assert batches == [rows]


def test_batch_rows_for_insert_splits_by_row_count():
    rows = [{"a": i} for i in range(5)]
    batches = _batch_rows_for_insert(rows, max_bytes=1_000_000, max_rows=2)
    assert [len(b) for b in batches] == [2, 2, 1]
    assert [row for batch in batches for row in batch] == rows


def test_batch_rows_for_insert_splits_by_byte_size():
    # Each row serializes to a known, fixed size; force a split well before max_rows.
    rows = [{"data": "x" * 100} for _ in range(10)]
    row_size = len(json.dumps(rows[0]).encode("utf-8"))
    batches = _batch_rows_for_insert(rows, max_bytes=row_size * 3, max_rows=1_000)
    assert len(batches) > 1
    assert all(len(b) <= 3 for b in batches)
    assert [row for batch in batches for row in batch] == rows


def test_batch_rows_for_insert_oversized_single_row_is_not_dropped():
    huge_row = {"data": "x" * 1000}
    rows = [huge_row, {"data": "y"}]
    batches = _batch_rows_for_insert(rows, max_bytes=10, max_rows=1_000)
    # The oversized row still gets its own batch rather than being split or dropped
    assert sum(len(b) for b in batches) == 2
    assert huge_row in [row for batch in batches for row in batch]
