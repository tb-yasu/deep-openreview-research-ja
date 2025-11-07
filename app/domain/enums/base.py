from enum import Enum
from collections.abc import Iterator


class BaseEnum(Enum):
    @classmethod
    def to_list(cls) -> list[str]:
        return [item.value for item in cls]

    @classmethod
    def __iter__(cls) -> Iterator[str]:
        return iter(cls.to_list())
