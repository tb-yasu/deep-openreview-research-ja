"""Tool for fetching detailed paper metadata using OpenReview API."""

import json
from typing import Any

import openreview
from langchain_core.tools import tool
from loguru import logger


@tool
def fetch_paper_metadata(paper_id: str) -> str:
    """OpenReview APIを使用して、指定された論文IDの詳細メタデータを取得します.

    Args:
    ----
        paper_id (str): OpenReviewの論文ID（例: 'abc123def456'）

    Returns:
    -------
        str: 論文の詳細メタデータのJSON。以下の情報が含まれます：
            - id: 論文ID
            - title: 論文タイトル
            - authors: 著者リスト
            - abstract: アブストラクト
            - keywords: キーワードリスト
            - reviews: レビュー情報のリスト
            - rating_avg: 平均評価スコア
            - confidence_avg: 平均信頼度スコア
            - decision: 採択/不採択の判定
            - pdf_url: PDF URL
            - forum_url: フォーラムURL

    """
    try:
        # OpenReview APIクライアントを初期化
        client = openreview.api.OpenReviewClient(baseurl="https://api2.openreview.net")

        # 論文情報を取得
        logger.info(f"Fetching metadata for paper: {paper_id}")
        note = client.get_note(paper_id)

        # レビュー情報を取得
        reviews = client.get_notes(forum=paper_id, invitation=".*Review$")
        
        # 評価スコアを集計
        ratings: list[float] = []
        confidences: list[float] = []
        review_list: list[dict[str, Any]] = []
        
        for review in reviews:
            rating = review.content.get("rating", {})
            confidence = review.content.get("confidence", {})
            
            if isinstance(rating, dict) and "value" in rating:
                try:
                    # "8: accept" のような形式から数値を抽出
                    rating_value = float(str(rating["value"]).split(":")[0].strip())
                    ratings.append(rating_value)
                except (ValueError, IndexError):
                    pass
            
            if isinstance(confidence, dict) and "value" in confidence:
                try:
                    confidence_value = float(str(confidence["value"]).split(":")[0].strip())
                    confidences.append(confidence_value)
                except (ValueError, IndexError):
                    pass
            
            summary = review.content.get("summary", {})
            summary_value = summary.get("value", "") if isinstance(summary, dict) else str(summary)
            
            strengths = review.content.get("strengths", {})
            strengths_value = strengths.get("value", "") if isinstance(strengths, dict) else str(strengths)
            
            weaknesses = review.content.get("weaknesses", {})
            weaknesses_value = weaknesses.get("value", "") if isinstance(weaknesses, dict) else str(weaknesses)
            
            review_list.append({
                "rating": str(rating.get("value", "N/A")) if isinstance(rating, dict) else "N/A",
                "confidence": str(confidence.get("value", "N/A")) if isinstance(confidence, dict) else "N/A",
                "summary": summary_value,
                "strengths": strengths_value,
                "weaknesses": weaknesses_value,
            })

        # 採択判定を取得
        decisions = client.get_notes(forum=paper_id, invitation=".*Decision$")
        decision = "N/A"
        if decisions:
            decision_content = decisions[0].content.get("decision", {})
            decision = decision_content.get("value", "N/A") if isinstance(decision_content, dict) else str(decision_content)

        # メタデータを構築
        title = note.content.get("title", {})
        title_value = title.get("value", "") if isinstance(title, dict) else str(title)
        
        authors = note.content.get("authors", {})
        authors_value = authors.get("value", []) if isinstance(authors, dict) else []
        
        abstract = note.content.get("abstract", {})
        abstract_value = abstract.get("value", "") if isinstance(abstract, dict) else str(abstract)
        
        keywords = note.content.get("keywords", {})
        keywords_value = keywords.get("value", []) if isinstance(keywords, dict) else []
        
        metadata = {
            "id": note.id,
            "title": title_value,
            "authors": authors_value,
            "abstract": abstract_value,
            "keywords": keywords_value,
            "reviews": review_list,
            "rating_avg": sum(ratings) / len(ratings) if ratings else None,
            "confidence_avg": sum(confidences) / len(confidences) if confidences else None,
            "decision": decision,
            "pdf_url": f"https://openreview.net/pdf?id={note.id}",
            "forum_url": f"https://openreview.net/forum?id={note.id}",
        }

        logger.info(f"Fetched metadata for paper: {metadata['title']}")
        return json.dumps(metadata, ensure_ascii=False, indent=2)

    except Exception as e:
        error_msg = f"Error fetching paper metadata: {e!s}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg}, ensure_ascii=False)

