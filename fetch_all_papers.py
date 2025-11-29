"""Fetch all papers from OpenReview.

This script downloads all papers from a specified conference (e.g., NeurIPS 2025).
By default, it fetches only basic paper information (title, abstract, authors) for
fast initial setup. Review data can be fetched on-demand later or with --with-reviews.

Features:
- Fast mode (default): Fetches basic paper info only (5-10 minutes)
- Full mode (--with-reviews): Fetches review data too (60-90 minutes)
- Handles API rate limits automatically
- Supports resume from interruption
- Saves progress checkpoints

Usage:
    # Fast mode: Basic info only (recommended for first run)
    python fetch_all_papers.py --venue NeurIPS --year 2025
    
    # Full mode: Include all review data
    python fetch_all_papers.py --venue NeurIPS --year 2025 --with-reviews
    
    # Force re-download
    python fetch_all_papers.py --venue NeurIPS --year 2025 --force

Author: Paper Review Agent Team
License: MIT
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import openreview
from loguru import logger

# Load environment variables from .env file
load_dotenv()


def detect_all_review_fields(
    client: openreview.api.OpenReviewClient, 
    venue_id: str, 
    num_samples: int = 3
) -> set[str]:
    """Detect all available review fields from sample papers.
    
    This function inspects a few sample papers to discover what review fields
    are actually available in this conference. Different conferences use different
    field names (e.g., NeurIPS uses "strengths_and_weaknesses" while ICLR uses
    separate "strengths" and "weaknesses" fields).
    
    Args:
    ----
        client: OpenReview API client
        venue_id: Conference venue ID (e.g., "NeurIPS.cc/2025/Conference")
        num_samples: Number of sample papers to inspect (default: 3)
        
    Returns:
    -------
        Set of field names found in reviews (e.g., {"rating", "confidence", "summary", ...})
        
    Note:
    ----
        This function is called once at the start to discover the schema.
        It's a lightweight operation (only fetches 3 papers).
    """
    logger.info(f"🔍 {num_samples}件のサンプル論文からレビューフィールドを検出中...")
    
    all_fields = set()
    papers_checked = 0
    
    try:
        # Fetch a few sample submissions
        sample_papers = client.get_notes(
            invitation=f"{venue_id}/-/Submission",
            limit=num_samples * 3  # Get more than needed in case some have no reviews
        )
        
        for paper in sample_papers:
            if papers_checked >= num_samples:
                break
            
            try:
                # Fetch all notes for this paper
                all_notes = client.get_notes(forum=paper.id)
                
                # Find official reviews
                reviews = [
                    note for note in all_notes
                    if any('Official_Review' in inv for inv in getattr(note, 'invitations', []))
                ]
                
                if not reviews:
                    continue
                
                # Collect all field names from all reviews
                for review in reviews:
                    if hasattr(review, 'content') and review.content:
                        all_fields.update(review.content.keys())
                
                papers_checked += 1
                logger.debug(f"  ✓ サンプル {papers_checked}/{num_samples}: {len(all_fields)} フィールド検出")
                
            except Exception as e:
                logger.debug(f"  ⚠ サンプル論文 {paper.id} の処理に失敗: {e}")
                continue
        
        if not all_fields:
            logger.warning("⚠ サンプルからレビューフィールドを検出できませんでした。フォールバックフィールドを使用します。")
            # Fallback to minimal fields
            return {"rating", "confidence", "summary"}
        
        # Sort for consistent display
        sorted_fields = sorted(all_fields)
        logger.success(f"✓ {len(sorted_fields)} 個のレビューフィールドを検出:")
        
        # Display in a nice format (4 columns)
        for i in range(0, len(sorted_fields), 4):
            fields_row = sorted_fields[i:i+4]
            logger.info(f"  • {' | '.join(f'{f:25s}' for f in fields_row)}")
        
        return all_fields
        
    except Exception as e:
        logger.error(f"❌ フィールド検出に失敗: {e}")
        logger.warning("⚠ フォールバックフィールドを使用: rating, confidence, summary")
        # Fallback to minimal fields
        return {"rating", "confidence", "summary"}


def fetch_paper_reviews_dynamic(
    client: openreview.api.OpenReviewClient, 
    paper_id: str,
    detected_fields: set[str]
) -> dict[str, Any]:
    """Fetch review information for a specific paper with dynamic field extraction.
    
    This function extracts ALL fields that were detected during the initial field
    discovery phase. This makes it adaptable to any conference's review schema.
    
    Args:
    ----
        client: OpenReview API client
        paper_id: Unique paper identifier
        detected_fields: Set of field names to extract from reviews
        
    Returns:
    -------
        Dictionary containing review data:
            - reviews: List of review dictionaries with all detected fields
            - rating_avg: Average rating (float or None)
            - confidence_avg: Average confidence (float or None)
            - decision: Acceptance decision string
            - meta_review: Meta review text (Area Chair summary)
            - author_remarks: Author final remarks
            - decision_comment: Decision justification comment
            
    Note:
    ----
        This function makes one API call per paper.
        Handles rate limiting externally.
    """
    try:
        # Fetch all notes associated with this paper
        all_notes = client.get_notes(forum=paper_id)
        
        # Extract official reviews (exclude rebuttals, comments, and meta-reviews)
        # Different conferences use different fields for scores:
        # - NeurIPS/ICLR: 'rating'
        # - ICML: 'overall_recommendation'
        # Strategy: Accept if it has Official_Review invitation AND one of these conditions:
        #   1. Has 'rating' or 'overall_recommendation' field (most common score fields)
        #   2. Has 'summary' field AND has many other fields (real reviews are comprehensive)
        reviews = []
        for note in all_notes:
            invitations = getattr(note, 'invitations', [])
            if not any('Official_Review' in inv for inv in invitations):
                continue
            
            content = note.content if hasattr(note, 'content') else {}
            if not content:
                continue
            
            # Exclude obvious non-reviews
            if len(content) == 1 and ('comment' in content or 'rebuttal' in content):
                continue  # Just a comment or rebuttal, not a full review
            
            # Include if it has rating-like fields
            score_fields = {'rating', 'overall_recommendation', 'score', 'recommendation'}
            if any(field in content for field in score_fields):
                reviews.append(note)
            # Or if it's a comprehensive review (many fields including summary)
            elif 'summary' in content and len(content) >= 5:
                reviews.append(note)
        
        ratings = []
        confidences = []
        review_list = []
        
        # Process each review - extract ALL detected fields
        for review in reviews:
            review_data = {}
            
            # Extract every field that was detected
            for field_name in detected_fields:
                field_value = review.content.get(field_name, None)
                
                if field_value is not None:
                    # Handle different value formats
                    if isinstance(field_value, dict):
                        # OpenReview often wraps values in {"value": ...}
                        actual_value = field_value.get("value", "")
                    else:
                        actual_value = field_value
                    
                    # Store if not empty (but keep 0 values)
                    if actual_value or actual_value == 0:
                        review_data[field_name] = str(actual_value)
            
            review_list.append(review_data)
            
            # Parse rating for statistics
            # Different conferences use different fields:
            # - NeurIPS/ICLR: 'rating' (format: "8: accept" -> 8.0)
            # - ICML: 'overall_recommendation' (format: {"value": 3} -> 3.0)
            rating_value = None
            for rating_field in ['rating', 'overall_recommendation', 'score', 'recommendation']:
                rating = review.content.get(rating_field, {})
                if isinstance(rating, dict) and "value" in rating:
                    try:
                        # Handle both string ("8: accept") and numeric (3) formats
                        val = rating["value"]
                        if isinstance(val, (int, float)):
                            rating_value = float(val)
                        else:
                            rating_value = float(str(val).split(":")[0].strip())
                        ratings.append(rating_value)
                        break  # Found a rating, stop searching
                    except (ValueError, IndexError, TypeError):
                        pass
            
            # Parse confidence for statistics (format: "4: confident" -> 4.0)
            confidence = review.content.get("confidence", {})
            if isinstance(confidence, dict) and "value" in confidence:
                try:
                    val = confidence["value"]
                    if isinstance(val, (int, float)):
                        confidence_value = float(val)
                    else:
                        confidence_value = float(str(val).split(":")[0].strip())
                    confidences.append(confidence_value)
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
            
            # Extract decision comment/justification
            decision_note = decisions[0].content
            decision_comment = (
                decision_note.get("comment", {}).get("value", "") or
                decision_note.get("justification", {}).get("value", "") or
                decision_note.get("metareview", {}).get("value", "")
            )
        
        # Extract Meta Review (Area Chair summary)
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
            "reviews": review_list,
            "rating_avg": sum(ratings) / len(ratings) if ratings else None,
            "confidence_avg": sum(confidences) / len(confidences) if confidences else None,
            "decision": decision,
            "meta_review": meta_review_text,
            "author_remarks": author_remarks_text,
            "decision_comment": decision_comment,
        }
    except Exception as e:
        logger.debug(f"Failed to fetch reviews for {paper_id}: {e}")
        return {
            "reviews": [],
            "rating_avg": None,
            "confidence_avg": None,
            "decision": "N/A",
            "meta_review": "",
            "author_remarks": "",
            "decision_comment": "",
        }


def fetch_all_papers(venue: str, year: int, force: bool = False, with_reviews: bool = False) -> None:
    """Fetch all papers from a conference and save to disk.
    
    Args:
    ----
        venue: Conference name (e.g., "NeurIPS", "ICML", "ICLR")
        year: Conference year (e.g., 2025)
        force: If True, re-download even if cache exists
        with_reviews: If True, fetch full review data (slower, 60-90 min)
                      If False (default), fetch basic info only (fast, 5-10 min)
        
    Note:
    ----
        Fast mode (default): Takes 5-10 minutes, fetches basic paper info only.
        Full mode (--with-reviews): Takes 60-90 minutes, includes all review data.
        Progress is saved every 100 papers, so it can be safely interrupted.
    """
    # Setup output directory
    data_dir = Path(f"storage/papers_data/{venue}_{year}")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    papers_file = data_dir / "all_papers.json"
    metadata_file = data_dir / "metadata.json"
    
    # Check for existing cache
    if papers_file.exists() and not force:
        logger.info(f"キャッシュあり: {papers_file}")
        if metadata_file.exists():
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            logger.info(f"キャッシュ済み: {metadata['total_papers']} 件の論文 ({metadata['fetch_date']})")
            logger.info(f"ファイルサイズ: {metadata['file_size_mb']:.2f} MB")
            
            # Show what data is included
            includes_reviews = metadata.get("includes_review_data", False)
            if includes_reviews:
                logger.info("データ内容: 基本情報 + レビュー")
                if "detected_review_fields" in metadata:
                    num_fields = len(metadata["detected_review_fields"])
                    logger.info(f"レビューフィールド: {num_fields} 個検出")
            else:
                logger.info("データ内容: 基本情報のみ（レビューなし）")
                logger.info("💡 レビューを取得するには: python fetch_all_papers.py --with-reviews --force")
        
        logger.info("")
        logger.info("✓ エージェントを実行してこのキャッシュを使用できます")
        logger.info("✓ 再ダウンロードするには --force フラグを使用してください")
        return
    
    # Display header based on mode
    logger.info("=" * 80)
    if with_reviews:
        logger.info(f"{venue} {year} の全論文をレビューデータ付きで取得中")
        logger.info("APIレート制限（60リクエスト/分）のため、60-90分かかります")
    else:
        logger.info(f"{venue} {year} の全論文（基本情報）を取得中")
        logger.info("⚡ 高速モード: 5-10分で完了します！")
        logger.info("💡 レビューはエージェント実行時にオンデマンドで取得されます")
    logger.info("=" * 80)
    
    # Initialize OpenReview client
    client = openreview.api.OpenReviewClient(baseurl="https://api2.openreview.net")
    venue_id = f"{venue}.cc/{year}/Conference"
    
    # Step 1: Detect review fields (only if with_reviews)
    detected_fields = set()
    if with_reviews:
        logger.info("")
        logger.info("=" * 80)
        logger.info("STEP 1: レビューフィールドの検出")
        logger.info("=" * 80)
        detected_fields = detect_all_review_fields(client, venue_id, num_samples=3)
        logger.info("")
    
    # Fetch all submissions with retry logic
    logger.info("=" * 80)
    step_num = "STEP 2" if with_reviews else "STEP 1"
    logger.info(f"{step_num}: 論文サブミッションの取得")
    logger.info("=" * 80)
    logger.info("OpenReview APIに接続中...")
    max_retries = 5
    retry_delay = 10  # seconds
    submissions = None
    
    for attempt in range(max_retries):
        try:
            logger.info(f"サブミッション取得中 (試行 {attempt + 1}/{max_retries})...")
            submissions = client.get_all_notes(
                invitation=f"{venue_id}/-/Submission",
            )
            logger.success(f"{len(submissions)} 件のサブミッションを取得しました")
            break
        except Exception as e:
            logger.warning(f"試行 {attempt + 1} 失敗: {e}")
            if attempt < max_retries - 1:
                logger.info(f"{retry_delay} 秒後にリトライ...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error("全リトライ後も取得に失敗しました")
                logger.error("")
                logger.error("解決策:")
                logger.error("  1. インターネット接続を確認してください")
                logger.error("  2. 数分後に再試行してください（OpenReview APIが過負荷の可能性）")
                logger.error("  3. キャッシュがある場合は使用してください（--force フラグを外す）")
                logger.error("")
                logger.error("問題が続く場合、OpenReview APIに問題がある可能性があります。")
                logger.error("APIステータス確認: https://openreview.net")
                raise RuntimeError(f"OpenReview APIからの論文取得に失敗しました（{max_retries}回試行）") from e
    
    if submissions is None:
        raise RuntimeError("サブミッションの取得に失敗 - これは発生しないはずです")
    
    papers: list[dict[str, Any]] = []
    processed_ids: set[str] = set()
    resume_from = 0
    
    # Check for checkpoint files (resume feature) - only for with_reviews mode
    if with_reviews:
        temp_files = sorted(
            data_dir.glob("all_papers_temp_*.json"),
            key=lambda f: int(f.stem.split('_')[-1])
        )
        if temp_files and not force:
            latest_temp_file = temp_files[-1]
            logger.info(f"再開: チェックポイント {latest_temp_file.name} を検出")
            
            try:
                temp_data = json.loads(latest_temp_file.read_text(encoding="utf-8"))
                papers = temp_data
                processed_ids = {p["id"] for p in papers}
                resume_from = len(papers)
                
                logger.success(f"再開: {resume_from} 件の論文をチェックポイントからロード")
                logger.info(f"再開: 論文 #{resume_from + 1} から開始")
            except Exception as e:
                logger.warning(f"再開: チェックポイントのロードに失敗: {e}")
                logger.info("再開: 最初から開始します")
                papers = []
                processed_ids = set()
                resume_from = 0
        elif force and temp_files:
            # Clean up temp files in force mode
            logger.info("強制モード: チェックポイントファイルをクリーンアップ中...")
            for temp_file in temp_files:
                temp_file.unlink()
                logger.debug(f"クリーンアップ: {temp_file.name}")
    
    logger.info("")
    logger.info("=" * 80)
    step_num = "STEP 3" if with_reviews else "STEP 2"
    if with_reviews:
        logger.info(f"{step_num}: レビューデータ付き論文処理")
        logger.info("100件ごとに進捗を保存します")
    else:
        logger.info(f"{step_num}: 論文基本情報の処理")
    logger.info("=" * 80)
    
    if resume_from > 0:
        logger.info(f"論文 #{resume_from + 1} から再開")
    
    start_time = time.time()
    request_count = 0
    
    for i, submission in enumerate(submissions, 1):
        # Skip already processed papers (for resume)
        if submission.id in processed_ids:
            if i % 100 == 0:
                logger.debug(f"処理済み論文をスキップ（#{i}まで）")
            continue
        
        # Log progress
        if len(papers) % 500 == 0 and len(papers) > 0:
            elapsed = time.time() - start_time
            actual_processed = len(papers) - resume_from
            if actual_processed > 0:
                rate = actual_processed / elapsed * 60  # papers per minute
                remaining = len(submissions) - len(papers)
                eta_minutes = remaining / rate if rate > 0 else 0
                logger.info(
                    f"進捗: {len(papers)}/{len(submissions)} 件 ({len(papers)/len(submissions)*100:.1f}%) | "
                    f"速度: {rate:.1f}件/分 | ETA: {eta_minutes:.0f} 分"
                )
        
        # Extract basic paper information (always)
        title = submission.content.get("title", {})
        title_value = title.get("value", "") if isinstance(title, dict) else str(title)
        
        authors = submission.content.get("authors", {})
        authors_value = authors.get("value", []) if isinstance(authors, dict) else []
        
        abstract = submission.content.get("abstract", {})
        abstract_value = abstract.get("value", "") if isinstance(abstract, dict) else str(abstract)
        
        keywords_field = submission.content.get("keywords", {})
        keywords_value = keywords_field.get("value", []) if isinstance(keywords_field, dict) else []
        
        # Try to get decision from submission content (some conferences include it)
        decision_field = submission.content.get("venue", {})
        decision_from_venue = ""
        if isinstance(decision_field, dict):
            venue_value = decision_field.get("value", "")
            if venue_value:
                # Parse decision from venue field (e.g., "NeurIPS 2025 Accept (poster)")
                decision_from_venue = venue_value
        
        # Build paper info
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
        
        if with_reviews:
            # Full mode: Fetch review data for each paper
            # Rate limiting: 60 requests/min = 1.2 sec/request
            time.sleep(1.2)
            
            # Fetch review data with dynamic field extraction
            review_data = fetch_paper_reviews_dynamic(client, submission.id, detected_fields)
            request_count += 1
            
            # Add review data
            paper_info.update({
                "reviews": review_data["reviews"],
                "rating_avg": review_data["rating_avg"],
                "confidence_avg": review_data["confidence_avg"],
                "decision": review_data["decision"],
                "meta_review": review_data["meta_review"],
                "author_remarks": review_data["author_remarks"],
                "decision_comment": review_data["decision_comment"],
            })
        else:
            # Fast mode: Basic info only, use venue field for decision hint
            paper_info.update({
                "reviews": [],
                "rating_avg": None,
                "confidence_avg": None,
                "decision": decision_from_venue if decision_from_venue else "N/A",
                "meta_review": "",
                "author_remarks": "",
                "decision_comment": "",
            })
        
        papers.append(paper_info)
        
        # Save checkpoint every 100 papers (only in with_reviews mode)
        if with_reviews and len(papers) % 100 == 0:
            temp_file = data_dir / f"all_papers_temp_{len(papers)}.json"
            temp_file.write_text(
                json.dumps(papers, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            logger.info(f"チェックポイント: {len(papers)} 件の論文を {temp_file.name} に保存")
    
    # Save final results
    logger.info("最終データをディスクに保存中...")
    papers_file.write_text(
        json.dumps(papers, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    # Calculate statistics
    papers_with_reviews = sum(1 for p in papers if p.get("rating_avg") is not None)
    avg_rating = sum(p["rating_avg"] for p in papers if p.get("rating_avg") is not None) / papers_with_reviews if papers_with_reviews > 0 else 0
    
    # Save metadata
    metadata = {
        "venue": venue,
        "year": year,
        "total_papers": len(papers),
        "papers_with_reviews": papers_with_reviews,
        "average_rating": round(avg_rating, 2) if avg_rating else None,
        "fetch_date": datetime.now().isoformat(),
        "file_size_mb": papers_file.stat().st_size / 1024 / 1024,
        "includes_review_data": with_reviews,
        # Dynamic field detection results (only if with_reviews)
        "detected_review_fields": sorted(detected_fields) if detected_fields else [],
        "num_detected_fields": len(detected_fields),
    }
    metadata_file.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    # Clean up checkpoint files
    for temp_file in data_dir.glob("all_papers_temp_*.json"):
        temp_file.unlink()
        logger.debug(f"クリーンアップ: {temp_file.name}")
    
    # Display completion summary
    elapsed_total = time.time() - start_time
    logger.success("")
    logger.success("=" * 80)
    logger.success("✓ データ取得完了！")
    logger.success("=" * 80)
    logger.success(f"✓ {len(papers)} 件の論文を {papers_file} に保存")
    logger.success(f"✓ ファイルサイズ: {metadata['file_size_mb']:.2f} MB")
    logger.success(f"✓ 経過時間: {elapsed_total/60:.1f} 分")
    
    if with_reviews:
        logger.success(f"✓ レビューあり: {papers_with_reviews} 件 ({papers_with_reviews/len(papers)*100:.1f}%)")
        logger.success(f"✓ 平均レーティング: {avg_rating:.2f}/10")
        logger.success(f"✓ {len(detected_fields)} 個のレビューフィールドを検出")
        logger.success("=" * 80)
        logger.info("")
        logger.info("📊 検出されたレビューフィールド:")
        for i in range(0, len(sorted(detected_fields)), 4):
            fields_row = sorted(detected_fields)[i:i+4]
            logger.info(f"  • {' | '.join(f'{f:25s}' for f in fields_row)}")
    else:
        logger.success("✓ モード: 高速（基本情報のみ）")
        logger.success("=" * 80)
        logger.info("")
        logger.info("💡 レビューはエージェント実行時にオンデマンドで取得されます")
        logger.info("💡 すべてのレビューを事前取得するには:")
        logger.info(f"   python fetch_all_papers.py --venue {venue} --year {year} --with-reviews --force")
    
    logger.info("")
    logger.success("🎉 エージェントを実行できます！")


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="学会から全論文を取得",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 高速モード（推奨）: 基本情報のみ（5-10分）
  python fetch_all_papers.py --venue NeurIPS --year 2025
  
  # フルモード: 全レビューデータ付き（60-90分）
  python fetch_all_papers.py --venue NeurIPS --year 2025 --with-reviews
  
  # キャッシュがあっても強制再ダウンロード
  python fetch_all_papers.py --venue NeurIPS --year 2025 --force

注意:
  高速モード（デフォルト）は基本的な論文情報のみを取得します。
  レビューはエージェント実行時にオンデマンドで取得されます。
  全レビューデータを事前に取得する場合は --with-reviews を使用してください。
        """
    )
    
    parser.add_argument(
        "--venue",
        type=str,
        default="NeurIPS",
        help="学会名（デフォルト: NeurIPS）"
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2025,
        help="学会年（デフォルト: 2025）"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="キャッシュがあっても強制的に再ダウンロード"
    )
    parser.add_argument(
        "--with-reviews",
        action="store_true",
        help="全レビューデータを取得（遅い、60-90分）。デフォルト: 基本情報のみ（5-10分）"
    )
    
    args = parser.parse_args()
    
    try:
        fetch_all_papers(args.venue, args.year, args.force, args.with_reviews)
    except KeyboardInterrupt:
        logger.warning("\nユーザーによって中断されました。進捗は保存されています。")
        logger.info("スクリプトを再実行すると最後のチェックポイントから再開します。")
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        logger.info("進捗は保存されています。スクリプトを再実行して再開してください。")
        raise


if __name__ == "__main__":
    main()
