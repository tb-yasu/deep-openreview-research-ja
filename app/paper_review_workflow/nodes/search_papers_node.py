"""Node for searching papers using OpenReview API."""

import json
from typing import Any

from loguru import logger

from app.paper_review_workflow.models.state import (
    PaperReviewAgentState,
    Paper,
)
from app.paper_review_workflow.tools import search_papers


class SearchPapersNode:
    """論文を検索するノード.
    
    OpenReview APIを使用して、指定された学会・年の論文を検索し、
    状態に保存します。
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
        logger.info(
            f"Searching papers from {state.venue} {state.year} "
            f"(max: {state.max_papers}, keywords: {state.keywords})"
        )
        
        try:
            # ツールを呼び出して論文を検索
            result = self.tool.invoke({
                "venue": state.venue,
                "year": state.year,
                "keywords": state.keywords,
                "max_results": state.max_papers,
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

