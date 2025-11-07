import sys

from loguru import logger

from app.core.config import settings
from app.domain.enums import BaseEnum


class LogLevel(BaseEnum):
    TRACE = "TRACE"  # 詳細なデバッグ情報。開発時のみ有効化し、運用時は無効。
    DEBUG = "DEBUG"  # デバッグ用情報。問題調査時に有効化、運用時は無効。
    INFO = "INFO"  # システムの通常動作を記録。常時有効。
    WARNING = (
        "WARNING"  # 注意が必要な事象。運用監視で確認し、3回/分の発生でアラート発生。
    )
    ERROR = "ERROR"  # 処理失敗や例外発生。即時調査・対応が必要。1回/分の発生でアラート発生。
    CRITICAL = "CRITICAL"  # システム停止や重大障害。即時対応・復旧作業が必要。1回/分の発生でアラート発生。


def set_logger() -> None:
    logger.remove()
    logger.add(sys.stdout, level=settings.LOG_LEVEL)


def log(log_level: LogLevel, subject: str, object: str, message: str) -> None:
    logger.log(log_level.value, f"[{subject}] {object} | {message}")
