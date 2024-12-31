import os

from op_tcg.backend.utils.utils import booleanize


def is_debug() -> bool:
    return booleanize(os.environ.get("DEBUG", ""))