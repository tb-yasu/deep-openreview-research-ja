"""Node for generating paper review report."""

from typing import Any
from datetime import datetime

from loguru import logger

from app.paper_review_workflow.models.state import PaperReviewAgentState


class GeneratePaperReportNode:
    """論文レビューレポートを生成するノード."""
    
    def __init__(self) -> None:
        """GeneratePaperReportNodeを初期化."""
        pass
    
    def __call__(self, state: PaperReviewAgentState) -> dict[str, Any]:
        """レポート生成を実行.
        
        Args:
        ----
            state: 現在の状態
            
        Returns:
        -------
            更新された状態の辞書
        """
        logger.info("Generating paper review report...")
        
        report = self._generate_markdown_report(state)
        
        logger.success("Paper review report generated successfully")
        
        return {
            "paper_report": report,
        }
    
    def _generate_markdown_report(self, state: PaperReviewAgentState) -> str:
        """Markdownレポートを生成.
        
        Args:
        ----
            state: 現在の状態
            
        Returns:
        -------
            Markdown形式のレポート
        """
        lines = []
        
        # タイトル
        lines.append("# 論文レビューレポート")
        lines.append("")
        lines.append(f"**生成日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}")
        lines.append("")
        
        # 検索条件
        lines.append("## 検索条件")
        lines.append("")
        lines.append(f"- **学会**: {state.venue} {state.year}")
        lines.append(f"- **キーワード**: {state.keywords or '指定なし'}")
        
        # 研究説明文を追加
        criteria = state.evaluation_criteria
        if criteria.research_description:
            lines.append(f"- **研究説明**: {criteria.research_description}")
        
        lines.append("")
        
        # ヒット件数の詳細
        lines.append("## ヒット件数")
        lines.append("")
        lines.append(f"- **全論文数**: {len(state.papers)}件")
        lines.append(f"- **評価対象論文数**: {len(state.evaluated_papers)}件")
        lines.append(f"- **ランク対象論文数**: {len(state.ranked_papers)}件")
        if state.top_papers:
            lines.append(f"- **最終選出論文数**: {len(state.top_papers)}件")
        lines.append("")
        
        # 評価基準
        lines.append("## 評価基準")
        lines.append("")
        lines.append(f"- **研究興味キーワード**: {', '.join(criteria.research_interests)}")
        lines.append(f"- **最小関連性スコア**: {criteria.min_relevance_score}")
        if criteria.min_rating:
            lines.append(f"- **最小レビュー評価**: {criteria.min_rating}/10")
        lines.append(f"- **新規性重視**: {'はい' if criteria.focus_on_novelty else 'いいえ'}")
        lines.append(f"- **インパクト重視**: {'はい' if criteria.focus_on_impact else 'いいえ'}")
        lines.append("")
        
        # キーワードと同義語
        if state.synonyms:
            lines.append("## キーワードと同義語")
            lines.append("")
            lines.append("各キーワードに対してLLMが生成した同義語を使用して論文を検索しました。")
            lines.append("")
            for keyword, syns in state.synonyms.items():
                lines.append(f"### {keyword}")
                lines.append("")
                if syns:
                    lines.append("**同義語**:")
                    for syn in syns:
                        lines.append(f"- {syn}")
                else:
                    lines.append("同義語なし（元のキーワードのみ使用）")
                lines.append("")
        
        # 統計情報（評価対象論文全体の統計）
        if state.ranked_papers:
            scores = [p.overall_score for p in state.ranked_papers if p.overall_score]
            ratings = [p.rating_avg for p in state.ranked_papers if p.rating_avg]
            
            lines.append("## 📊 評価対象論文の統計")
            lines.append("")
            lines.append(f"評価対象: {len(state.ranked_papers)}件")
            lines.append("")
            if scores:
                lines.append(f"- **平均総合スコア**: {sum(scores) / len(scores):.3f}")
                lines.append(f"- **最高スコア**: {max(scores):.3f}")
                lines.append(f"- **最低スコア**: {min(scores):.3f}")
            if ratings:
                lines.append(f"- **平均OpenReview評価**: {sum(ratings) / len(ratings):.2f}")
            lines.append("")
            lines.append("*注: 以下に表示されるトップ論文は、上記の評価対象から選出された上位論文です。*")
            lines.append("")
        
        # トップ論文（LLM評価後はtop_papersから、なければranked_papersから）
        lines.append("## トップ論文")
        lines.append("")
        
        # top_papersがあればそれを使用（LLM評価済み）、なければranked_papersを使用
        papers_to_display = state.top_papers if state.top_papers else state.ranked_papers[:10]
        
        for i, paper_data in enumerate(papers_to_display[:20], 1):  # 上位20件
            # paper_dataが辞書の場合とEvaluatedPaperオブジェクトの場合を処理
            if isinstance(paper_data, dict):
                paper = paper_data
                rank = paper.get('rank', i)
            else:
                paper = paper_data
                rank = getattr(paper, 'rank', i)
            
            # タイトルを取得（辞書とオブジェクト両対応）
            title = paper.get('title') if isinstance(paper, dict) else paper.title
            lines.append(f"### {rank}. {title}")
            lines.append("")
            
            # TL;DR（3行要約）を生成
            ai_rationale = paper.get('ai_rationale') if isinstance(paper, dict) else getattr(paper, 'ai_rationale', None)
            review_summary = paper.get('review_summary') if isinstance(paper, dict) else getattr(paper, 'review_summary', None)
            decision = paper.get('decision') if isinstance(paper, dict) else getattr(paper, 'decision', None)
            
            lines.append("#### 🎯 TL;DR")
            lines.append("")
            
            # AI評価から要点を抽出（最初の100文字程度）
            if ai_rationale and ai_rationale.strip():
                tldr_text = ai_rationale[:150].split('。')[0] + '。'
                lines.append(f"- **提案内容・強み**: {tldr_text}")
            
            # レビュー要約から評価を抽出
            if review_summary and review_summary.strip():
                review_tldr = review_summary[:100].split('。')[0] + '。'
                lines.append(f"- **レビュー評価**: {review_tldr}")
            
            # 採択判定
            if decision and decision != "N/A":
                decision_lower = decision.lower()
                if "oral" in decision_lower:
                    lines.append(f"- **判定**: 採択（🎤 Oral発表）")
                elif "spotlight" in decision_lower:
                    lines.append(f"- **判定**: 採択（✨ Spotlight）")
                elif "poster" in decision_lower:
                    lines.append(f"- **判定**: 採択（📊 Poster）")
                elif "accept" in decision_lower:
                    lines.append(f"- **判定**: 採択")
                else:
                    lines.append(f"- **判定**: {decision}")
            
            lines.append("")
            
            # スコアを視覚的に見やすく表示（複数行）
            overall_score = paper.get('overall_score') if isinstance(paper, dict) else getattr(paper, 'overall_score', None)
            relevance_score = paper.get('relevance_score') if isinstance(paper, dict) else getattr(paper, 'relevance_score', None)
            novelty_score = paper.get('novelty_score') if isinstance(paper, dict) else getattr(paper, 'novelty_score', None)
            impact_score = paper.get('impact_score') if isinstance(paper, dict) else getattr(paper, 'impact_score', None)
            practicality_score = paper.get('practicality_score') if isinstance(paper, dict) else getattr(paper, 'practicality_score', None)
            rating_avg = paper.get('rating_avg') if isinstance(paper, dict) else getattr(paper, 'rating_avg', None)
            
            if overall_score is not None:
                lines.append(f"**総合: {overall_score:.3f}**")
            
            # 詳細スコアを1行にまとめる
            detail_scores = []
            if relevance_score is not None:
                detail_scores.append(f"関連性: {relevance_score:.2f}")
            if novelty_score is not None:
                detail_scores.append(f"新規性: {novelty_score:.2f}")
            if impact_score is not None:
                detail_scores.append(f"インパクト: {impact_score:.2f}")
            if practicality_score is not None:
                detail_scores.append(f"実用性: {practicality_score:.2f}")
            
            if detail_scores:
                lines.append(" / ".join(detail_scores))
            
            # OpenReview評価を別行に（スケール統一のため /10 を削除）
            if rating_avg is not None:
                lines.append(f"OpenReview: {rating_avg:.2f}")
            
            # 採択情報を強調
            if decision and decision != "N/A":
                decision_lower = decision.lower()
                if "oral" in decision_lower:
                    lines.append("採択: 🎤 **Oral**")
                elif "spotlight" in decision_lower:
                    lines.append("採択: ✨ **Spotlight**")
                elif "poster" in decision_lower:
                    lines.append("採択: 📊 **Poster**")
                elif "accept" in decision_lower:
                    lines.append("採択: ✅ **Accept**")
            
            lines.append("")
            
            # 著者情報を表示（キーワードの前）
            authors = paper.get('authors') if isinstance(paper, dict) else paper.authors
            if authors:
                authors_display = ", ".join(authors[:3])
                if len(authors) > 3:
                    authors_display += f" 他{len(authors) - 3}名"
                lines.append(f"**著者**: {authors_display}")
                lines.append("")
            
            # キーワード（著者の後）
            keywords = paper.get('keywords') if isinstance(paper, dict) else paper.keywords
            if keywords:
                lines.append(f"**キーワード**: {', '.join(keywords[:5])}")
                lines.append("")
            
            # 概要（英文の冒頭5-7文のみ表示、全文は折りたたみ）
            abstract = paper.get('abstract') if isinstance(paper, dict) else getattr(paper, 'abstract', '')
            if abstract and abstract.strip():
                lines.append("#### 概要")
                lines.append("")
                
                # 英文を文単位で分割（'. ' で区切り）し、冒頭5-7文のみ表示
                sentences = abstract.split('. ')
                
                # 最初の5-7文を抽出（長さに応じて調整）
                if len(sentences) >= 7:
                    abstract_short = '. '.join(sentences[:7]) + '.'
                elif len(sentences) >= 5:
                    abstract_short = '. '.join(sentences[:5]) + '.'
                elif len(sentences) >= 3:
                    abstract_short = '. '.join(sentences[:3]) + '.'
                else:
                    # 文が少ない場合はそのまま
                    abstract_short = abstract
                
                lines.append(abstract_short)
                lines.append("")
                
                # 英語原文の全文を折りたたみで提供（短縮版より長い場合のみ）
                if len(abstract) > len(abstract_short) + 10:  # 10文字以上長い場合のみ
                    lines.append("<details>")
                    lines.append("<summary>📄 英語原文（全文）を表示</summary>")
                    lines.append("")
                    lines.append(abstract)
                    lines.append("")
                    lines.append("</details>")
                    lines.append("")
            
            # 評価ハイライト（AI評価 + レビュー要約を統合）
            if (ai_rationale and ai_rationale.strip()) or (review_summary and review_summary.strip()):
                lines.append("#### 📊 評価ハイライト")
                lines.append("")
                
                if ai_rationale and ai_rationale.strip():
                    lines.append("**AI分析**:")
                    lines.append(ai_rationale)
                    lines.append("")
                
                if review_summary and review_summary.strip():
                    lines.append("**レビュー要約**:")
                    lines.append(review_summary)
                    lines.append("")
            
            # レビューの詳細（Strengths/Weaknesses）- コメントアウト（ユーザー要望により非表示）
            # reviews = paper.get('reviews') if isinstance(paper, dict) else getattr(paper, 'reviews', [])
            # if reviews and len(reviews) > 0:
            #     lines.append("#### 📊 レビュー詳細")
            #     lines.append("")
            #     for review_idx, review in enumerate(reviews[:3], 1):  # 最大3件のレビュー
            #         review_rating = review.get('rating', 'N/A')
            #         review_confidence = review.get('confidence', 'N/A')
            #         lines.append(f"**レビュー {review_idx}** (評価: {review_rating}, 確信度: {review_confidence})")
            #         lines.append("")
            #         
            #         # サマリー
            #         summary = review.get('summary', '')
            #         if summary and summary.strip():
            #             lines.append("**要約:**")
            #             summary_text = summary[:300] + ("..." if len(summary) > 300 else "")
            #             lines.append(summary_text)
            #             lines.append("")
            #         
            #         # 強み
            #         strengths = review.get('strengths', '')
            #         if strengths and strengths.strip():
            #             lines.append("**強み:**")
            #             strengths_text = strengths[:300] + ("..." if len(strengths) > 300 else "")
            #             lines.append(strengths_text)
            #             lines.append("")
            #         
            #         # 弱み
            #         weaknesses = review.get('weaknesses', '')
            #         if weaknesses and weaknesses.strip():
            #             lines.append("**弱み:**")
            #             weaknesses_text = weaknesses[:300] + ("..." if len(weaknesses) > 300 else "")
            #             lines.append(weaknesses_text)
            #             lines.append("")
            #     
            #     if len(reviews) > 3:
            #         lines.append(f"*他 {len(reviews) - 3} 件のレビューは省略*")
            #         lines.append("")
            
            # リンク（シンプルに）
            forum_url = paper.get('forum_url') if isinstance(paper, dict) else paper.forum_url
            pdf_url = paper.get('pdf_url') if isinstance(paper, dict) else paper.pdf_url
            lines.append(f"🔗 [OpenReview]({forum_url}) | [PDF]({pdf_url})")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
    
    def _translate_field_name(self, field: str) -> str:
        """レビューフィールド名を日本語に翻訳.
        
        Args:
        ----
            field: 英語のフィールド名
            
        Returns:
        -------
            日本語のフィールド名
        """
        translations = {
            # 基本スコア
            'rating': '総合評価 (Rating)',
            'overall_recommendation': '総合評価 (Overall Recommendation)',
            'confidence': '確信度 (Confidence)',
            'score': 'スコア (Score)',
            'recommendation': '推薦度 (Recommendation)',
            
            # ICLR/NeurIPS/ICML 共通フィールド
            'soundness': '健全性 (Soundness)',
            'presentation': 'プレゼンテーション (Presentation)',
            'contribution': '貢献度 (Contribution)',
            'originality': '独創性 (Originality)',
            'quality': '品質 (Quality)',
            'clarity': '明瞭性 (Clarity)',
            'significance': '重要性 (Significance)',
            
            # ICML固有フィールド
            'experimental_designs_or_analyses': '実験設計・分析 (Experimental Design)',
            'methods_and_evaluation_criteria': '手法・評価基準 (Methods & Evaluation)',
            'reproducibility': '再現性 (Reproducibility)',
            'claims_and_evidence': '主張と根拠 (Claims & Evidence)',
            'impact': 'インパクト (Impact)',
            'novelty': '新規性 (Novelty)',
            
            # その他
            'technical_novelty_and_significance': '技術的新規性・重要性',
            'potential_for_real_world_impact': '実世界へのインパクトの可能性',
            'ethical_considerations': '倫理的考慮事項',
        }
        
        return translations.get(field, field.replace('_', ' ').title())

