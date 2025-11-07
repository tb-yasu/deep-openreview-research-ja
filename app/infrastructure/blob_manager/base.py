from abc import ABC, abstractmethod
from functools import partial

from jinja2 import Template
from pydantic import BaseModel

from app.core.logging import log, LogLevel


class BaseBlobManager(ABC):
    def __init__(self, log_level: LogLevel = LogLevel.DEBUG) -> None:
        self.log = partial(log, log_level=log_level, subject=self.__name__)

    @property
    def __name__(self) -> str:
        return str(self.__class__.__name__)

    @abstractmethod
    def read_blob_as_bytes(self, blob_path: str) -> bytes:
        pass

    @abstractmethod
    def read_blob_as_str(self, blob_path: str) -> str:
        pass

    @abstractmethod
    def read_blob_as_template(self, blob_path: str) -> Template:
        pass

    @abstractmethod
    def read_blob_as_json(
        self, blob_path: str, schema: BaseModel | None = None
    ) -> dict | list | BaseModel:
        pass

    @abstractmethod
    def read_blob_as_jsonl(
        self, blob_path: str, schema: BaseModel | None = None
    ) -> list[dict] | list[BaseModel]:
        pass

    @abstractmethod
    def save_blob_as_bytes(self, content: bytes, blob_path: str) -> None:
        pass

    @abstractmethod
    def save_blob_as_str(self, content: str, blob_path: str) -> None:
        pass

    @abstractmethod
    def save_blob_as_json(self, content: dict, blob_path: str) -> None:
        pass

    @abstractmethod
    def save_blob_as_jsonl(
        self, content: list[dict], blob_path: str, schema: BaseModel | None = None
    ) -> None:
        pass

    @abstractmethod
    def mkdir(self, blob_dir_path: str) -> None:
        pass

    @abstractmethod
    def list_blobs(self, blob_dir_path: str) -> list[str]:
        pass

    @abstractmethod
    def exists(self, blob_path: str) -> bool:
        pass
