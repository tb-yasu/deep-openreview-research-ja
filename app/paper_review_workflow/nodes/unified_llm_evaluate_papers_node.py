"""Unified LLM evaluation node - 1回の呼び出しで全評価を完結."""

import asyncio
import json
import re
from typing import Any

from loguru import logger

from app.paper_review_workflow.models.state import (
    PaperReviewAgentState,
    EvaluatedPaper,
)
from app.paper_review_workflow.config import (
    LLMConfig,
    ScoringWeights,
    DEFAULT_SCORING_WEIGHTS,
)
from app.paper_review_workflow.constants import (
    MIN_SCORE,
    MAX_SCORE,
    MAX_AUTHORS_DISPLAY,
    MAX_KEYWORDS_DISPLAY,
)
from app.paper_review_workflow.llm_factory import create_chat_openai


class UnifiedLLMEvaluatePapersNode:
    """統合LLM評価ノード - タイトル、アブスト、レビュー全フィールドを使って1回で全評価."""
    
    def __init__(
        self,
        llm_config: LLMConfig | None = None,
        scoring_weights: ScoringWeights | None = None,
    ) -> None:
        """UnifiedLLMEvaluatePapersNodeを初期化.
        
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
            return create_chat_openai(
                model=model_name,
                temperature=self.llm_config.temperature,
                max_tokens=self.llm_config.max_tokens,
                timeout=self.llm_config.timeout,
            )
        else:
            raise ValueError(f"Unsupported model: {model_name}. Only OpenAI GPT models are supported.")
    
    def __call__(self, state: PaperReviewAgentState) -> dict[str, Any]:
        """統合LLM評価を実行（並列処理版）.
        
        Args:
        ----
            state: 現在の状態
            
        Returns:
        -------
            更新された状態の辞書
        """
        logger.info(f"🤖 Unified LLM evaluation for {len(state.ranked_papers)} papers using {self.llm_config.model.value}...")
        logger.info(f"⚡ Parallel execution with max {self.llm_config.max_concurrent} concurrent requests")
        logger.info(f"📊 1回の呼び出しで全スコア + レビュー要約 + field_insights を取得")
        
        # asyncioイベントループで並列実行
        evaluated_papers = asyncio.run(
            self._evaluate_papers_parallel(
                state.ranked_papers,
                state.evaluation_criteria,
                max_concurrent=self.llm_config.max_concurrent,
            )
        )
        
        logger.success(f"✅ Successfully evaluated {len(evaluated_papers)} papers with unified LLM (parallel)")
        
        return {
            "llm_evaluated_papers": evaluated_papers,
        }
    
    async def _evaluate_papers_parallel(
        self,
        papers: list[EvaluatedPaper],
        criteria,
        max_concurrent: int = 10,
    ) -> list[EvaluatedPaper]:
        """複数論文を並列評価（レート制限付き）.
        
        Args:
        ----
            papers: 評価対象論文リスト
            criteria: 評価基準
            max_concurrent: 最大同時実行数（APIレート制限対策）
            
        Returns:
        -------
            評価済み論文リスト
        """
        # Semaphoreで同時実行数を制限
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def evaluate_with_semaphore(paper, index, total):
            async with semaphore:
                return await self._evaluate_single_paper_async(paper, criteria, index, total)
        
        # 全論文を並列実行
        tasks = [
            evaluate_with_semaphore(paper, i + 1, len(papers))
            for i, paper in enumerate(papers)
        ]
        
        # 全タスクを実行（エラーが発生しても他のタスクは継続）
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 正常に完了した論文のみを返す（Exceptionは除外）
        evaluated_papers = [
            result for result in results
            if not isinstance(result, Exception)
        ]
        
        # エラーが発生した論文数をログ
        error_count = len(results) - len(evaluated_papers)
        if error_count > 0:
            logger.warning(f"⚠ {error_count}/{len(results)} papers failed during evaluation")
        
        return evaluated_papers
    
    async def _evaluate_single_paper_async(
        self,
        paper: EvaluatedPaper,
        criteria,
        index: int,
        total: int,
    ) -> EvaluatedPaper:
        """単一論文を非同期で評価.
        
        Args:
        ----
            paper: 評価対象論文
            criteria: 評価基準
            index: 論文番号（ログ用）
            total: 総論文数（ログ用）
            
        Returns:
        -------
            評価済み論文
        """
        try:
            logger.info(f"  [{index}/{total}] Evaluating: {paper.title[:50]}...")
            
            # 統合プロンプトを作成
            prompt = self._create_unified_evaluation_prompt(paper, criteria)
            
            # LLMに非同期で評価を依頼
            response = await self.llm.ainvoke(prompt)
            response_text = response.content
            
            # レスポンスが空の場合の詳細ログ
            if not response_text or len(response_text.strip()) == 0:
                logger.error(f"  ❌ Empty response from LLM for paper: {paper.title[:50]}")
                logger.error(f"     Model: {self.llm_config.model.value}")
                logger.error(f"     Response object: {response}")
                raise ValueError("Empty response from LLM")
            
            # レスポンスをパース
            evaluation = self._parse_llm_response(response_text)
            
            # 論文オブジェクトを更新
            updated_paper = paper.model_copy(deep=True)
            updated_paper.relevance_score = evaluation['relevance']
            updated_paper.novelty_score = evaluation['novelty']
            updated_paper.impact_score = evaluation['impact']
            updated_paper.practicality_score = evaluation['practicality']
            updated_paper.review_summary = evaluation['review_summary']
            updated_paper.field_insights = evaluation['field_insights']
            updated_paper.ai_rationale = evaluation['rationale']
            
            # overall_scoreを計算（4つのスコアの重み付き平均）
            updated_paper.overall_score = (
                evaluation['relevance'] * 0.4 +
                evaluation['novelty'] * 0.25 +
                evaluation['impact'] * 0.25 +
                evaluation['practicality'] * 0.10
            )
            
            logger.debug(
                f"    ✓ [{index}/{total}] Scores: R={evaluation['relevance']:.2f} "
                f"N={evaluation['novelty']:.2f} "
                f"I={evaluation['impact']:.2f} "
                f"P={evaluation['practicality']:.2f} "
                f"Overall={updated_paper.overall_score:.2f}"
            )
            
            return updated_paper
            
        except Exception as e:
            logger.warning(f"  ⚠ Failed to evaluate paper {paper.id}: {e}")
            # 評価失敗時はデフォルト値を設定
            updated_paper = paper.model_copy(deep=True)
            updated_paper.relevance_score = 0.5
            updated_paper.novelty_score = 0.5
            updated_paper.impact_score = 0.5
            updated_paper.practicality_score = 0.5
            updated_paper.overall_score = 0.5
            updated_paper.review_summary = "評価に失敗しました"
            updated_paper.field_insights = "N/A"
            updated_paper.ai_rationale = f"LLM評価エラー: {str(e)[:100]}"
            return updated_paper
    
    def _create_unified_evaluation_prompt(self, paper: EvaluatedPaper, criteria) -> str:
        """統合評価プロンプトを作成 - 1回の呼び出しで全て完結."""
        
        # ユーザーの研究興味
        research_interests_str = ", ".join(criteria.research_interests)
        user_interests = criteria.research_description or f"キーワード: {research_interests_str}"
        
        # レビューデータをフォーマット
        reviews_formatted = self._format_dynamic_reviews(paper.reviews)
        
        prompt = f"""
あなたは機械学習論文の評価専門家です。以下の論文を総合的に評価してください。

# 📄 論文情報

**学会**: {paper.venue} {paper.year}

**タイトル**: {paper.title}

**著者**: {', '.join(paper.authors[:MAX_AUTHORS_DISPLAY])}{'...' if len(paper.authors) > MAX_AUTHORS_DISPLAY else ''}

**キーワード**: {', '.join(paper.keywords[:MAX_KEYWORDS_DISPLAY])}

**アブストラクト**:
{paper.abstract[:1500]}{'...' if len(paper.abstract) > 1500 else ''}

**採択判定**: {paper.decision or 'N/A'}

**採択判定コメント** (Program Chairs):
{(paper.decision_comment[:500] + '...') if paper.decision_comment and len(paper.decision_comment) > 500 else (paper.decision_comment or 'N/A')}

# 📊 OpenReview レビューデータ

{reviews_formatted}

# 🎯 ユーザーの研究興味

{user_interests}

# 📝 評価タスク

以下の**4つのスコア**を0.0-1.0の範囲で評価してください：

## 1. 関連性 (relevance)
研究テーマ「{user_interests}」との具体的な関連度を評価。
- 論文のキーワード、タイトル、アブストラクトから判断
- レビューに "relevance" や "significance" フィールドがあれば参考にする

## 2. 新規性 (novelty)
研究の独創性・新しさを評価。
- レビューの **"originality"** や **"novelty"** フィールドがあれば優先的に使用
- **"strengths_and_weaknesses"** に新規性の記述があれば参考
- **"claims_and_evidence"** や **"contribution"** も参考
- なければアブストラクトから推測

## 3. インパクト (impact)
学術的・実用的な影響力を評価。
- レビューの **"significance"** や **"contribution"** フィールドがあれば優先
- **"rating"** や **"overall_recommendation"** も重視
- 採択判定 (Accept/Reject) も考慮
- **"experimental_designs_or_analyses"** の質も参考

## 4. 実用性 (practicality)
実際の応用可能性を評価。
- 実装の容易性、再現性、産業応用の可能性
- **"methods_and_evaluation_criteria"** や **"code_of_conduct"** フィールドも参考
- レビューの **"questions_for_authors"** も参考

## 5. レビュー要約 (review_summary)
すべてのレビューを統合して、2-3文で要約してください：
- レビューワーの主な評価点（強み・弱み）
- 平均的な評価傾向
- Program Chairsの判定理由（あれば）

## 6. フィールド活用の説明 (field_insights)
どのレビューフィールドを主に使用したかを1-2文で説明：
例: "{paper.venue}のoverall_recommendationフィールド(平均3.0)とsummaryを主に参照しました"
例: "{paper.venue}のratingフィールド(平均5.5)とstrengths_and_weaknessesを主に参照しました"

# ⚠ 重要な指示

**rationale（評価理由）** は以下の点に注意して記述してください：
- ❌ 避けるべき表現: 「ユーザーの興味に合致」「研究興味に直接関連」などのテンプレート表現
- ✅ 推奨: 論文固有の**具体的な技術的特徴**と**革新点**を記述
- 例: 「Transformer の attention 機構に新しい正則化手法を導入し、長距離依存性の学習を改善。実験で BERT より 3% 向上を達成したが、計算コストが 2 倍に増加。」

# 出力形式

必ず以下のJSON形式のみを出力してください（説明文は不要）：

{{
  "relevance": 0.85,
  "novelty": 0.72,
  "impact": 0.68,
  "practicality": 0.80,
  "review_summary": "レビューワーは手法の理論的堅牢性を高く評価。一方で実験の限定性を指摘。Program Chairsは新規性と実験品質のバランスから採択を推奨。",
  "field_insights": "{paper.venue}のoverall_recommendation(平均2.75)、theoretical_claims、experimental_designs_or_analysesフィールドを主に参照しました。",
  "rationale": "Transformerのattention機構に新しい正則化手法を導入し、長距離依存性の学習を改善。実験でBERTより3%向上を達成したが、計算コストが2倍に増加。"
}}
"""
        return prompt
    
    def _format_dynamic_reviews(self, reviews: list[dict]) -> str:
        """動的フィールドを含むレビューを読みやすくフォーマット."""
        if not reviews:
            return "**レビューデータなし**（採択済みだがレビューが非公開、または取得エラー）"
        
        formatted_lines = []
        
        for i, review in enumerate(reviews, 1):
            formatted_lines.append(f"## レビュー {i}")
            formatted_lines.append("")
            
            # 重要フィールドを優先表示
            priority_fields = {
                'rating': 'スコア',
                'overall_recommendation': 'スコア', 
                'confidence': '確信度',
                'summary': '要約',
            }
            
            for field, label in priority_fields.items():
                if field in review:
                    value = review[field]
                    # 長すぎる場合は省略
                    display = value[:300] + "..." if len(value) > 300 else value
                    formatted_lines.append(f"**{label}**: {display}")
            
            formatted_lines.append("")
            
            # その他のフィールド（アルファベット順、最大10個まで）
            other_fields = {k: v for k, v in review.items() 
                           if k not in priority_fields}
            
            if other_fields:
                formatted_lines.append("**その他の評価項目**:")
                for j, (field, value) in enumerate(sorted(other_fields.items()), 1):
                    if j > 10:  # 長すぎる場合は省略
                        formatted_lines.append(f"  ...他 {len(other_fields) - 10} 項目")
                        break
                    # フィールド名を読みやすく
                    field_display = field.replace('_', ' ').title()
                    # 値を省略
                    display = value[:150] + "..." if len(value) > 150 else value
                    formatted_lines.append(f"  • **{field_display}**: {display}")
            
            formatted_lines.append("")
            formatted_lines.append("---")
            formatted_lines.append("")
        
        return "\n".join(formatted_lines)
    
    def _parse_llm_response(self, response: str) -> dict:
        """LLMのレスポンスをパースして評価結果を抽出."""
        try:
            # JSONブロックを抽出
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # JSONブロックがない場合、全体から{}を探す
                json_match = re.search(r'\{.*?\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    # 全体をJSONとしてパース
                    json_str = response.strip()
            
            # JSONをパース
            evaluation = json.loads(json_str)
            
            # スコアを0-1の範囲にクリップ
            return {
                'relevance': max(MIN_SCORE, min(MAX_SCORE, float(evaluation.get('relevance', 0.5)))),
                'novelty': max(MIN_SCORE, min(MAX_SCORE, float(evaluation.get('novelty', 0.5)))),
                'impact': max(MIN_SCORE, min(MAX_SCORE, float(evaluation.get('impact', 0.5)))),
                'practicality': max(MIN_SCORE, min(MAX_SCORE, float(evaluation.get('practicality', 0.5)))),
                'review_summary': str(evaluation.get('review_summary', 'レビュー要約なし'))[:500],
                'field_insights': str(evaluation.get('field_insights', 'フィールド情報なし'))[:300],
                'rationale': str(evaluation.get('rationale', '評価理由なし'))[:500],
            }
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            logger.warning(f"Full response: {response[:500]}...")
            # パース失敗時はデフォルト値
            return {
                'relevance': 0.5,
                'novelty': 0.5,
                'impact': 0.5,
                'practicality': 0.5,
                'review_summary': 'LLM評価のパースに失敗しました',
                'field_insights': 'パースエラー',
                'rationale': f'パースエラー: {str(e)[:100]}',
            }

