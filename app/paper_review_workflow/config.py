"""Configuration for PaperReviewAgent."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class LLMModel(str, Enum):
    """サポートされるLLMモデル (OpenAI GPT models only)."""
    
    GPT4O_MINI = "gpt-4o-mini"
    GPT4O = "gpt-4o"
    GPT4_TURBO = "gpt-4-turbo"


class LLMConfig:
    """LLM評価の設定."""
    
    def __init__(
        self,
        model: LLMModel = LLMModel.GPT4O_MINI,
        temperature: float = 0.0,
        max_tokens: int = 1000,
        timeout: int = 60,
    ):
        """LLMConfigを初期化.
        
        Args:
        ----
            model: 使用するLLMモデル
            temperature: サンプリング温度（0.0-1.0）
            max_tokens: 最大トークン数
            timeout: タイムアウト（秒）
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
    
    def to_dict(self) -> dict:
        """設定を辞書に変換."""
        return {
            "model": self.model.value,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
        }


@dataclass
class ScoringWeights:
    """スコアリングの重み設定."""
    
    # OpenReviewとLLMの統合重み
    openreview_weight: float = 0.4  # OpenReview評価の重み
    llm_weight: float = 0.6          # LLM評価の重み
    
    # OpenReview内のスコア重み（relevance, novelty, impactの重み）
    relevance_weight: float = 0.4   # 関連性の重み
    novelty_weight: float = 0.3     # 新規性の重み
    impact_weight: float = 0.3      # インパクトの重み
    
    # 関連性スコア計算の重み（同義語拡張に最適化）
    keyword_exact_match_weight: float = 0.3   # 完全一致の重み
    keyword_partial_match_weight: float = 0.15  # 部分一致の重み（0.1→0.15に増加）
    review_quality_weight: float = 0.25        # [未使用] レビュー評価の重み（関連性とは独立なため除外）
    
    def __post_init__(self):
        """重みの合計が1.0になることを検証."""
        # OpenReviewとLLMの重みの合計チェック
        total_integration = self.openreview_weight + self.llm_weight
        if abs(total_integration - 1.0) > 0.01:
            raise ValueError(
                f"openreview_weight + llm_weight must equal 1.0 (got {total_integration})"
            )
        
        # OpenReview内のスコア重みの合計チェック
        total_openreview = self.relevance_weight + self.novelty_weight + self.impact_weight
        if abs(total_openreview - 1.0) > 0.01:
            raise ValueError(
                f"relevance_weight + novelty_weight + impact_weight must equal 1.0 (got {total_openreview})"
            )


# デフォルト設定
DEFAULT_LLM_CONFIG = LLMConfig(
    model=LLMModel.GPT4O_MINI,
    temperature=0.0,
    max_tokens=1000,
)

DEFAULT_SCORING_WEIGHTS = ScoringWeights()

