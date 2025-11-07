"""Node for evaluating papers using LLM."""

import json
import re
from typing import Any

from langchain_openai import ChatOpenAI
from loguru import logger

from app.paper_review_workflow.models.state import (
    PaperReviewAgentState,
    EvaluatedPaper,
)
from app.paper_review_workflow.config import (
    LLMConfig,
    LLMModel,
    ScoringWeights,
    DEFAULT_SCORING_WEIGHTS,
)
from app.paper_review_workflow.constants import (
    MIN_SCORE,
    MAX_SCORE,
    MAX_AUTHORS_DISPLAY,
    MAX_KEYWORDS_DISPLAY,
    MAX_RATIONALE_LENGTH,
)


class LLMEvaluatePapersNode:
    """LLMを使って論文の内容を深く評価するノード."""
    
    def __init__(
        self,
        llm_config: LLMConfig | None = None,
        scoring_weights: ScoringWeights | None = None,
    ) -> None:
        """LLMEvaluatePapersNodeを初期化.
        
        Args:
        ----
            llm_config: LLM設定（省略時はデフォルト）
            scoring_weights: スコアリング重み設定（省略時はデフォルト）
        """
        from app.paper_review_workflow.config import DEFAULT_LLM_CONFIG
        
        self.llm_config = llm_config or DEFAULT_LLM_CONFIG
        self.weights = scoring_weights or DEFAULT_SCORING_WEIGHTS
        self.llm = self._create_llm()
    
    def _create_llm(self):
        """LLMインスタンスを作成."""
        model_name = self.llm_config.model.value
        
        if model_name.startswith("gpt"):
            return ChatOpenAI(
                model=model_name,
                temperature=self.llm_config.temperature,
                max_tokens=self.llm_config.max_tokens,
                timeout=self.llm_config.timeout,
            )
        else:
            raise ValueError(f"Unsupported model: {model_name}. Only OpenAI GPT models are supported.")
    
    def __call__(self, state: PaperReviewAgentState) -> dict[str, Any]:
        """LLM評価を実行.
        
        Args:
        ----
            state: 現在の状態
            
        Returns:
        -------
            更新された状態の辞書
        """
        logger.info(f"LLM evaluating {len(state.ranked_papers)} papers using {self.llm_config.model.value}...")
        
        llm_evaluated_papers: list[EvaluatedPaper] = []
        
        for i, paper in enumerate(state.ranked_papers, 1):
            try:
                logger.info(f"LLM evaluating paper {i}/{len(state.ranked_papers)}: {paper.title[:50]}...")
                
                # プロンプトを作成
                prompt = self._create_evaluation_prompt(paper, state.evaluation_criteria)
                
                # LLMに評価を依頼
                response = self.llm.invoke(prompt)
                response_text = response.content
                
                # スコアをパース
                scores = self._parse_llm_response(response_text)
                
                # 論文オブジェクトを更新
                updated_paper = paper.model_copy(deep=True)
                updated_paper.llm_relevance_score = scores['relevance']
                updated_paper.llm_novelty_score = scores['novelty']
                updated_paper.llm_practical_score = scores['practical']
                updated_paper.llm_rationale = scores['rationale']
                
                # 最終スコアを計算（設定された重みで統合）
                llm_average = (scores['relevance'] + scores['novelty'] + scores['practical']) / 3
                updated_paper.final_score = (
                    paper.overall_score * self.weights.openreview_weight +
                    llm_average * self.weights.llm_weight
                )
                
                llm_evaluated_papers.append(updated_paper)
                
                logger.debug(f"LLM scores - Relevance: {scores['relevance']:.3f}, "
                           f"Novelty: {scores['novelty']:.3f}, "
                           f"Practical: {scores['practical']:.3f}, "
                           f"Final: {updated_paper.final_score:.3f}")
                
            except Exception as e:
                logger.warning(f"Failed to LLM evaluate paper {paper.id}: {e}")
                # LLM評価失敗時は元のスコアを保持
                updated_paper = paper.model_copy(deep=True)
                updated_paper.final_score = paper.overall_score
                llm_evaluated_papers.append(updated_paper)
                continue
        
        logger.success(f"Successfully LLM evaluated {len(llm_evaluated_papers)} papers")
        
        return {
            "llm_evaluated_papers": llm_evaluated_papers,
        }
    
    def _create_evaluation_prompt(self, paper: EvaluatedPaper, criteria) -> str:
        """評価用プロンプトを作成."""
        research_interests_str = ", ".join(criteria.research_interests)
        
        # research_description がない場合は research_interests をフォールバック
        user_interests = criteria.research_description or f"キーワード: {research_interests_str}"

        prompt = f"""
            以下の論文を評価してください。

            # 論文情報
タイトル: {paper.title}
著者: {', '.join(paper.authors[:MAX_AUTHORS_DISPLAY])}{'...' if len(paper.authors) > MAX_AUTHORS_DISPLAY else ''}
キーワード: {', '.join(paper.keywords[:MAX_KEYWORDS_DISPLAY])}
アブストラクト:
{paper.abstract}
OpenReview評価 (参考): {paper.rating_avg if paper.rating_avg else 'N/A'}/10

# 前提
以下の情報をタイトルとアブストラクトとキーワードとOpenReview評価を読み判断してください。

# ユーザーの研究興味
{user_interests}

# 評価基準 (0.0〜1.0の実数値で評価)
1. 関連性 (Relevance)
2. 新規性 (Novelty)
3. 実用性 (Practicality)

# 出力形式
次の形式でJSONのみ出力してください。

{{
  "relevance": float,
  "novelty": float,
  "practical": float,
  "rationale": "2〜3文で各スコアの理由を簡潔に説明"
}}
"""

        return prompt
    
    def _parse_llm_response(self, response: str) -> dict:
        """LLMのレスポンスをパースしてスコアを抽出."""
        try:
            # JSONブロックを抽出
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # JSONブロックがない場合、全体をJSONとしてパース
                json_str = response.strip()
            
            # JSONをパース
            scores = json.loads(json_str)
            
            # スコアを0-1の範囲にクリップ
            return {
                'relevance': max(MIN_SCORE, min(MAX_SCORE, float(scores.get('relevance', 0.5)))),
                'novelty': max(MIN_SCORE, min(MAX_SCORE, float(scores.get('novelty', 0.5)))),
                'practical': max(MIN_SCORE, min(MAX_SCORE, float(scores.get('practical', 0.5)))),
                'rationale': str(scores.get('rationale', '評価理由なし'))[:MAX_RATIONALE_LENGTH],
            }
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            logger.debug(f"Response: {response[:200]}...")
            # パース失敗時はデフォルト値
            return {
                'relevance': 0.5,
                'novelty': 0.5,
                'practical': 0.5,
                'rationale': 'LLM評価のパースに失敗しました',
            }

