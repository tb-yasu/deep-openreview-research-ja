import nanoid
from typing import NewType

NanoID = NewType("NanoID", str)


def generate_id(size: int = 5) -> NanoID:
    id_: str = nanoid.generate(size=size)
    return NanoID(id_)
