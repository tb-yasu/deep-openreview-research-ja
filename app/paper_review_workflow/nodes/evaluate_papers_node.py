"""Node for evaluating papers based on OpenReview review data."""

import json
from typing import Any

from langchain_openai import ChatOpenAI
from loguru import logger

from app.paper_review_workflow.models.state import (
    PaperReviewAgentState,
    EvaluatedPaper,
    Paper,
    EvaluationCriteria,
)
from app.paper_review_workflow.tools import fetch_paper_metadata
from app.paper_review_workflow.config import ScoringWeights, DEFAULT_SCORING_WEIGHTS
from app.paper_review_workflow.constants import (
    SYNONYMS_LLM_MAX_TOKENS,
    SYNONYMS_COUNT_MIN,
    SYNONYMS_COUNT_MAX,
    MIN_SCORE,
    MAX_SCORE,
    NEURIPS_RATING_SCALE,
    RELEVANCE_KEYWORD_WEIGHT,
    RELEVANCE_TEXT_WEIGHT,
    RELEVANCE_COVERAGE_WEIGHT,
    MAX_RATIONALE_LENGTH,
)


class EvaluatePapersNode:
    """OpenReviewのレビューデータに基づいて論文を評価するノード."""
    
    def __init__(self, scoring_weights: ScoringWeights | None = None) -> None:
        """EvaluatePapersNodeを初期化.
        
        Args:
        ----
            scoring_weights: スコアリングの重み設定（省略時はデフォルト）
        """
        self.tool = fetch_paper_metadata
        self.weights = scoring_weights or DEFAULT_SCORING_WEIGHTS
        self._synonyms_cache: dict[str, list[str]] = {}  # 同義語キャッシュ
    
    def __call__(self, state: PaperReviewAgentState) -> dict[str, Any]:
        """論文評価を実行.
        
        Args:
        ----
            state: 現在の状態
            
        Returns:
        -------
            更新された状態の辞書
        """
        logger.info(f"Evaluating {len(state.papers)} papers based on review data...")
        
        # 最初に同義語を生成（全論文の評価で使用）
        research_interests = state.evaluation_criteria.research_interests
        if research_interests:
            synonyms = self._generate_synonyms(research_interests)
        else:
            synonyms = {}
        
        evaluated_papers: list[EvaluatedPaper] = []
        
        for i, paper in enumerate(state.papers, 1):
            try:
                logger.info(f"Evaluating paper {i}/{len(state.papers)}: {paper.title[:50]}...")
                
                # メタデータを取得（既にレビューデータがある場合はそれを使用）
                if paper.reviews and paper.rating_avg is not None:
                    # all_papers.jsonから読み込んだデータを使用（API呼び出し不要）
                    logger.debug(f"Using cached review data for {paper.id}")
                    metadata = {
                        "reviews": paper.reviews,
                        "rating_avg": paper.rating_avg,
                        "confidence_avg": paper.confidence_avg,
                        "decision": paper.decision,
                    }
                else:
                    # APIから取得
                    logger.debug(f"Fetching review data from API for {paper.id}")
                    result = self.tool.invoke({"paper_id": paper.id})
                    metadata = json.loads(result)
                    
                    # エラーチェック
                    if isinstance(metadata, dict) and "error" in metadata:
                        logger.warning(f"Failed to fetch metadata for {paper.id}: {metadata['error']}")
                        # メタデータなしで評価
                        evaluated_paper = EvaluatedPaper(
                            **paper.model_dump(),
                            relevance_score=None,
                            novelty_score=None,
                            impact_score=None,
                            overall_score=0.0,
                            evaluation_rationale="メタデータ取得失敗",
                        )
                        evaluated_papers.append(evaluated_paper)
                        continue
                
                # スコアを計算（paperオブジェクトも渡す）
                scores = self._calculate_scores(paper, metadata, state.evaluation_criteria)
                
                # 評価理由を生成
                rationale = self._generate_rationale(metadata, scores)
                
                # EvaluatedPaperオブジェクトを作成
                evaluated_paper = EvaluatedPaper(
                    **paper.model_dump(),
                    relevance_score=scores["relevance"],
                    novelty_score=scores["novelty"],
                    impact_score=scores["impact"],
                    overall_score=scores["overall"],
                    evaluation_rationale=rationale,
                )
                
                evaluated_papers.append(evaluated_paper)
                logger.debug(f"Evaluated: {paper.title[:50]} - Score: {scores['overall']:.2f}")
                
            except Exception as e:
                logger.error(f"Error evaluating paper {paper.id}: {e}")
                # エラーが発生した場合もスキップせず、スコア0で追加
                evaluated_paper = EvaluatedPaper(
                    **paper.model_dump(),
                    overall_score=0.0,
                    evaluation_rationale=f"評価エラー: {e!s}",
                )
                evaluated_papers.append(evaluated_paper)
        
        logger.info(f"Successfully evaluated {len(evaluated_papers)} papers")
        
        return {
            "evaluated_papers": evaluated_papers,
            "synonyms": synonyms,
        }
    
    def _calculate_scores(
        self,
        paper: Paper,
        metadata: dict[str, Any],
        criteria: EvaluationCriteria,
    ) -> dict[str, float]:
        """レビューデータから各種スコアを計算.
        
        Args:
        ----
            paper: 論文オブジェクト
            metadata: 論文のメタデータ
            criteria: 評価基準
            
        Returns:
        -------
            各種スコアの辞書
        """
        rating_avg = metadata.get("rating_avg")
        
        if rating_avg is None:
            # レビューデータがない場合：キーワードベースの関連性のみ
            relevance = self._calculate_relevance_score(paper, criteria)
            return {
                "relevance": relevance,
                "novelty": 0.5,     # 中立
                "impact": 0.5,      # 中立
                "overall": relevance * 0.7 + 0.3,  # 関連性を重視
            }
        
        # レビュースコアを0-1スケールに正規化
        normalized_rating = rating_avg / NEURIPS_RATING_SCALE
        
        # 1. 関連性スコア：ユーザーの研究興味とのマッチング（キーワードベースのみ）
        relevance_score = self._calculate_relevance_score(paper, criteria)
        
        # 2. 新規性スコア：レビュー内容から推定（改善版）
        novelty_score = self._estimate_novelty_from_reviews(metadata, normalized_rating)
        
        # 3. インパクトスコア：採択判定とレビュースコアから計算
        impact_score = self._calculate_impact_score(metadata, normalized_rating)
        
        # 4. 総合スコア：設定された重みで統合（重複なし）
        overall_score = (
            relevance_score * self.weights.relevance_weight +
            novelty_score * self.weights.novelty_weight +
            impact_score * self.weights.impact_weight
        )
        
        return {
            "relevance": min(max(relevance_score, MIN_SCORE), MAX_SCORE),
            "novelty": min(max(novelty_score, MIN_SCORE), MAX_SCORE),
            "impact": min(max(impact_score, MIN_SCORE), MAX_SCORE),
            "overall": min(max(overall_score, MIN_SCORE), MAX_SCORE),
        }
    
    def _generate_synonyms(self, research_interests: list[str]) -> dict[str, list[str]]:
        """各キーワードごとにLLMを使って同義語を生成.
        
        各キーワードを個別に処理することで、キーワードと同義語辞書のキーが
        確実に一致するようにします。
        
        Args:
        ----
            research_interests: ユーザーの研究興味キーワードリスト
            
        Returns:
        -------
            キーワードごとの同義語辞書（キー: 元のキーワード、値: 同義語リスト）
        """
        # キャッシュチェック
        cache_key = ",".join(sorted(research_interests))
        if cache_key in self._synonyms_cache:
            logger.debug("Using cached synonyms")
            return self._synonyms_cache[cache_key]
        
        logger.info(f"Generating synonyms for {len(research_interests)} research interests using LLM...")
        
        try:
            llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.0,
                max_tokens=SYNONYMS_LLM_MAX_TOKENS,
            )
            
            # 各キーワードごとに個別に同義語を生成
            synonyms = {}
            
            for keyword in research_interests:
                keyword_lower = keyword.lower().strip()
                
                prompt = f"""Generate {SYNONYMS_COUNT_MIN}-{SYNONYMS_COUNT_MAX} synonyms and related terms for this research topic:

Topic: "{keyword}"

Return ONLY a JSON array of synonyms (all lowercase):
["synonym1", "synonym2", "synonym3", ...]

Include:
- Common abbreviations (e.g., "llm" for "large language model")
- Related terms
- Alternative phrasings
- Keep terms concise and technical
"""
                
                try:
                    response = llm.invoke(prompt)
                    response_text = response.content.strip()
                    
                    # JSONパース（コードブロックを除去）
                    if "```json" in response_text:
                        response_text = response_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in response_text:
                        response_text = response_text.split("```")[1].split("```")[0].strip()
                    
                    syn_list = json.loads(response_text)
                    
                    # リストの場合のみ処理
                    if isinstance(syn_list, list):
                        # 小文字化して重複削除
                        synonyms[keyword_lower] = [s.lower().strip() for s in syn_list if s]
                        logger.debug(f"  ✓ '{keyword_lower}': {synonyms[keyword_lower][:3]}...")
                    else:
                        logger.warning(f"Invalid synonym format for '{keyword}': expected list, got {type(syn_list)}")
                        synonyms[keyword_lower] = []
                
                except Exception as e:
                    logger.warning(f"Failed to generate synonyms for '{keyword}': {e}")
                    # エラー時は空リストを設定（そのキーワードだけスキップ）
                    synonyms[keyword_lower] = []
            
            # キャッシュに保存
            self._synonyms_cache[cache_key] = synonyms
            
            # サマリーログ
            successful = sum(1 for syns in synonyms.values() if syns)
            logger.success(f"Generated synonyms for {successful}/{len(synonyms)} topics")
            
            return synonyms
            
        except Exception as e:
            logger.warning(f"Failed to generate synonyms: {e}. Using original keywords only.")
            # エラー時は空の辞書を返す（元のキーワードのみ使用）
            return {}
    
    def _calculate_relevance_score(
        self,
        paper: Paper,
        criteria: EvaluationCriteria,
    ) -> float:
        """ユーザーの研究興味との関連性を計算（グループベース）.
        
        各キーワードグループ（元のキーワード + 同義語）ごとにマッチを判定し、
        同じグループ内の複数マッチは1回としてカウントします。
        論文keywordのマッチはタイトル/アブストラクトよりも高く評価します。
        
        Args:
        ----
            paper: 論文オブジェクト
            criteria: 評価基準
            
        Returns:
        -------
            関連性スコア（0.0-1.0）
        """
        research_interests = criteria.research_interests
        
        if not research_interests:
            # 研究興味が指定されていない場合は中立
            return 0.5
        
        # 同義語を生成（初回のみLLM呼び出し、その後はキャッシュ）
        synonyms = self._generate_synonyms(research_interests)
        
        # 論文データを準備
        paper_keywords = set([kw.lower().strip() for kw in paper.keywords])
        paper_text = (paper.title + " " + paper.abstract).lower()
        
        # 各キーワードグループごとにマッチを判定
        matched_groups = 0
        matched_in_paper_keywords = 0
        matched_in_text_only = 0
        
        for interest in research_interests:
            interest_lower = interest.lower().strip()
            
            # グループのキーワード（元のキーワード + 同義語）
            group_keywords = {interest_lower}
            if interest_lower in synonyms:
                group_keywords.update([syn.lower().strip() for syn in synonyms[interest_lower]])
            
            # このグループが論文keywordにマッチするか
            has_keyword_match = bool(group_keywords & paper_keywords)
            
            # このグループがタイトル/アブストラクトにマッチするか
            has_text_match = any(kw in paper_text for kw in group_keywords)
            
            if has_keyword_match or has_text_match:
                matched_groups += 1
                
                if has_keyword_match:
                    matched_in_paper_keywords += 1
                elif has_text_match:
                    matched_in_text_only += 1
        
        # スコア計算（合計が最大1.0になるように重みを設計）
        num_groups = len(research_interests)
        
        # 論文keywordマッチを優先
        keyword_weight_per_group = RELEVANCE_KEYWORD_WEIGHT / num_groups if num_groups > 0 else 0
        
        # テキストマッチは控えめ
        text_weight_per_group = RELEVANCE_TEXT_WEIGHT / num_groups if num_groups > 0 else 0
        
        # カバレッジボーナス
        coverage_weight = RELEVANCE_COVERAGE_WEIGHT
        
        keyword_match_score = matched_in_paper_keywords * keyword_weight_per_group
        text_match_score = matched_in_text_only * text_weight_per_group
        coverage_score = (matched_groups / num_groups) * coverage_weight
        
        total_score = keyword_match_score + text_match_score + coverage_score
        
        logger.debug(
            f"Relevance: {total_score:.3f} "
            f"(keyword:{matched_in_paper_keywords}/{num_groups}={keyword_match_score:.3f}, "
            f"text:{matched_in_text_only}/{num_groups}={text_match_score:.3f}, "
            f"coverage:{matched_groups}/{num_groups}={coverage_score:.3f})"
        )
        
        # 理論上の最大値は設定された重みの合計
        # 念のためmin()を残すが、通常は1.0を超えない
        return min(MAX_SCORE, total_score)
    
    def _calculate_impact_score(
        self,
        metadata: dict[str, Any],
        normalized_rating: float,
    ) -> float:
        """研究のインパクトを計算.
        
        Args:
        ----
            metadata: 論文のメタデータ
            normalized_rating: 正規化されたレビュースコア
            
        Returns:
        -------
            インパクトスコア（0.0-1.0）
        """
        # 採択判定の影響
        decision = metadata.get("decision", "").lower()
        decision_score = 0.5  # デフォルト
        
        if "oral" in decision or "spotlight" in decision:
            decision_score = 1.0  # 高評価
        elif "accept" in decision:
            decision_score = 0.7
        elif "reject" in decision:
            decision_score = 0.2
        
        # レビュアーの信頼度
        confidence_avg = metadata.get("confidence_avg")
        confidence_score = (confidence_avg / 5.0) if confidence_avg else 0.5
        
        # インパクトスコア = 採択判定50% + レビュースコア30% + 信頼度20%
        impact = (
            decision_score * 0.5 +
            normalized_rating * 0.3 +
            confidence_score * 0.2
        )
        
        return min(MAX_SCORE, max(MIN_SCORE, impact))
    
    def _estimate_novelty_from_reviews(
        self,
        metadata: dict[str, Any],
        normalized_rating: float,
    ) -> float:
        """レビュー内容から新規性を推定（改善版）.
        
        Args:
        ----
            metadata: 論文のメタデータ
            normalized_rating: 正規化されたレビュースコア
            
        Returns:
        -------
            新規性スコア（0.0-1.0）
        """
        reviews = metadata.get("reviews", [])
        if not reviews:
            return normalized_rating  # レビューがない場合は総合評価を使用
        
        # 新規性に関するキーワード（ポジティブ）
        positive_keywords = [
            "novel", "new approach", "innovative", "original", "first",
            "groundbreaking", "pioneering", "unique", "creative", "fresh"
        ]
        
        # 新規性が低いことを示すキーワード（ネガティブ）
        negative_keywords = [
            "not novel", "incremental", "limited novelty", "similar to",
            "existing work", "well-known", "standard approach"
        ]
        
        positive_score = 0
        negative_score = 0
        
        for review in reviews:
            strengths = review.get("strengths", "").lower()
            weaknesses = review.get("weaknesses", "").lower()
            summary = review.get("summary", "").lower()
            
            # レビューテキストを結合
            review_text = strengths + " " + weaknesses + " " + summary
            
            # ポジティブな言及をカウント
            for keyword in positive_keywords:
                if keyword in review_text:
                    # strengths内での言及は重み2倍
                    if keyword in strengths:
                        positive_score += 2
                    else:
                        positive_score += 1
        
            # ネガティブな言及をカウント
            for keyword in negative_keywords:
                if keyword in review_text:
                    # weaknesses内での言及は重み2倍
                    if keyword in weaknesses:
                        negative_score += 2
                    else:
                        negative_score += 1
        
        # スコア計算
        if positive_score > 0 or negative_score > 0:
            # ポジティブとネガティブのバランスを考慮
            keyword_score = positive_score / (positive_score + negative_score + 1)
            # キーワードベース50% + レビュースコア50%
            novelty_score = keyword_score * 0.5 + normalized_rating * 0.5
        else:
            # キーワードが見つからない場合はレビュースコアを使用
            novelty_score = normalized_rating
        
        return min(MAX_SCORE, max(MIN_SCORE, novelty_score))
    
    def _generate_rationale(
        self,
        metadata: dict[str, Any],
        scores: dict[str, float],
    ) -> str:
        """評価理由を詳細な文章形式で生成.
        
        Args:
        ----
            metadata: 論文のメタデータ
            scores: 計算されたスコア
            
        Returns:
        -------
            評価理由の文字列
        """
        rating_avg = metadata.get("rating_avg")
        confidence_avg = metadata.get("confidence_avg")
        decision = metadata.get("decision", "N/A")
        num_reviews = len(metadata.get("reviews", []))
        
        parts = []
        
        # 基本情報（レビュー数と評価）
        if num_reviews > 0:
            parts.append(f"この論文は{num_reviews}件のレビューを受け、")
            if rating_avg is not None:
                parts.append(f"平均{rating_avg:.2f}/10の評価を獲得しました。")
            else:
                parts.append("評価スコアは未公開です。")
        else:
            parts.append("この論文はまだレビューを受けていません。")
        
        # 採択状況
        decision_lower = decision.lower()
        if "oral" in decision_lower or "spotlight" in decision_lower:
            parts.append(f"採択判定は「{decision}」で、特に高く評価されています。")
        elif "accept" in decision_lower:
            parts.append(f"採択判定は「{decision}」です。")
        elif "reject" in decision_lower:
            parts.append(f"不採択（{decision}）となりました。")
        elif decision != "N/A":
            parts.append(f"判定状況：{decision}")
        
        # スコア詳細
        parts.append(f"\n\n【評価スコアの詳細】")
        parts.append(f"総合スコア：{scores['overall']:.3f}")
        parts.append(f"（内訳：関連性 {scores['relevance']:.3f}、")
        parts.append(f"新規性 {scores['novelty']:.3f}、")
        parts.append(f"インパクト {scores['impact']:.3f}）")
        
        # レビュアーの信頼度
        if confidence_avg is not None:
            confidence_desc = "非常に高い" if confidence_avg >= 4.0 else "高い" if confidence_avg >= 3.0 else "中程度"
            parts.append(f"\nレビュアーの信頼度は{confidence_avg:.2f}/5（{confidence_desc}）です。")
        
        return " ".join(parts)

