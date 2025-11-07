"""Node for ranking evaluated papers."""

import re
from typing import Any

from langchain_openai import ChatOpenAI
from loguru import logger

from app.paper_review_workflow.models.state import (
    PaperReviewAgentState,
    EvaluatedPaper,
    EvaluationCriteria,
)
from app.paper_review_workflow.utils import convert_papers_to_dict_list
from app.paper_review_workflow.constants import (
    MAX_DISPLAY_PAPERS,
    PRELIMINARY_LLM_MAX_TOKENS,
    ABSTRACT_SHORT_LENGTH,
    MAX_KEYWORDS_DISPLAY,
)


class RankPapersNode:
    """評価済み論文をスコア順にランク付けするノード."""
    
    def __init__(self) -> None:
        """RankPapersNodeを初期化."""
        self.llm = None  # 必要時に初期化（コスト削減）
    
    def __call__(self, state: PaperReviewAgentState) -> dict[str, Any]:
        """論文ランキングを実行.
        
        Args:
        ----
            state: 現在の状態
            
        Returns:
        -------
            更新された状態の辞書
        """
        logger.info(f"Ranking {len(state.evaluated_papers)} evaluated papers...")
        
        # 評価基準に基づいてフィルタリング
        criteria = state.evaluation_criteria
        filtered_papers = [
            paper for paper in state.evaluated_papers
            if self._meets_criteria(paper, criteria)
        ]
        
        logger.info(
            f"After filtering: {len(filtered_papers)}/{len(state.evaluated_papers)} papers "
            f"meet the criteria"
        )
        
        # 総合スコアでソート（降順）
        ranked_papers = sorted(
            filtered_papers,
            key=lambda p: p.overall_score or 0.0,
            reverse=True,
        )
        
        # 簡易LLMフィルタ（有効な場合）
        if criteria.enable_preliminary_llm_filter and len(ranked_papers) > 0:
            logger.info("🔍 Preliminary LLM filter enabled - evaluating top candidates...")
            ranked_papers = self._apply_preliminary_llm_filter(
                ranked_papers, 
                criteria
            )
        
        # top_kが指定されている場合、上位k件のみ選択
        if criteria.top_k_papers is not None:
            selected_papers = ranked_papers[:criteria.top_k_papers]
            logger.info(
                f"Selected top {criteria.top_k_papers} papers from {len(ranked_papers)} ranked papers "
                f"(actual: {len(selected_papers)})"
            )
        else:
            selected_papers = ranked_papers
            logger.info(f"All {len(ranked_papers)} papers selected (no top_k limit)")
        
        # 上位論文を辞書形式に変換（表示用）
        top_papers = convert_papers_to_dict_list(
            selected_papers,
            max_count=MAX_DISPLAY_PAPERS,
            include_llm_scores=False,
        )
        
        if top_papers:
            logger.success(f"Top paper: {top_papers[0]['title'][:50]} (Score: {top_papers[0]['overall_score']:.3f})")
        
        return {
            "ranked_papers": selected_papers,  # LLM評価に渡す論文リスト
            "top_papers": top_papers,
        }
    
    def _meets_criteria(self, paper: EvaluatedPaper, criteria: EvaluationCriteria) -> bool:
        """論文が評価基準を満たすかチェック.
        
        Args:
        ----
            paper: 評価済み論文
            criteria: 評価基準
            
        Returns:
        -------
            基準を満たす場合True
        """
        # 関連性スコアの最小値チェック
        if paper.relevance_score is not None:
            if paper.relevance_score < criteria.min_relevance_score:
                return False
        
        # レビュースコアの最小値チェック
        if criteria.min_rating is not None and paper.rating_avg is not None:
            if paper.rating_avg < criteria.min_rating:
                return False
        
        return True
    
    def _apply_preliminary_llm_filter(
        self, 
        ranked_papers: list[EvaluatedPaper], 
        criteria: EvaluationCriteria,
    ) -> list[EvaluatedPaper]:
        """簡易LLM評価でrelevance_scoreを再計算し、再ソート.
        
        Args:
        ----
            ranked_papers: ソート済み論文リスト
            criteria: 評価基準
            
        Returns:
        -------
            relevance_scoreを更新して再ソートした論文リスト
        """
        # 評価対象数を決定
        filter_count = min(
            criteria.preliminary_llm_filter_count,
            len(ranked_papers)
        )
        
        logger.info(f"Evaluating top {filter_count} papers with LLM for better relevance scoring...")
        
        # LLM初期化
        if self.llm is None:
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.0,
                max_tokens=PRELIMINARY_LLM_MAX_TOKENS,
            )
        
        # 上位N件を簡易LLM評価
        updated_papers = []
        success_count = 0
        
        for i, paper in enumerate(ranked_papers[:filter_count], 1):
            try:
                # LLMで関連性を評価
                llm_relevance = self._evaluate_relevance_with_llm(paper, criteria)
                
                # relevance_scoreを更新
                updated_paper = paper.model_copy(deep=True)
                old_score = paper.relevance_score or 0.0
                updated_paper.relevance_score = llm_relevance
                
                # overall_scoreも更新（relevance_weightを考慮）
                # overall_score = relevance * weight + novelty * weight + impact * weight
                # 簡易的にrelevanceの差分を反映
                score_diff = llm_relevance - old_score
                updated_paper.overall_score = (paper.overall_score or 0.0) + score_diff * 0.4  # relevance_weight=0.4
                
                updated_papers.append(updated_paper)
                success_count += 1
                
                if i % 50 == 0:
                    logger.info(f"  Progress: {i}/{filter_count} papers evaluated")
                
            except Exception as e:
                logger.warning(f"Failed to LLM evaluate paper {paper.id}: {e}")
                # 失敗時は元のスコアを保持
                updated_papers.append(paper)
        
        # 残りの論文（LLM評価しない）を追加
        remaining_papers = ranked_papers[filter_count:]
        all_papers = updated_papers + remaining_papers
        
        # relevance_scoreで再ソート（overall_scoreに反映されているので、overall_scoreでソート）
        re_ranked_papers = sorted(
            all_papers,
            key=lambda p: p.overall_score or 0.0,
            reverse=True,
        )
        
        logger.success(
            f"✓ Preliminary LLM filter completed: {success_count}/{filter_count} papers re-scored"
        )
        
        return re_ranked_papers
    
    def _evaluate_relevance_with_llm(
        self, 
        paper: EvaluatedPaper, 
        criteria: EvaluationCriteria,
    ) -> float:
        """LLMで論文の関連性を簡易評価.
        
        Args:
        ----
            paper: 評価対象論文
            criteria: 評価基準
            
        Returns:
        -------
            関連性スコア（0.0-1.0）
        """
        # アブストラクトを短縮
        abstract_short = (
            paper.abstract[:ABSTRACT_SHORT_LENGTH] + 
            ("..." if len(paper.abstract) > ABSTRACT_SHORT_LENGTH else "")
        )
        keywords_str = ", ".join(paper.keywords[:MAX_KEYWORDS_DISPLAY])
        
        # research_description がない場合は research_interests をフォールバック
        research_interests_str = ", ".join(criteria.research_interests)
        user_interests = criteria.research_description or f"Keywords: {research_interests_str}"
        
        prompt = f"""Rate the relevance of this paper to the user's research interests.

User's Research Interests:
{user_interests}

Paper:
Title: {paper.title}
Keywords: {keywords_str}
Abstract: {abstract_short}

Rate the relevance on a scale of 0.0 to 1.0:
- 1.0: Highly relevant, directly addresses the research interests
- 0.7-0.9: Very relevant, closely related
- 0.4-0.6: Moderately relevant, some overlap
- 0.1-0.3: Slightly relevant, tangential connection
- 0.0: Not relevant

Return ONLY a single number between 0.0 and 1.0 (e.g., "0.85"). No other text.
"""
        
        try:
            response = self.llm.invoke(prompt)
            response_text = response.content.strip()
            
            # 数値を抽出
            # "0.85"のような形式、または"The relevance is 0.85"のような形式に対応
            match = re.search(r'(\d+\.?\d*)', response_text)
            if match:
                score = float(match.group(1))
                # 0-1の範囲に制限
                score = max(0.0, min(1.0, score))
                return score
            else:
                logger.warning(f"Could not parse LLM response: {response_text[:50]}")
                return paper.relevance_score or 0.5
                
        except Exception as e:
            logger.warning(f"LLM evaluation failed: {e}")
            return paper.relevance_score or 0.5

