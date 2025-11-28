"""Node for searching papers using OpenReview API or Hybrid Search."""

import json
from pathlib import Path
from typing import Any

from loguru import logger

from app.paper_review_workflow.models.state import (
    PaperReviewAgentState,
    Paper,
)
from app.paper_review_workflow.tools import search_papers


class SearchPapersNode:
    """論文を検索するノード.
    
    OpenReview APIまたはハイブリッド検索を使用して、
    指定された学会・年の論文を検索し、状態に保存します。
    """
    
    def __init__(self) -> None:
        """SearchPapersNodeを初期化."""
        self.tool = search_papers
    
    def __call__(self, state: PaperReviewAgentState) -> dict[str, Any]:
        """論文検索を実行.
        
        Args:
        ----
            state: 現在の状態
            
        Returns:
        -------
            更新された状態の辞書
        """
        accepted_status = "採択論文のみ" if state.accepted_only else "全論文（採択・不採択含む）"
        
        # ハイブリッド検索が有効かつインデックスが存在する場合
        if state.use_hybrid_search:
            return self._hybrid_search(state, accepted_status)
        else:
            return self._standard_search(state, accepted_status)
    
    def _hybrid_search(self, state: PaperReviewAgentState, accepted_status: str) -> dict[str, Any]:
        """ハイブリッド検索（ベクトル + キーワード）を実行."""
        try:
            from search_engine import hybrid_search, get_db_path
        except ImportError:
            logger.warning("⚠️ search_engine module not found, falling back to standard search")
            return self._standard_search(state, accepted_status)
        
        # インデックスの存在確認
        db_path = get_db_path(state.venue, state.year)
        if not db_path.exists():
            logger.warning(
                f"⚠️ Vector index not found at {db_path}\n"
                f"   Run: python indexer.py --venue {state.venue} --year {state.year}\n"
                f"   Falling back to standard search..."
            )
            return self._standard_search(state, accepted_status)
        
        # 検索クエリの準備
        query_text = state.evaluation_criteria.research_description or ""
        keywords = state.evaluation_criteria.research_interests or []
        
        if not query_text and not keywords:
            logger.warning("⚠️ No research description or keywords provided, falling back to standard search")
            return self._standard_search(state, accepted_status)
        
        logger.info(
            f"🔍 Hybrid search in {state.venue} {state.year} "
            f"(max: {state.max_papers}, {accepted_status})"
        )
        logger.info(f"   Query: {query_text[:80]}..." if len(query_text) > 80 else f"   Query: {query_text}")
        logger.info(f"   Keywords: {', '.join(keywords[:5])}" + (f" ... ({len(keywords)} total)" if len(keywords) > 5 else ""))
        
        try:
            # ハイブリッド検索を実行
            results = hybrid_search(
                query_text=query_text,
                keywords=keywords,
                venue=state.venue,
                year=state.year,
                top_k=state.max_papers,
                vector_weight=state.hybrid_vector_weight,
                keyword_weight=state.hybrid_keyword_weight,
                accepted_only=state.accepted_only,
            )
            
            # Paper オブジェクトに変換
            papers: list[Paper] = []
            for paper_data in results:
                try:
                    paper = Paper(**paper_data)
                    papers.append(paper)
                except Exception as e:
                    logger.warning(f"Failed to parse paper data: {e}")
                    continue
            
            # 検索結果の内訳をログ出力
            search_sources = {}
            for paper_data in results:
                src = paper_data.get("search_source", "unknown")
                search_sources[src] = search_sources.get(src, 0) + 1
            
            logger.success(f"✓ Hybrid search found {len(papers)} papers")
            for src, count in search_sources.items():
                logger.info(f"   - {src}: {count}")
            
            return {
                "papers": papers,
            }
            
        except Exception as e:
            error_msg = f"Hybrid search failed: {e!s}"
            logger.error(error_msg)
            logger.info("⚠️ Falling back to standard search...")
            return self._standard_search(state, accepted_status)
    
    def _standard_search(self, state: PaperReviewAgentState, accepted_status: str) -> dict[str, Any]:
        """標準のOpenReview API検索を実行."""
        logger.info(
            f"Searching papers from {state.venue} {state.year} "
            f"(max: {state.max_papers}, keywords: {state.keywords}, {accepted_status})"
        )
        
        try:
            # ツールを呼び出して論文を検索
            result = self.tool.invoke({
                "venue": state.venue,
                "year": state.year,
                "keywords": state.keywords,
                "max_results": state.max_papers,
                "accepted_only": state.accepted_only,
            })
            
            # 結果をパース
            papers_data = json.loads(result)
            
            # エラーチェック
            if isinstance(papers_data, dict) and "error" in papers_data:
                error_msg = f"Error searching papers: {papers_data['error']}"
                logger.error(error_msg)
                return {
                    "papers": [],
                    "error_messages": [error_msg],
                }
            
            # Paper オブジェクトのリストに変換
            papers: list[Paper] = []
            for paper_data in papers_data:
                try:
                    paper = Paper(**paper_data)
                    papers.append(paper)
                except Exception as e:
                    logger.warning(f"Failed to parse paper data: {e}")
                    continue
            
            logger.info(f"Successfully found {len(papers)} papers")
            
            return {
                "papers": papers,
            }
            
        except Exception as e:
            error_msg = f"Unexpected error in SearchPapersNode: {e!s}"
            logger.error(error_msg)
            return {
                "papers": [],
                "error_messages": [error_msg],
            }

