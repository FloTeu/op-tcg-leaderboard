import re
from enum import Enum

from pydantic import BaseModel


class EnumBase(Enum):
    @classmethod
    def to_list(cls) -> list[str]:
        return list(map(lambda c: c.value, cls))


def classproperty(func):
    class _ClassProperty:
        def __get__(self, instance, owner):
            return func(owner)

    return _ClassProperty()



class SQLTableBaseModel(BaseModel):

    @classproperty
    def __tablename__(cls) -> str:
        # use snake case and not just lower case
        return re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()

