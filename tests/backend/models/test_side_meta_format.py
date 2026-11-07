from datetime import datetime

import pytest

from op_tcg.backend.models import input as input_module
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion, SideMetaFormat, released_side_meta_format, \
    side_meta_format2release_datetime, meta_format2side_meta_format


def _freeze_now(monkeypatch, now: datetime):
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return now
    monkeypatch.setattr(input_module, "datetime", FrozenDatetime)


@pytest.mark.parametrize("region", MetaFormatRegion.to_list())
def test_eb05_belongs_to_op17_in_all_regions(region):
    assert meta_format2side_meta_format(MetaFormat.OP17, MetaFormatRegion(region)) == SideMetaFormat.EB05
    assert side_meta_format2release_datetime(SideMetaFormat.EB05, MetaFormatRegion(region)) == datetime(2026, 10, 30)


def test_side_meta_format_is_only_released_after_its_release_date(monkeypatch):
    _freeze_now(monkeypatch, datetime(2026, 10, 29))
    assert released_side_meta_format(MetaFormat.OP17) is None
    _freeze_now(monkeypatch, datetime(2026, 10, 30))
    assert released_side_meta_format(MetaFormat.OP17) == SideMetaFormat.EB05


def test_side_meta_format_without_release_date_is_not_released():
    # EB04 has no known release date, OP16 has no side meta format
    assert released_side_meta_format(MetaFormat.OP15, MetaFormatRegion.WEST) is None
    assert released_side_meta_format(MetaFormat.OP16) is None


def test_regional_release_dates():
    assert side_meta_format2release_datetime(SideMetaFormat.EB03, MetaFormatRegion.WEST) == datetime(2026, 2, 20)
    assert side_meta_format2release_datetime(SideMetaFormat.EB03, MetaFormatRegion.ASIA) == datetime(2025, 10, 30)
    # region all uses the earliest known release
    assert side_meta_format2release_datetime(SideMetaFormat.EB02, MetaFormatRegion.ALL) == datetime(2025, 1, 25)
    assert side_meta_format2release_datetime(SideMetaFormat.EB01, MetaFormatRegion.ALL) == datetime(2024, 5, 3)
    assert side_meta_format2release_datetime(SideMetaFormat.EB01, MetaFormatRegion.ASIA) is None


@pytest.mark.parametrize("meta_format, region, expected", [
    (MetaFormat.OP06, MetaFormatRegion.WEST, SideMetaFormat.EB01),
    (MetaFormat.OP06, MetaFormatRegion.ASIA, None),
    (MetaFormat.OP10, MetaFormatRegion.ALL, SideMetaFormat.EB02),
    (MetaFormat.OP12, MetaFormatRegion.ALL, SideMetaFormat.PRB02),
    (MetaFormat.OP13, MetaFormatRegion.ASIA, SideMetaFormat.EB03),
    (MetaFormat.OP14, MetaFormatRegion.WEST, SideMetaFormat.EB03),
])
def test_released_side_meta_formats(meta_format, region, expected):
    assert released_side_meta_format(meta_format, region) == expected
