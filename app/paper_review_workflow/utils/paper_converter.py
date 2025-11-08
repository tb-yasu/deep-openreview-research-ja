"""Utility functions for converting paper objects to dictionaries."""

from typing import Any

from app.paper_review_workflow.models.state import EvaluatedPaper


def convert_paper_to_dict(
    paper: EvaluatedPaper,
    rank: int | None = None,
    include_llm_scores: bool = False,
) -> dict[str, Any]:
    """論文オブジェクトを辞書形式に変換.
    
    Args:
    ----
        paper: 評価済み論文オブジェクト
        rank: ランク番号（省略可）
        include_llm_scores: LLM評価スコアを含めるかどうか
        
    Returns:
    -------
        論文情報の辞書
    """
    paper_dict: dict[str, Any] = {
        "id": paper.id,
        "title": paper.title,
        "authors": paper.authors,
        "abstract": paper.abstract,
        "keywords": paper.keywords,
        "overall_score": paper.overall_score,
        "relevance_score": paper.relevance_score,
        "novelty_score": paper.novelty_score,
        "impact_score": paper.impact_score,
        "practicality_score": paper.practicality_score,  # 統合LLM評価
        "rating_avg": paper.rating_avg,
        "reviews": paper.reviews,
        "decision": paper.decision,
        "forum_url": paper.forum_url,
        "pdf_url": paper.pdf_url,
        "evaluation_rationale": paper.evaluation_rationale,
        # 統合LLM評価の新フィールド
        "review_summary": paper.review_summary,
        "field_insights": paper.field_insights,
        "ai_rationale": paper.ai_rationale,
        # OpenReview詳細情報
        "meta_review": paper.meta_review,
        "decision_comment": paper.decision_comment,
        "author_remarks": paper.author_remarks,
    }
    
    # ランクがある場合は追加
    if rank is not None:
        paper_dict["rank"] = rank
    
    # LLMスコアを含める場合
    if include_llm_scores:
        paper_dict.update({
            "llm_relevance_score": paper.llm_relevance_score,
            "llm_novelty_score": paper.llm_novelty_score,
            "llm_practical_score": paper.llm_practical_score,
            "final_score": paper.final_score,
            "llm_rationale": paper.llm_rationale,
        })
    
    return paper_dict


def convert_papers_to_dict_list(
    papers: list[EvaluatedPaper],
    max_count: int | None = None,
    include_llm_scores: bool = False,
) -> list[dict[str, Any]]:
    """論文リストを辞書のリストに変換.
    
    Args:
    ----
        papers: 評価済み論文のリスト
        max_count: 最大変換数（省略時は全て変換）
        include_llm_scores: LLM評価スコアを含めるかどうか
        
    Returns:
    -------
        論文情報の辞書のリスト
    """
    papers_to_convert = papers[:max_count] if max_count else papers
    
    return [
        convert_paper_to_dict(
            paper=paper,
            rank=i + 1,
            include_llm_scores=include_llm_scores,
        )
        for i, paper in enumerate(papers_to_convert)
    ]

