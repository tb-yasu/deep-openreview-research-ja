"""Node for re-ranking papers based on LLM evaluation scores."""

from typing import Any

from loguru import logger

from app.paper_review_workflow.models.state import (
    PaperReviewAgentState,
    EvaluatedPaper,
)
from app.paper_review_workflow.utils import convert_papers_to_dict_list
from app.paper_review_workflow.constants import DEFAULT_TOP_N_PAPERS


class ReRankPapersNode:
    """LLM評価スコアに基づいて論文を再ランキングするノード."""
    
    def __init__(self, top_n: int = DEFAULT_TOP_N_PAPERS) -> None:
        """ReRankPapersNodeを初期化.
        
        Args:
        ----
            top_n: トップN件を選出（デフォルト: 20）
        """
        self.top_n = top_n
    
    def __call__(self, state: PaperReviewAgentState) -> dict[str, Any]:
        """LLM評価スコアで論文を再ランキング.
        
        Args:
        ----
            state: 現在の状態
            
        Returns:
        -------
            更新された状態の辞書
        """
        logger.info(f"Re-ranking {len(state.llm_evaluated_papers)} papers based on LLM scores...")
        
        # final_scoreでソート（降順）
        re_ranked_papers = sorted(
            state.llm_evaluated_papers,
            key=lambda p: p.final_score if p.final_score is not None else 0.0,
            reverse=True
        )
        
        # ランク番号を付与して辞書に変換
        top_papers = convert_papers_to_dict_list(
            re_ranked_papers,
            max_count=self.top_n,
            include_llm_scores=True,
        )
        
        # 統計情報
        if re_ranked_papers:
            avg_final_score = sum(p.final_score for p in re_ranked_papers if p.final_score) / len(re_ranked_papers)
            logger.info(f"Average final score: {avg_final_score:.3f}")
            logger.info(f"Top paper: {re_ranked_papers[0].title[:50]}... (Score: {re_ranked_papers[0].final_score:.3f})")
            logger.info(f"Bottom paper: {re_ranked_papers[-1].title[:50]}... (Score: {re_ranked_papers[-1].final_score:.3f})")
        
        logger.success(f"Re-ranked papers: {len(re_ranked_papers)} total, top {len(top_papers)} selected")
        
        return {
            "re_ranked_papers": re_ranked_papers,
            "top_papers": top_papers,
        }

