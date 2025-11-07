from abc import ABC, abstractmethod
from functools import partial

from langgraph.types import Command
from pydantic import BaseModel

from app.core.logging import log, LogLevel


class BaseChain(ABC):
    def __init__(
        self,
        log_level: LogLevel,
    ) -> None:
        self.log = partial(log, log_level=log_level, subject=self.__name__)

    @property
    def __name__(self) -> str:
        return str(self.__class__.__name__)

    @abstractmethod
    def __call__(self, state: BaseModel) -> Command:
        raise NotImplementedError
