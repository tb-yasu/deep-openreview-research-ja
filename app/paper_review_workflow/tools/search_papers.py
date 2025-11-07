"""Tool for searching papers using OpenReview API."""

import json
from pathlib import Path
from typing import Any

import openreview
from langchain_core.tools import tool
from loguru import logger

from app.paper_review_workflow.tools.cache_utils import (
    get_cache_key,
    get_cached_data,
    save_to_cache,
)

from app.paper_review_workflow.tools.cache_manager import CacheManager

# グローバルキャッシュマネージャー
_cache_manager = CacheManager(cache_dir="storage/cache", ttl_hours=24)


@tool
def search_papers(
    venue: str,
    year: int,
    keywords: str | None = None,
    max_results: int = 100,
) -> str:
    """OpenReview APIを使用して、指定された学会・年の採択論文を検索します.

    Args:
    ----
        venue (str): 学会名（例: 'NeurIPS', 'ICML', 'ICLR'）
        year (int): 開催年（例: 2024）
        keywords (str, optional): 検索キーワード（論文タイトルやアブストラクトで絞り込み）
        max_results (int): 最大取得件数（デフォルト: 100）

    Returns:
    -------
        str: 論文情報のJSONリスト。各論文には以下の情報が含まれます：
            - id: 論文ID
            - title: 論文タイトル
            - authors: 著者リスト
            - abstract: アブストラクト
            - keywords: キーワードリスト
            - venue: 学会名
            - year: 年
            - pdf_url: PDF URL
            - forum_url: フォーラムURL

    """
    try:
        # まず全論文のローカルキャッシュをチェック
        data_dir = Path(f"storage/papers_data/{venue}_{year}")
        papers_file = data_dir / "all_papers.json"
        
        if papers_file.exists():
            logger.info(f"Loading from local papers data: {papers_file}")
            all_papers = json.loads(papers_file.read_text(encoding="utf-8"))
            
            # キーワードでフィルタリング
            filtered_papers: list[dict[str, Any]] = []
            for paper in all_papers:
                if keywords:
                    title_match = keywords.lower() in paper["title"].lower()
                    abstract_match = keywords.lower() in paper["abstract"].lower()
                    if not (title_match or abstract_match):
                        continue
                
                filtered_papers.append(paper)
                
                if len(filtered_papers) >= max_results:
                    break
            
            logger.info(f"Found {len(filtered_papers)} papers (filtered from {len(all_papers)} total)")
            return json.dumps(filtered_papers, ensure_ascii=False, indent=2)
        
        # ローカルキャッシュがない場合は従来のキャッシュをチェック
        logger.info("No local papers data found. Checking temporary cache...")
        cache_key_params = {
            "venue": venue,
            "year": year,
            "keywords": keywords,
            "max_results": max_results,
        }
        cached_result = _cache_manager.get(prefix="search_papers", **cache_key_params)
        
        if cached_result:
            logger.info(f"Using temporary cached results for {venue} {year} (keywords: {keywords})")
            return cached_result
        
        # キャッシュがない場合はAPIから取得
        logger.warning(f"No cache found. Downloading from OpenReview API...")
        logger.warning(f"TIP: Run 'python fetch_all_papers.py' to download all papers once")
        
        # OpenReview APIクライアントを初期化（認証なし）
        client = openreview.api.OpenReviewClient(baseurl="https://api2.openreview.net")

        # 学会のinvitation IDを構成
        # 例: NeurIPS.cc/2024/Conference/-/Submission
        venue_id = f"{venue}.cc/{year}/Conference"
        
        # 採択論文を取得
        logger.info(f"Searching papers from {venue} {year}...")
        submissions = client.get_all_notes(
            invitation=f"{venue_id}/-/Submission",
            details="replies",
        )

        papers: list[dict[str, Any]] = []
        for submission in submissions:
            # キーワードフィルタリング
            if keywords:
                title = submission.content.get("title", {})
                title_value = title.get("value", "") if isinstance(title, dict) else str(title)
                
                abstract = submission.content.get("abstract", {})
                abstract_value = abstract.get("value", "") if isinstance(abstract, dict) else str(abstract)
                
                title_match = keywords.lower() in title_value.lower()
                abstract_match = keywords.lower() in abstract_value.lower()
                
                if not (title_match or abstract_match):
                    continue

            # 論文情報を抽出
            title = submission.content.get("title", {})
            title_value = title.get("value", "") if isinstance(title, dict) else str(title)
            
            authors = submission.content.get("authors", {})
            authors_value = authors.get("value", []) if isinstance(authors, dict) else []
            
            abstract = submission.content.get("abstract", {})
            abstract_value = abstract.get("value", "") if isinstance(abstract, dict) else str(abstract)
            
            keywords_field = submission.content.get("keywords", {})
            keywords_value = keywords_field.get("value", []) if isinstance(keywords_field, dict) else []
            
            paper_info = {
                "id": submission.id,
                "title": title_value,
                "authors": authors_value,
                "abstract": abstract_value,
                "keywords": keywords_value,
                "venue": venue,
                "year": year,
                "pdf_url": f"https://openreview.net/pdf?id={submission.id}",
                "forum_url": f"https://openreview.net/forum?id={submission.id}",
            }
            papers.append(paper_info)
            
            # max_resultsに達したら終了
            if len(papers) >= max_results:
                break

        logger.info(f"Found {len(papers)} papers from {venue} {year}")
        result = json.dumps(papers, ensure_ascii=False, indent=2)
        
        # キャッシュに保存
        _cache_manager.set(result, prefix="search_papers", **cache_key_params)
        
        return result

    except Exception as e:
        error_msg = f"Error searching papers: {e!s}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg}, ensure_ascii=False)

