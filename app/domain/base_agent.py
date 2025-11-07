from abc import ABC, abstractmethod
from functools import partial

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from app.core.logging import LogLevel, log


class LangGraphAgent(ABC):
    def __init__(
        self,
        log_level: LogLevel,
        checkpointer: MemorySaver | None,
        recursion_limit: int,
    ) -> None:
        self.log = partial(log, log_level=log_level, subject=self.__name__)
        self.checkpointer = checkpointer
        self.recursion_limit = recursion_limit
        self.graph = self._create_graph()

    @property
    def __name__(self) -> str:
        return str(self.__class__.__name__)

    @property
    def default_models(self) -> dict[str, str]:
        raise NotImplementedError

    @abstractmethod
    def _create_graph(self) -> CompiledStateGraph:
        raise NotImplementedError
