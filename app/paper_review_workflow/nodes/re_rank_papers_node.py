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
        logger.info(f"Top N papers to select: {self.top_n}")
        
        # overall_scoreでソート（降順） - 統合LLM評価システムではoverall_scoreを使用
        re_ranked_papers = sorted(
            state.llm_evaluated_papers,
            key=lambda p: p.overall_score if p.overall_score is not None else 0.0,
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
            scores = [p.overall_score for p in re_ranked_papers if p.overall_score is not None]
            if scores:
                avg_score = sum(scores) / len(scores)
                logger.info(f"Average overall score: {avg_score:.3f}")
                top_score = re_ranked_papers[0].overall_score
                bottom_score = re_ranked_papers[-1].overall_score
                if top_score is not None:
                    logger.info(f"Top paper: {re_ranked_papers[0].title[:50]}... (Score: {top_score:.3f})")
                if bottom_score is not None:
                    logger.info(f"Bottom paper: {re_ranked_papers[-1].title[:50]}... (Score: {bottom_score:.3f})")
            else:
                logger.warning("No valid overall_score found in papers")
        
        logger.success(f"Re-ranked papers: {len(re_ranked_papers)} total, top {len(top_papers)} selected")
        
        return {
            "re_ranked_papers": re_ranked_papers,
            "top_papers": top_papers,
        }

