"""ランキングされた論文のレビューをオンデマンドで取得するノード"""

from typing import Any

from loguru import logger

from app.paper_review_workflow.models.state import (
    PaperReviewAgentState,
    EvaluatedPaper,
)


class FetchReviewsNode:
    """レビューをオンデマンドで取得するノード
    
    このノードは、まだレビューを持っていないランキング済み論文のレビューデータを取得します。
    繰り返しのAPI呼び出しを避けるためにレビューキャッシュシステムを使用します。
    """
    
    def __init__(self) -> None:
        """FetchReviewsNodeを初期化"""
        pass
    
    def __call__(self, state: PaperReviewAgentState) -> dict[str, Any]:
        """ランキング済み論文のレビューを取得
        
        Args:
        ----
            state: ranked_papersを含む現在の状態
            
        Returns:
        -------
            レビューがマージされたranked_papersを含む更新された状態辞書
        """
        if not state.ranked_papers:
            logger.warning("レビューを取得する論文がありません")
            return {}
        
        # 論文がすでにレビューデータを持っているか確認
        papers_without_reviews = [
            p for p in state.ranked_papers 
            if not p.reviews or len(p.reviews) == 0
        ]
        
        if not papers_without_reviews:
            logger.info("✓ すべてのランキング済み論文がすでにレビューデータを持っています")
            return {}
        
        logger.info(f"📚 {len(papers_without_reviews)}/{len(state.ranked_papers)} 件の論文がレビューデータを必要としています")
        
        try:
            # 循環インポートを避けるためにここでインポート
            from review_cache import fetch_reviews_on_demand, merge_reviews_into_papers
            
            # レビューが必要な論文IDを取得
            paper_ids = [p.id for p in papers_without_reviews]
            
            # オンデマンドでレビューを取得（キャッシュ付き）
            reviews = fetch_reviews_on_demand(
                paper_ids=paper_ids,
                venue=state.venue,
                year=state.year,
            )
            
            # レビューを論文にマージ
            # EvaluatedPaperオブジェクトをマージ用の辞書に変換
            papers_as_dicts = [p.model_dump() for p in state.ranked_papers]
            merged_papers = merge_reviews_into_papers(papers_as_dicts, reviews)
            
            # EvaluatedPaperオブジェクトに戻す
            updated_papers = []
            for paper_dict in merged_papers:
                try:
                    updated_paper = EvaluatedPaper(**paper_dict)
                    updated_papers.append(updated_paper)
                except Exception as e:
                    logger.warning(f"論文 {paper_dict.get('id')} の変換に失敗: {e}")
                    # 元の論文を保持
                    original = next((p for p in state.ranked_papers if p.id == paper_dict.get('id')), None)
                    if original:
                        updated_papers.append(original)
            
            # マージ後のレビュー付き論文数をカウント
            papers_with_reviews = sum(1 for p in updated_papers if p.reviews and len(p.reviews) > 0)
            logger.success(f"✓ レビューをマージ: {papers_with_reviews}/{len(updated_papers)} 件の論文がレビューデータを持っています")
            
            return {
                "ranked_papers": updated_papers,
            }
            
        except ImportError as e:
            logger.warning(f"⚠ review_cache モジュールが利用できません: {e}")
            logger.warning("⚠ レビューを取得せずに続行します")
            return {}
        except Exception as e:
            logger.error(f"❌ レビューの取得に失敗: {e}")
            logger.warning("⚠ レビューを取得せずに続行します")
            return {}

