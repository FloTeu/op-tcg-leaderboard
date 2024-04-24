import re
from enum import Enum
from typing import ClassVar

from pydantic import BaseModel
from sqlmodel import SQLModel
from sqlalchemy.orm import (
    declared_attr
)

class EnumBase(Enum):
    @classmethod
    def to_list(cls):
        return list(map(lambda c: c.value, cls))



def classproperty(func):
    class _ClassProperty:
        def __get__(self, instance, owner):
            return func(owner)
    return _ClassProperty()


class BQTableBaseModel(BaseModel):

    @classproperty
    def __tablename__(cls) -> str:
        # use snake case and not just lower case
        return re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()