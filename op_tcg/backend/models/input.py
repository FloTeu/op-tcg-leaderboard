import datetime
from enum import StrEnum, auto
from datetime import datetime

from pydantic import BaseModel, Field

from op_tcg.backend.models.base import EnumBase


class MetaFormatRegion(EnumBase, StrEnum):
    ASIA = auto()
    WEST = auto()
    ALL = auto()

class MetaFormat(EnumBase, StrEnum):
    # Note: must be in the right order for some frontend functionality
    OP01 = "OP01"
    OP02 = "OP02"
    OP03 = "OP03"
    OP04 = "OP04"
    OP05 = "OP05"
    OP06 = "OP06"
    OP07 = "OP07"
    OP08 = "OP08"
    OP09 = "OP09"
    OP10 = "OP10"
    OP11 = "OP11"
    OP12 = "OP12"
    OP13 = "OP13"
    OP14 = "OP14"
    OP15 = "OP15"
    OP16 = "OP16"
    OP17 = "OP17"
    OP18 = "OP18"

    @classmethod
    def to_list(cls, only_after_release: bool = True, until_meta_format: str | None = None, region: MetaFormatRegion = MetaFormatRegion.WEST) -> list[str]:
        """
        Get a list of meta format values.
        
        Args:
            only_after_release: If True, only include meta formats that have been released
            until_meta_format: If specified, only include meta formats up to this one
            region: The region to use for release date checking (WEST, ASIA, or ALL). 
                   Defaults to WEST for backward compatibility.
        
        Returns:
            List of meta format strings
        """
        all_meta_formats = list(map(lambda c: c.value, cls))
        if until_meta_format is not None:
            until_meta_format_i = all_meta_formats.index(cls(until_meta_format))
            all_meta_formats = all_meta_formats[:until_meta_format_i+1]
        return_meta_formats = []
        for meta_format in all_meta_formats:
            if not only_after_release:
                return_meta_formats.append(meta_format)
            elif meta_format2release_datetime(meta_format, region) and (
                    meta_format2release_datetime(meta_format, region) <= datetime.now()):
                return_meta_formats.append(meta_format)
        return return_meta_formats

    @classmethod
    def latest_meta_format(cls, only_after_release: bool = True) -> "MetaFormat":
        return cls.to_list(only_after_release=only_after_release)[-1]



class LimitlessMatch(BaseModel):
    leader_name: str = Field(description="The op tcg leader name")
    leader_id: str = Field(description="The op tcg leader id e.g. OP03-099")
    num_matches: int = Field(description="Total number of matches")
    score_win: int = Field(
        description="Number of matches won. its the first digit of the score string e.g. 31 - 35 - 0 -> 31")
    score_lose: int = Field(
        description="Number of matches lost. its the second digit of the score string e.g. 31 - 35 - 0 -> 35")
    score_draw: int = Field(
        description="Number of matches draw. its the third digit of the score string e.g. 31 - 35 - 0 -> 0")
    win_rate: float = Field(description="Ratio of games won. Number should be between 0 and 1.")


class LimitlessLeaderMetaDoc(BaseModel):
    leader_id: str = Field(description="The op tcg leader id e.g. OP03-099")
    meta_format: MetaFormat = Field(description="Meta in which matches happened, e.g. OP06")
    matches: list[LimitlessMatch] = Field(description="List of matches between this leader with all others")


class AllLeaderMetaDocs(BaseModel):
    documents: list[LimitlessLeaderMetaDoc]


def meta_format2release_datetime(meta_format: MetaFormat, region: MetaFormatRegion = MetaFormatRegion.WEST) -> datetime | None:
    """
    Get the release datetime for a meta format in a specific region.
    
    Args:
        meta_format: The meta format to get release date for
        region: The region (WEST, ASIA, or ALL). Defaults to WEST for backward compatibility.
                If ALL is specified, returns the earliest release date (Japanese).
    
    Returns:
        datetime object for the release date, or None if not available
        
    """
    # Japanese release dates
    # TODO: include correct datetime (only approximated right now)
    japanese_releases = {
        MetaFormat.OP01: datetime(2022, 9, 2),     # 3 months earlier
        MetaFormat.OP02: datetime(2022, 12, 10),   # 3 months earlier  
        MetaFormat.OP03: datetime(2023, 3, 30),    # 3 months earlier
        MetaFormat.OP04: datetime(2023, 6, 22),    # 3 months earlier
        MetaFormat.OP05: datetime(2023, 9, 8),     # 3 months earlier
        MetaFormat.OP06: datetime(2023, 12, 8),    # 3 months earlier
        MetaFormat.OP07: datetime(2024, 3, 28),    # 3 months earlier
        MetaFormat.OP08: datetime(2024, 6, 13),    # 3 months earlier
        MetaFormat.OP09: datetime(2024, 9, 13),    # 3 months earlier
        MetaFormat.OP10: datetime(2024, 12, 21),   # 3 months earlier
        MetaFormat.OP11: datetime(2025, 3, 6),     # 3 months earlier
        MetaFormat.OP12: datetime(2025, 5, 31),    # 3 months earlier
        MetaFormat.OP13: datetime(2025, 8, 23),    # 3 months earlier
    }
    
    # Western release dates (existing dates)
    western_releases = {
        MetaFormat.OP01: datetime(2022, 12, 2),
        MetaFormat.OP02: datetime(2023, 3, 10),
        MetaFormat.OP03: datetime(2023, 6, 30),
        MetaFormat.OP04: datetime(2023, 9, 22),
        MetaFormat.OP05: datetime(2023, 12, 8),
        MetaFormat.OP06: datetime(2024, 3, 8),
        MetaFormat.OP07: datetime(2024, 6, 28),
        MetaFormat.OP08: datetime(2024, 9, 13),
        MetaFormat.OP09: datetime(2024, 12, 13),
        MetaFormat.OP10: datetime(2025, 3, 21),
        MetaFormat.OP11: datetime(2025, 6, 6),
        MetaFormat.OP12: datetime(2025, 8, 29),
        MetaFormat.OP13: datetime(2025, 11, 7),
    }
    
    if region == MetaFormatRegion.ASIA:
        return japanese_releases.get(meta_format)
    elif region == MetaFormatRegion.WEST:
        return western_releases.get(meta_format)
    elif region == MetaFormatRegion.ALL:
        # Return the earliest release date (Japanese)
        return japanese_releases.get(meta_format)
    else:
        return None

def get_meta_format_by_datetime(dt: datetime, region: MetaFormatRegion = MetaFormatRegion.WEST) -> MetaFormat:
    """
    Returns the matching meta format to given datetime for a specific region.
    
    Args:
        dt: The datetime to match
        region: The region (WEST, ASIA, or ALL). Defaults to WEST for backward compatibility.
    
    Returns:
        The meta format that was active at the given datetime
    """
    # starts with latest (released) meta format
    for meta_format in sorted(MetaFormat.to_list(only_after_release=True), reverse=True):
        if dt >= meta_format2release_datetime(meta_format, region):
            return meta_format
    raise ValueError(f"Could not match meta format to datetime: {dt} for region: {region}")