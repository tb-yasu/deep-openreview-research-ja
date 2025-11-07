import json
from pathlib import Path

from jinja2 import Template
from pydantic import BaseModel

from app.core.logging import LogLevel
from app.infrastructure.blob_manager.base import BaseBlobManager


class LocalBlobManager(BaseBlobManager):
    def __init__(self, log_level: LogLevel = LogLevel.TRACE) -> None:
        super().__init__(log_level)

    def read_blob_as_bytes(self, blob_path: str) -> bytes:
        self.log(object="read_blob_as_bytes", message=blob_path)
        with open(blob_path, "rb") as fi:
            return fi.read()

    def read_blob_as_str(self, blob_path: str) -> str:
        self.log(object="read_blob_as_str", message=blob_path)
        with open(blob_path, encoding="utf-8") as fi:
            return fi.read()

    def read_blob_as_template(self, blob_path: str) -> Template:
        self.log(object="read_blob_as_template", message=blob_path)
        return Template(source=self.read_blob_as_str(blob_path))

    def read_blob_as_json(
        self, blob_path: str, schema: BaseModel | None = None
    ) -> dict | list:
        self.log(object="read_blob_as_json", message=blob_path)
        with open(blob_path, encoding="utf-8") as fi:
            if schema:
                return schema.model_validate_json(fi.read())  # type: ignore
            return json.load(fi)  # type: ignore

    def read_blob_as_jsonl(
        self, blob_path: str, schema: BaseModel | None = None
    ) -> list[dict] | list[BaseModel]:
        self.log(object="read_blob_as_jsonl", message=blob_path)
        with open(blob_path, encoding="utf-8") as fi:
            if isinstance(schema, BaseModel):
                return [schema.model_validate_json(line) for line in fi]
            return [json.loads(line) for line in fi]

    def save_blob_as_bytes(self, content: bytes, blob_path: str) -> None:
        self.log(object="save_blob_as_bytes", message=blob_path)
        with open(blob_path, "wb") as fo:
            fo.write(content)

    def save_blob_as_str(self, content: str, blob_path: str) -> None:
        self.log(object="save_blob_as_str", message=blob_path)
        with open(blob_path, "w", encoding="utf-8") as fo:
            fo.write(content)

    def save_blob_as_json(self, content: dict, blob_path: str) -> None:
        self.log(object="save_blob_as_json", message=blob_path)
        with open(blob_path, "w", encoding="utf-8") as fo:
            json.dump(content, fo, ensure_ascii=False, indent=4)

    def save_blob_as_jsonl(
        self, content: list[dict], blob_path: str, schema: BaseModel | None = None
    ) -> None:
        self.log(object="save_blob_as_jsonl", message=blob_path)
        with open(blob_path, "w", encoding="utf-8") as fo:
            for line in content:
                if schema:
                    obj = schema.model_validate(line)
                    fo.write(obj.model_dump_json(ensure_ascii=False) + "\n")
                else:
                    fo.write(json.dumps(line, ensure_ascii=False) + "\n")

    def mkdir(self, blob_dir_path: str) -> None:
        self.log(object="mkdir", message=blob_dir_path)
        Path(blob_dir_path).mkdir(parents=True, exist_ok=True)

    def list_blobs(self, blob_dir_path: str) -> list[str]:
        self.log(object="list_blobs", message=blob_dir_path)
        return list(Path(blob_dir_path).iterdir())

    def exists(self, blob_path: str) -> bool:
        self.log(object="exists", message=blob_path)
        return Path(blob_path).exists()
