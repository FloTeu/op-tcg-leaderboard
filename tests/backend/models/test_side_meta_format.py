from datetime import datetime

import pytest

from op_tcg.backend.models import input as input_module
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion, SideMetaFormat, released_side_meta_format, \
    side_meta_format2release_datetime, meta_format2side_meta_format, meta_format2release_datetime, \
    GLOBAL_SIDE_META_FORMAT_RELEASES


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
    # EB04 has no known west release date, OP16 has no side meta format
    assert released_side_meta_format(MetaFormat.OP15, MetaFormatRegion.WEST) is None
    assert released_side_meta_format(MetaFormat.OP16) is None


def test_regional_release_dates():
    assert side_meta_format2release_datetime(SideMetaFormat.EB03, MetaFormatRegion.WEST) == datetime(2026, 2, 20)
    assert side_meta_format2release_datetime(SideMetaFormat.EB03, MetaFormatRegion.ASIA) == datetime(2025, 10, 30)
    # region all uses the earliest known release
    assert side_meta_format2release_datetime(SideMetaFormat.EB02, MetaFormatRegion.ALL) == datetime(2025, 1, 25)
    assert side_meta_format2release_datetime(SideMetaFormat.EB01, MetaFormatRegion.ALL) == datetime(2024, 1, 27)
    assert side_meta_format2release_datetime(SideMetaFormat.EB04, MetaFormatRegion.WEST) is None


@pytest.mark.parametrize("meta_format, region, expected", [
    (MetaFormat.OP06, MetaFormatRegion.WEST, SideMetaFormat.EB01),
    (MetaFormat.OP06, MetaFormatRegion.ASIA, SideMetaFormat.EB01),
    (MetaFormat.OP14, MetaFormatRegion.ASIA, SideMetaFormat.EB04),
    (MetaFormat.OP10, MetaFormatRegion.ALL, SideMetaFormat.EB02),
    (MetaFormat.OP12, MetaFormatRegion.ALL, SideMetaFormat.PRB02),
    (MetaFormat.OP13, MetaFormatRegion.ASIA, SideMetaFormat.EB03),
    (MetaFormat.OP14, MetaFormatRegion.WEST, SideMetaFormat.EB03),
])
def test_released_side_meta_formats(meta_format, region, expected):
    assert released_side_meta_format(meta_format, region) == expected


@pytest.mark.parametrize("side_meta_format", list(GLOBAL_SIDE_META_FORMAT_RELEASES))
def test_global_side_meta_formats_share_mapping_and_date_in_all_regions(side_meta_format):
    meta_format, release = GLOBAL_SIDE_META_FORMAT_RELEASES[side_meta_format]
    for region in MetaFormatRegion:
        assert meta_format2side_meta_format(meta_format, region) == side_meta_format
        assert side_meta_format2release_datetime(side_meta_format, region) == release


@pytest.mark.parametrize("region", [MetaFormatRegion.WEST, MetaFormatRegion.ASIA])
def test_side_meta_formats_are_released_within_their_meta_format(region):
    """Catches wrong mappings or dates: the release must lie between the main meta format release and the next one."""
    all_meta_formats = MetaFormat.to_list(only_after_release=False)
    for i, meta_format in enumerate(all_meta_formats):
        side_meta_format = meta_format2side_meta_format(MetaFormat(meta_format), region)
        release = side_meta_format and side_meta_format2release_datetime(side_meta_format, region)
        if not release:
            continue
        meta_format_release = meta_format2release_datetime(MetaFormat(meta_format), region)
        if meta_format_release:
            assert meta_format_release <= release, f"{side_meta_format} released before {meta_format} in {region}"
        next_release = meta_format2release_datetime(MetaFormat(all_meta_formats[i + 1]), region) if i + 1 < len(all_meta_formats) else None
        if next_release:
            assert release < next_release, f"{side_meta_format} released after the end of {meta_format} in {region}"


@pytest.mark.parametrize("meta_format, release", [
    (MetaFormat.OP17, datetime(2026, 8, 28)),
    (MetaFormat.OP18, datetime(2026, 11, 20)),
])
def test_global_meta_format_release_is_the_same_in_all_regions(meta_format, release):
    for region in MetaFormatRegion:
        assert meta_format2release_datetime(meta_format, region) == release
