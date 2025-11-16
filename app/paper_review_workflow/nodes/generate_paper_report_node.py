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
        
        # 統計情報
        if state.ranked_papers:
            scores = [p.overall_score for p in state.ranked_papers if p.overall_score]
            ratings = [p.rating_avg for p in state.ranked_papers if p.rating_avg]
            
            lines.append("## 統計情報")
            lines.append("")
            if scores:
                lines.append(f"- **平均総合スコア**: {sum(scores) / len(scores):.3f}")
                lines.append(f"- **最高スコア**: {max(scores):.3f}")
                lines.append(f"- **最低スコア**: {min(scores):.3f}")
            if ratings:
                lines.append(f"- **平均レビュー評価**: {sum(ratings) / len(ratings):.2f}/10")
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
            
            # スコア表示（統合LLM評価版）
            lines.append("#### スコア")
            lines.append("")
            lines.append(f"| 項目 | スコア |")
            lines.append(f"|------|--------|")
            
            # 総合スコア（4つの重み付き平均）
            overall_score = paper.get('overall_score') if isinstance(paper, dict) else getattr(paper, 'overall_score', None)
            if overall_score is not None:
                lines.append(f"| **総合スコア** | **{overall_score:.3f}** |")
            
            # AI評価詳細スコア
            relevance_score = paper.get('relevance_score') if isinstance(paper, dict) else getattr(paper, 'relevance_score', None)
            if relevance_score is not None:
                lines.append(f"| 　├ 関連性 | {relevance_score:.3f} |")
            
            novelty_score = paper.get('novelty_score') if isinstance(paper, dict) else getattr(paper, 'novelty_score', None)
            if novelty_score is not None:
                lines.append(f"| 　├ 新規性 | {novelty_score:.3f} |")
            
            impact_score = paper.get('impact_score') if isinstance(paper, dict) else getattr(paper, 'impact_score', None)
            if impact_score is not None:
                lines.append(f"| 　├ インパクト | {impact_score:.3f} |")
            
            practicality_score = paper.get('practicality_score') if isinstance(paper, dict) else getattr(paper, 'practicality_score', None)
            if practicality_score is not None:
                lines.append(f"| 　└ 実用性 | {practicality_score:.3f} |")
            
            # OpenReview平均評価
            rating_avg = paper.get('rating_avg') if isinstance(paper, dict) else getattr(paper, 'rating_avg', None)
            if rating_avg is not None:
                lines.append(f"| OpenReview評価 | {rating_avg:.2f}/10 |")
            lines.append("")
            
            # 採択判定と発表形式
            decision = paper.get('decision') if isinstance(paper, dict) else getattr(paper, 'decision', None)
            if decision and decision != "N/A":
                lines.append(f"**採択判定**: {decision}")
                
                # 発表形式を抽出（NeurIPSなどの場合）
                decision_lower = decision.lower()
                if "oral" in decision_lower:
                    lines.append("  - 🎤 **発表形式**: Oral Presentation（口頭発表）")
                elif "spotlight" in decision_lower:
                    lines.append("  - ✨ **発表形式**: Spotlight Presentation")
                elif "poster" in decision_lower:
                    lines.append("  - 📊 **発表形式**: Poster Presentation")
                lines.append("")
            
            # 著者
            authors = paper.get('authors') if isinstance(paper, dict) else paper.authors
            if authors:
                authors_display = ", ".join(authors[:5])
                if len(authors) > 5:
                    authors_display += f" 他{len(authors) - 5}名"
                lines.append(f"**著者**: {authors_display}")
                lines.append("")
            
            # キーワード
            keywords = paper.get('keywords') if isinstance(paper, dict) else paper.keywords
            if keywords:
                lines.append(f"**キーワード**: {', '.join(keywords[:8])}")
                lines.append("")
            
            # アブストラクト（全文表示、セクションとして独立）
            abstract = paper.get('abstract') if isinstance(paper, dict) else getattr(paper, 'abstract', '')
            if abstract and abstract.strip():
                lines.append("#### 概要")
                lines.append("")
                lines.append(abstract)
                lines.append("")
            
            # AI評価（統合LLM評価）
            ai_rationale = paper.get('ai_rationale') if isinstance(paper, dict) else getattr(paper, 'ai_rationale', None)
            if ai_rationale and ai_rationale.strip():
                lines.append("#### 🤖 AI評価")
                lines.append("")
                lines.append(ai_rationale)
                lines.append("")
            
            # レビュー要約
            review_summary = paper.get('review_summary') if isinstance(paper, dict) else getattr(paper, 'review_summary', None)
            if review_summary and review_summary.strip():
                lines.append("#### 📊 レビュー要約")
                lines.append("")
                lines.append(review_summary)
                lines.append("")
            
            # フィールド活用の説明
            field_insights = paper.get('field_insights') if isinstance(paper, dict) else getattr(paper, 'field_insights', None)
            if field_insights and field_insights.strip():
                lines.append("#### 🔍 評価データソース")
                lines.append("")
                lines.append(field_insights)
                lines.append("")
            
            # Meta Review（エリアチェアのまとめ）
            meta_review = paper.get('meta_review') if isinstance(paper, dict) else getattr(paper, 'meta_review', None)
            if meta_review and meta_review.strip():
                lines.append("#### 📋 Meta Review（エリアチェアのまとめ）")
                lines.append("")
                # 長い場合は制限（最初の800文字程度）
                if len(meta_review) > 800:
                    lines.append(meta_review[:800] + "...")
                else:
                    lines.append(meta_review)
                lines.append("")
            
            # Decision の詳細コメント
            decision_comment = paper.get('decision_comment') if isinstance(paper, dict) else getattr(paper, 'decision_comment', None)
            if decision_comment and decision_comment.strip():
                lines.append("#### 📝 採択理由")
                lines.append("")
                # 長い場合は制限
                if len(decision_comment) > 600:
                    lines.append(decision_comment[:600] + "...")
                else:
                    lines.append(decision_comment)
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
            
            # レビュースコアの平均値を表示
            reviews = paper.get('reviews') if isinstance(paper, dict) else getattr(paper, 'reviews', [])
            if reviews and len(reviews) > 0:
                lines.append("#### 📊 レビュースコアの平均")
                lines.append("")
                
                # 数値フィールドを収集
                score_fields = {}
                for review in reviews:
                    for key, value in review.items():
                        # 数値または数値に変換可能なフィールドのみ
                        if key in ['summary', 'strengths', 'weaknesses', 'detailed_comments', 
                                  'main_review', 'review_text', 'comments', 'strengths_and_weaknesses']:
                            continue  # テキストフィールドはスキップ
                        
                        try:
                            # 数値に変換してみる
                            if isinstance(value, (int, float)):
                                numeric_value = float(value)
                            elif isinstance(value, str) and value.strip():
                                # "3.5/5" のような形式を処理
                                if '/' in value:
                                    numeric_value = float(value.split('/')[0].strip())
                                else:
                                    numeric_value = float(value)
                            else:
                                continue
                            
                            if key not in score_fields:
                                score_fields[key] = []
                            score_fields[key].append(numeric_value)
                        except (ValueError, TypeError):
                            continue
                
                # 平均値を計算して表示
                if score_fields:
                    lines.append("| 項目 | 平均値 | レビュー数 |")
                    lines.append("|------|--------|-----------|")
                    
                    # rating と confidence を最初に表示
                    priority_fields = ['rating', 'overall_recommendation', 'confidence']
                    for field in priority_fields:
                        if field in score_fields:
                            avg_value = sum(score_fields[field]) / len(score_fields[field])
                            count = len(score_fields[field])
                            field_name = self._translate_field_name(field)
                            lines.append(f"| {field_name} | {avg_value:.2f} | {count} |")
                    
                    # その他のフィールドをアルファベット順に表示
                    other_fields = sorted([f for f in score_fields.keys() if f not in priority_fields])
                    for field in other_fields:
                        avg_value = sum(score_fields[field]) / len(score_fields[field])
                        count = len(score_fields[field])
                        field_name = self._translate_field_name(field)
                        lines.append(f"| {field_name} | {avg_value:.2f} | {count} |")
                    
                    lines.append("")
                    lines.append(f"*{len(reviews)}件のレビューから集計*")
                    lines.append("")
            
            # Author Final Remarks
            author_remarks = paper.get('author_remarks') if isinstance(paper, dict) else getattr(paper, 'author_remarks', None)
            if author_remarks and author_remarks.strip():
                lines.append("#### 💬 著者からのコメント")
                lines.append("")
                # 長い場合は制限
                if len(author_remarks) > 400:
                    lines.append(author_remarks[:400] + "...")
                else:
                    lines.append(author_remarks)
                lines.append("")
            
            # LLM評価理由
            llm_rationale = paper.get('llm_rationale') if isinstance(paper, dict) else getattr(paper, 'llm_rationale', None)
            if llm_rationale:
                lines.append("#### AI評価（内容分析）")
                lines.append("")
                lines.append(llm_rationale)
                lines.append("")
            
            # リンク
            forum_url = paper.get('forum_url') if isinstance(paper, dict) else paper.forum_url
            pdf_url = paper.get('pdf_url') if isinstance(paper, dict) else paper.pdf_url
            lines.append(f"**🔗 リンク**:")
            lines.append(f"- [OpenReview]({forum_url})")
            lines.append(f"- [PDF]({pdf_url})")
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

