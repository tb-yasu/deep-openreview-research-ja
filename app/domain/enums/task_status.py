from app.domain.enums.base import BaseEnum


class TaskStatus(BaseEnum):
    COMPLETED = "completed"  # 完了
    FAILED = "failed"  # 失敗
    PENDING = "pending"  # 保留


class ManagedTaskStatus(BaseEnum):
    NOT_STARTED = "not_started"  # 未開始
    IN_PROGRESS = "in_progress"  # 進行中
    COMPLETED = TaskStatus.COMPLETED.value  # 完了
    PENDING = TaskStatus.PENDING.value  # 保留
    FAILED = TaskStatus.FAILED.value  # 失敗
