"""Base class for paper review workflow nodes."""

from abc import ABC, abstractmethod
from typing import Any

from loguru import logger

from app.paper_review_workflow.models.state import PaperReviewAgentState


class BaseNode(ABC):
    """ワークフローノードの基底クラス.
    
    全てのノードはこのクラスを継承し、__call__メソッドを実装する必要があります。
    """
    
    def __init__(self) -> None:
        """ベースノードを初期化."""
        self.logger = logger
    
    @abstractmethod
    def __call__(self, state: PaperReviewAgentState) -> dict[str, Any]:
        """ノードの処理を実行.
        
        Args:
        ----
            state: 現在のワークフロー状態
            
        Returns:
        -------
            更新する状態の辞書
        """
        raise NotImplementedError
    
    @property
    def name(self) -> str:
        """ノードの名前を取得."""
        return self.__class__.__name__
    
    def log_start(self, message: str) -> None:
        """ノード開始ログを出力."""
        self.logger.info(f"[{self.name}] {message}")
    
    def log_success(self, message: str) -> None:
        """ノード成功ログを出力."""
        self.logger.success(f"[{self.name}] {message}")
    
    def log_error(self, message: str) -> None:
        """ノードエラーログを出力."""
        self.logger.error(f"[{self.name}] {message}")
    
    def log_warning(self, message: str) -> None:
        """ノード警告ログを出力."""
        self.logger.warning(f"[{self.name}] {message}")
    
    def log_debug(self, message: str) -> None:
        """ノードデバッグログを出力."""
        self.logger.debug(f"[{self.name}] {message}")

