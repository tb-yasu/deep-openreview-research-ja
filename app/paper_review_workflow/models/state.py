"""State management for Paper Review Agent."""

import operator
from typing import Annotated, Any

from pydantic import BaseModel, Field


class Paper(BaseModel):
    """論文の基本情報を表すモデル."""
    
    id: str = Field(title="論文ID")
    title: str = Field(title="論文タイトル")
    authors: list[str] = Field(default_factory=list, title="著者リスト")
    abstract: str = Field(default="", title="アブストラクト")
    keywords: list[str] = Field(default_factory=list, title="キーワードリスト")
    venue: str = Field(title="学会名")
    year: int = Field(title="開催年")
    pdf_url: str = Field(title="PDF URL")
    forum_url: str = Field(title="フォーラムURL")
    
    # レビューデータ（fetch_all_papers.pyで取得済みの場合に含まれる）
    reviews: list[dict[str, Any]] = Field(default_factory=list, title="レビューリスト")
    rating_avg: float | None = Field(default=None, title="平均評価")
    confidence_avg: float | None = Field(default=None, title="平均confidence")
    decision: str | None = Field(default=None, title="採択判定")
    
    # 追加のOpenReview情報
    meta_review: str | None = Field(default=None, title="メタレビュー（エリアチェアのまとめ）")
    author_remarks: str | None = Field(default=None, title="著者の最終コメント")
    decision_comment: str | None = Field(default=None, title="採択判定の詳細コメント")


class EvaluatedPaper(Paper):
    """評価済み論文の情報を表すモデル."""
    
    # 統合LLM評価スコア（新システム）
    relevance_score: float | None = Field(
        default=None,
        title="関連性スコア",
        description="ユーザーの研究興味との関連性（0.0-1.0）",
    )
    novelty_score: float | None = Field(
        default=None,
        title="新規性スコア",
        description="研究の新規性・独創性（0.0-1.0）",
    )
    impact_score: float | None = Field(
        default=None,
        title="インパクトスコア",
        description="研究の潜在的影響力（0.0-1.0）",
    )
    practicality_score: float | None = Field(
        default=None,
        title="実用性スコア",
        description="実際の応用可能性（0.0-1.0）",
    )
    overall_score: float | None = Field(
        default=None,
        title="総合スコア",
        description="4つのスコアの重み付き平均（0.0-1.0）",
    )
    
    # 統合LLM評価による追加情報
    review_summary: str | None = Field(
        default=None,
        title="レビュー要約",
        description="OpenReviewレビューの統合要約",
    )
    field_insights: str | None = Field(
        default=None,
        title="フィールド活用の説明",
        description="どのレビューフィールドを主に使用したかの説明",
    )
    ai_rationale: str | None = Field(
        default=None,
        title="AI評価の根拠",
        description="AIによる評価の詳細な理由（2-3文）",
    )
    
    # 旧システムとの互換性維持
    evaluation_rationale: str = Field(
        default="",
        title="評価理由（旧）",
        description="スコアの根拠となる詳細な理由（後方互換性のため残す）",
    )
    citation_count: int | None = Field(
        default=None,
        title="被引用数",
        description="Semantic Scholarでの被引用数",
    )
    
    # 旧LLM評価スコア（後方互換性のため残す）
    llm_relevance_score: float | None = Field(
        default=None,
        title="LLM関連性スコア（旧）",
        description="旧システムのLLM関連性スコア（0.0-1.0）",
    )
    llm_novelty_score: float | None = Field(
        default=None,
        title="LLM新規性スコア（旧）",
        description="旧システムのLLM新規性スコア（0.0-1.0）",
    )
    llm_practical_score: float | None = Field(
        default=None,
        title="LLM実用性スコア（旧）",
        description="旧システムのLLM実用性スコア（0.0-1.0）",
    )
    llm_rationale: str | None = Field(
        default=None,
        title="LLM評価理由（旧）",
        description="旧システムのLLM評価理由",
    )
    final_score: float | None = Field(
        default=None,
        title="最終スコア（旧）",
        description="旧システムの最終スコア（0.0-1.0）",
    )
    rank: int | None = Field(
        default=None,
        title="ランク",
        description="論文のランク（1から始まる）",
    )


class EvaluationCriteria(BaseModel):
    """論文評価の基準を表すモデル."""
    
    research_description: str | None = Field(
        default=None,
        title="研究興味の説明",
        description="自然言語でのユーザーの研究興味の説明",
    )
    research_interests: list[str] = Field(
        default_factory=list,
        title="研究興味キーワード",
        description="ユーザーの研究興味・関心領域のキーワードリスト（省略時はresearch_descriptionから抽出）",
    )
    min_relevance_score: float = Field(
        default=0.5,
        title="最小関連性スコア",
        description="論文を有益と判断する最小の関連性スコア（0.0-1.0）",
    )
    min_rating: float | None = Field(
        default=None,
        title="最小レビュー評価",
        description="論文の最小OpenReview評価スコア（任意）",
    )
    min_citations: int | None = Field(
        default=None,
        title="最小引用数",
        description="論文の最小被引用数（任意）",
    )
    focus_on_novelty: bool = Field(
        default=True,
        title="新規性重視",
        description="新規性を重視するかどうか",
    )
    focus_on_impact: bool = Field(
        default=True,
        title="インパクト重視",
        description="インパクトを重視するかどうか",
    )
    top_k_papers: int | None = Field(
        default=None,
        title="上位論文数",
        description="LLM評価する上位論文の数（Noneの場合は閾値のみでフィルタリング）",
    )
    enable_preliminary_llm_filter: bool = Field(
        default=False,
        title="簡易LLMフィルタ有効化",
        description="top-k選択前に簡易LLM評価でrelevance_scoreを再計算するかどうか",
    )
    preliminary_llm_filter_count: int = Field(
        default=500,
        title="簡易LLMフィルタ対象数",
        description="簡易LLM評価する候補論文数（上位N件を評価して精度を向上）",
    )


class PaperReviewAgentInputState(BaseModel):
    """PaperReviewAgentの入力状態."""
    
    venue: str = Field(
        title="学会名",
        description="検索対象の学会名（例: 'NeurIPS', 'ICML', 'ICLR'）",
    )
    year: int = Field(
        title="開催年",
        description="検索対象の開催年（例: 2024）",
    )
    keywords: str | None = Field(
        default=None,
        title="検索キーワード",
        description="論文の絞り込み用キーワード（任意）",
    )
    max_papers: int = Field(
        default=50,
        title="最大論文数",
        description="検索する最大論文数",
    )
    accepted_only: bool = Field(
        default=True,
        title="採択論文のみ",
        description="採択論文のみを検索対象にする（デフォルト: True）",
    )
    evaluation_criteria: EvaluationCriteria = Field(
        default_factory=EvaluationCriteria,
        title="評価基準",
        description="論文を評価する基準",
    )


class PaperReviewAgentPrivateState(BaseModel):
    """PaperReviewAgentの内部状態."""
    
    papers: list[Paper] = Field(
        default_factory=list,
        title="検索された論文リスト",
    )
    evaluated_papers: Annotated[list[EvaluatedPaper], operator.add] = Field(
        default_factory=list,
        title="評価済み論文リスト",
    )
    ranked_papers: list[EvaluatedPaper] = Field(
        default_factory=list,
        title="ランク付けされた論文リスト",
    )
    llm_evaluated_papers: list[EvaluatedPaper] = Field(
        default_factory=list,
        title="LLM評価済み論文リスト",
    )
    re_ranked_papers: list[EvaluatedPaper] = Field(
        default_factory=list,
        title="LLMスコアで再ランク付けされた論文リスト",
    )
    synonyms: dict[str, list[str]] = Field(
        default_factory=dict,
        title="キーワード同義語辞書",
        description="各キーワードとその同義語のマッピング（キー: キーワード、値: 同義語リスト）",
    )
    error_messages: Annotated[list[str], operator.add] = Field(
        default_factory=list,
        title="エラーメッセージリスト",
    )


class PaperReviewAgentOutputState(BaseModel):
    """PaperReviewAgentの出力状態."""
    
    paper_report: str | None = Field(
        default=None,
        title="論文レビューレポート",
        description=(
            "検索・評価された論文に基づいて生成された最終レポート。"
            "上位の有益な論文の概要、評価理由、推奨事項などが含まれます。"
        ),
    )
    top_papers: list[dict[str, Any]] = Field(
        default_factory=list,
        title="トップ論文リスト",
        description="評価スコアが高い上位論文のリスト",
    )


class PaperReviewAgentState(
    PaperReviewAgentInputState,
    PaperReviewAgentPrivateState,
    PaperReviewAgentOutputState,
):
    """PaperReviewAgentの完全な状態."""
    pass

