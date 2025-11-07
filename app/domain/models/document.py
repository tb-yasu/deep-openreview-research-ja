from pydantic import BaseModel, Field

from app.domain.enums import ManagedTaskStatus
from app.core.utils.datetime_utils import get_current_time
from app.core.utils.nano_id import NanoID, generate_id


class Document(BaseModel):
    id: NanoID = Field(title="文書ID", default_factory=generate_id)
    title: str = Field(title="タイトル")
    url: str = Field(title="URL")
    abstract: str = Field(title="アブストラクト", default="")
    authors: list[str] = Field(title="著者", default_factory=list)

    def to_string(self) -> str:
        return f"""\
<document>
    <id>{self.id}</id>
    <title>{self.title}</title>
    <link>{self.url}</link>
    <abstract>{self.abstract}</abstract>
    <authors>{", ".join(self.authors)}</authors>
</document>"""


class ManagedDocument(Document):
    task_id: NanoID = Field(title="タスクID")
    status: ManagedTaskStatus = Field(
        title="文書状況", default=ManagedTaskStatus.NOT_STARTED
    )
    summary: str | None = Field(
        title="タスク解決のための詳細要約",
        description=(
            "この文書が担当するタスクに関連する重要な知見、洞察、または解決策を、"
            "具体的かつ詳細に記述してください。"
            "要約には、文書の主な主張、根拠となるデータや理論、"
            "タスク達成に直接寄与するポイントを明確に含めてください。"
            "また、他の文書との差別化や、タスクに対する独自の貢献があれば明記してください。"
        ),
        default=None,
    )
    created_at: str = Field(default_factory=get_current_time)
    updated_at: str = Field(default_factory=get_current_time)

    def to_string(self) -> str:
        return f"""\
<document>
    <id>{self.id}</id>
    <title>{self.title}</title>
    <link>{self.url}</link>
    <abstract>{self.abstract}</abstract>
    <authors>{", ".join(self.authors)}</authors>
    <summary>{self.summary}</summary>
</document>"""
