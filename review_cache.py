"""Review cache for on-demand fetching.

This module provides functionality to fetch and cache paper reviews on-demand.
Reviews are fetched only for papers that need them (e.g., top-ranked papers),
and cached locally to avoid repeated API calls.

Features:
- On-demand review fetching for specific papers
- Incremental caching (new reviews are added to existing cache)
- Efficient batch processing with rate limiting
- Cache statistics and hit/miss tracking

Usage:
    from review_cache import fetch_reviews_on_demand
    
    # Fetch reviews for specific papers
    reviews = fetch_reviews_on_demand(
        paper_ids=["paper_id_1", "paper_id_2"],
        venue="NeurIPS",
        year=2025,
    )

Author: Paper Review Agent Team
License: MIT
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import openreview
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

# Cache configuration
CACHE_FILENAME = "reviews_cache.json"


def get_cache_path(venue: str, year: int) -> Path:
    """Get the path to the reviews cache file.
    
    Args:
    ----
        venue: Conference name (e.g., "NeurIPS")
        year: Conference year (e.g., 2025)
        
    Returns:
    -------
        Path to the cache file
    """
    return Path(f"storage/papers_data/{venue}_{year}") / CACHE_FILENAME


def load_reviews_cache(venue: str, year: int) -> dict[str, dict[str, Any]]:
    """Load the reviews cache from disk.
    
    Args:
    ----
        venue: Conference name
        year: Conference year
        
    Returns:
    -------
        Dictionary mapping paper_id to review data
    """
    cache_path = get_cache_path(venue, year)
    
    if not cache_path.exists():
        return {}
    
    try:
        cache_data = json.loads(cache_path.read_text(encoding="utf-8"))
        return cache_data.get("reviews", {})
    except Exception as e:
        logger.warning(f"レビューキャッシュのロードに失敗: {e}")
        return {}


def save_reviews_cache(cache: dict[str, dict[str, Any]], venue: str, year: int) -> None:
    """Save the reviews cache to disk.
    
    Args:
    ----
        cache: Dictionary mapping paper_id to review data
        venue: Conference name
        year: Conference year
    """
    cache_path = get_cache_path(venue, year)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    cache_data = {
        "venue": venue,
        "year": year,
        "updated_at": datetime.now().isoformat(),
        "total_cached": len(cache),
        "reviews": cache,
    }
    
    cache_path.write_text(
        json.dumps(cache_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def fetch_single_paper_reviews(
    client: openreview.api.OpenReviewClient,
    paper_id: str,
) -> dict[str, Any]:
    """Fetch review data for a single paper.
    
    Args:
    ----
        client: OpenReview API client
        paper_id: Paper ID to fetch reviews for
        
    Returns:
    -------
        Dictionary containing review data
    """
    try:
        # Fetch all notes associated with this paper
        all_notes = client.get_notes(forum=paper_id)
        
        # Extract official reviews
        reviews = []
        ratings = []
        confidences = []
        
        for note in all_notes:
            invitations = getattr(note, 'invitations', [])
            if not any('Official_Review' in inv for inv in invitations):
                continue
            
            content = note.content if hasattr(note, 'content') else {}
            if not content:
                continue
            
            # Exclude obvious non-reviews
            if len(content) == 1 and ('comment' in content or 'rebuttal' in content):
                continue
            
            # Include if it has rating-like fields or is comprehensive
            score_fields = {'rating', 'overall_recommendation', 'score', 'recommendation'}
            if any(field in content for field in score_fields):
                pass  # Include
            elif 'summary' in content and len(content) >= 5:
                pass  # Include
            else:
                continue
            
            # Extract review data
            review_data = {}
            for field_name, field_value in content.items():
                if field_value is not None:
                    if isinstance(field_value, dict):
                        actual_value = field_value.get("value", "")
                    else:
                        actual_value = field_value
                    if actual_value or actual_value == 0:
                        review_data[field_name] = str(actual_value)
            
            reviews.append(review_data)
            
            # Parse rating
            for rating_field in ['rating', 'overall_recommendation', 'score', 'recommendation']:
                rating = content.get(rating_field, {})
                if isinstance(rating, dict) and "value" in rating:
                    try:
                        val = rating["value"]
                        if isinstance(val, (int, float)):
                            ratings.append(float(val))
                        else:
                            ratings.append(float(str(val).split(":")[0].strip()))
                        break
                    except (ValueError, IndexError, TypeError):
                        pass
            
            # Parse confidence
            confidence = content.get("confidence", {})
            if isinstance(confidence, dict) and "value" in confidence:
                try:
                    val = confidence["value"]
                    if isinstance(val, (int, float)):
                        confidences.append(float(val))
                    else:
                        confidences.append(float(str(val).split(":")[0].strip()))
                except (ValueError, IndexError, TypeError):
                    pass
        
        # Extract decision
        decisions = [
            note for note in all_notes
            if any('Decision' in inv for inv in getattr(note, 'invitations', []))
        ]
        decision = "N/A"
        decision_comment = ""
        if decisions:
            decision_content = decisions[0].content.get("decision", {})
            decision = decision_content.get("value", "N/A") if isinstance(decision_content, dict) else str(decision_content)
            
            decision_note = decisions[0].content
            decision_comment = (
                decision_note.get("comment", {}).get("value", "") or
                decision_note.get("justification", {}).get("value", "") or
                decision_note.get("metareview", {}).get("value", "")
            )
        
        # Extract Meta Review
        meta_reviews = [
            note for note in all_notes
            if any('Meta_Review' in inv for inv in getattr(note, 'invitations', []))
        ]
        meta_review_text = ""
        if meta_reviews:
            meta_content = meta_reviews[0].content
            meta_review_text = (
                meta_content.get("metareview", {}).get("value", "") or
                meta_content.get("recommendation", {}).get("value", "") or
                meta_content.get("summary", {}).get("value", "")
            )
        
        # Extract Author Final Remarks
        author_remarks = [
            note for note in all_notes
            if any('Author_Final_Remarks' in inv or 'Camera_Ready_Revision' in inv 
                   for inv in getattr(note, 'invitations', []))
        ]
        author_remarks_text = ""
        if author_remarks:
            remarks_content = author_remarks[0].content
            author_remarks_text = (
                remarks_content.get("author_remarks", {}).get("value", "") or
                remarks_content.get("comment", {}).get("value", "") or
                remarks_content.get("summary_of_changes", {}).get("value", "")
            )
        
        return {
            "reviews": reviews,
            "rating_avg": sum(ratings) / len(ratings) if ratings else None,
            "confidence_avg": sum(confidences) / len(confidences) if confidences else None,
            "decision": decision,
            "meta_review": meta_review_text,
            "author_remarks": author_remarks_text,
            "decision_comment": decision_comment,
            "fetched_at": datetime.now().isoformat(),
        }
        
    except Exception as e:
        logger.debug(f"{paper_id} のレビュー取得に失敗: {e}")
        return {
            "reviews": [],
            "rating_avg": None,
            "confidence_avg": None,
            "decision": "N/A",
            "meta_review": "",
            "author_remarks": "",
            "decision_comment": "",
            "fetched_at": datetime.now().isoformat(),
            "error": str(e),
        }


def fetch_reviews_on_demand(
    paper_ids: list[str],
    venue: str,
    year: int,
    rate_limit_delay: float = 1.2,
) -> dict[str, dict[str, Any]]:
    """Fetch reviews for specified papers, using cache when available.
    
    This function:
    1. Loads existing cache
    2. Identifies papers not in cache
    3. Fetches only missing reviews from API
    4. Updates cache with new reviews
    5. Returns combined results
    
    Args:
    ----
        paper_ids: List of paper IDs to fetch reviews for
        venue: Conference name (e.g., "NeurIPS")
        year: Conference year (e.g., 2025)
        rate_limit_delay: Delay between API calls in seconds (default: 1.2)
        
    Returns:
    -------
        Dictionary mapping paper_id to review data
    """
    if not paper_ids:
        return {}
    
    # Load existing cache
    cache = load_reviews_cache(venue, year)
    
    # Identify papers not in cache
    missing_ids = [pid for pid in paper_ids if pid not in cache]
    cached_count = len(paper_ids) - len(missing_ids)
    
    logger.info(f"📚 レビュー取得: {len(paper_ids)} 件の論文をリクエスト")
    logger.info(f"   └ キャッシュ済み: {cached_count} | 取得必要: {len(missing_ids)}")
    
    if not missing_ids:
        logger.success("✓ すべてのレビューがキャッシュにあります！")
        return {pid: cache[pid] for pid in paper_ids if pid in cache}
    
    # Initialize OpenReview client
    client = openreview.api.OpenReviewClient(baseurl="https://api2.openreview.net")
    
    # Fetch missing reviews
    logger.info(f"🔄 OpenReview APIから {len(missing_ids)} 件のレビューを取得中...")
    logger.info(f"   (レート制限: {60/rate_limit_delay:.0f} リクエスト/分)")
    
    start_time = time.time()
    new_reviews = {}
    
    for i, paper_id in enumerate(missing_ids, 1):
        # Progress logging
        if i % 10 == 0 or i == len(missing_ids):
            elapsed = time.time() - start_time
            rate = i / elapsed * 60 if elapsed > 0 else 0
            remaining = len(missing_ids) - i
            eta = remaining / (i / elapsed) if elapsed > 0 else 0
            logger.info(f"   進捗: {i}/{len(missing_ids)} ({i/len(missing_ids)*100:.0f}%) | ETA: {eta:.0f}秒")
        
        # Rate limiting
        if i > 1:
            time.sleep(rate_limit_delay)
        
        # Fetch review
        review_data = fetch_single_paper_reviews(client, paper_id)
        new_reviews[paper_id] = review_data
    
    # Update cache
    if new_reviews:
        cache.update(new_reviews)
        save_reviews_cache(cache, venue, year)
        logger.success(f"✓ {len(new_reviews)} 件の新しいレビューをキャッシュ（合計: {len(cache)}）")
    
    # Return results for requested papers
    result = {}
    for pid in paper_ids:
        if pid in cache:
            result[pid] = cache[pid]
        elif pid in new_reviews:
            result[pid] = new_reviews[pid]
    
    elapsed_total = time.time() - start_time
    logger.success(f"✓ レビュー取得完了 ({elapsed_total:.1f}秒)")
    
    return result


def merge_reviews_into_papers(
    papers: list[dict[str, Any]],
    reviews: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge review data into paper dictionaries.
    
    Args:
    ----
        papers: List of paper dictionaries
        reviews: Dictionary mapping paper_id to review data
        
    Returns:
    -------
        List of paper dictionaries with merged review data
    """
    for paper in papers:
        paper_id = paper.get("id")
        if paper_id and paper_id in reviews:
            review_data = reviews[paper_id]
            paper["reviews"] = review_data.get("reviews", [])
            paper["rating_avg"] = review_data.get("rating_avg")
            paper["confidence_avg"] = review_data.get("confidence_avg")
            paper["decision"] = review_data.get("decision", paper.get("decision", "N/A"))
            paper["meta_review"] = review_data.get("meta_review", "")
            paper["author_remarks"] = review_data.get("author_remarks", "")
            paper["decision_comment"] = review_data.get("decision_comment", "")
    
    return papers


def get_cache_stats(venue: str, year: int) -> dict[str, Any]:
    """Get statistics about the review cache.
    
    Args:
    ----
        venue: Conference name
        year: Conference year
        
    Returns:
    -------
        Dictionary with cache statistics
    """
    cache_path = get_cache_path(venue, year)
    
    if not cache_path.exists():
        return {
            "exists": False,
            "total_cached": 0,
            "file_size_mb": 0,
        }
    
    try:
        cache_data = json.loads(cache_path.read_text(encoding="utf-8"))
        return {
            "exists": True,
            "total_cached": cache_data.get("total_cached", 0),
            "updated_at": cache_data.get("updated_at"),
            "file_size_mb": cache_path.stat().st_size / 1024 / 1024,
        }
    except Exception as e:
        return {
            "exists": True,
            "error": str(e),
        }


if __name__ == "__main__":
    # Test execution
    import argparse
    
    parser = argparse.ArgumentParser(description="レビューキャッシュのテスト")
    parser.add_argument("--venue", type=str, default="NeurIPS")
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--paper-ids", type=str, nargs="+", default=[])
    
    args = parser.parse_args()
    
    if args.paper_ids:
        reviews = fetch_reviews_on_demand(args.paper_ids, args.venue, args.year)
        print(f"\n{len(reviews)} 件の論文のレビューを取得しました")
        for pid, data in reviews.items():
            print(f"  {pid}: {len(data.get('reviews', []))} 件のレビュー, rating={data.get('rating_avg')}")
    else:
        stats = get_cache_stats(args.venue, args.year)
        print(f"\n{args.venue} {args.year} のキャッシュ統計:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

