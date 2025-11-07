"""Fetch all papers from OpenReview with review data.

This script downloads all papers from a specified conference (e.g., NeurIPS 2025)
including their review data, ratings, and decisions. The data is cached locally
to avoid repeated API calls.

Features:
- Fetches complete paper metadata (title, authors, abstract, keywords)
- Retrieves review data (ratings, confidence scores, review text)
- Handles API rate limits automatically (60 requests/min)
- Supports resume from interruption
- Saves progress checkpoints every 100 papers
- Provides detailed progress tracking and ETA

Usage:
    # Fetch NeurIPS 2025 papers
    python fetch_all_papers.py --venue NeurIPS --year 2025
    
    # Force re-download even if cache exists
    python fetch_all_papers.py --venue NeurIPS --year 2025 --force
    
    # Fetch from a different conference
    python fetch_all_papers.py --venue ICML --year 2024

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


def fetch_paper_reviews(client: openreview.api.OpenReviewClient, paper_id: str) -> dict[str, Any]:
    """Fetch review information for a specific paper.
    
    Args:
    ----
        client: OpenReview API client
        paper_id: Unique paper identifier
        
    Returns:
    -------
        Dictionary containing review data:
            - reviews: List of review dictionaries
            - rating_avg: Average rating (float or None)
            - confidence_avg: Average confidence (float or None)
            - decision: Acceptance decision string
            
    Note:
    ----
        This function makes one API call per paper.
        Handles rate limiting externally.
    """
    try:
        # Fetch all notes associated with this paper
        all_notes = client.get_notes(forum=paper_id)
        
        # Extract official reviews (exclude rebuttals and meta-reviews)
        reviews = [
            note for note in all_notes
            if any('Official_Review' in inv for inv in getattr(note, 'invitations', []))
            and 'rating' in note.content  # Ensure it's an actual review
        ]
        
        ratings = []
        confidences = []
        review_list = []
        
        # Process each review
        for review in reviews:
            rating = review.content.get("rating", {})
            confidence = review.content.get("confidence", {})
            
            # Parse rating (format: "8: accept" -> 8.0)
            if isinstance(rating, dict) and "value" in rating:
                try:
                    rating_value = float(str(rating["value"]).split(":")[0].strip())
                    ratings.append(rating_value)
                except (ValueError, IndexError):
                    pass
            
            # Parse confidence (format: "4: confident" -> 4.0)
            if isinstance(confidence, dict) and "value" in confidence:
                try:
                    confidence_value = float(str(confidence["value"]).split(":")[0].strip())
                    confidences.append(confidence_value)
                except (ValueError, IndexError):
                    pass
            
            # Build review dictionary
            review_list.append({
                "rating": str(rating.get("value", "N/A")),
                "confidence": str(confidence.get("value", "N/A")),
                "summary": review.content.get("summary", {}).get("value", ""),
                "strengths": review.content.get("strengths", {}).get("value", ""),
                "weaknesses": review.content.get("weaknesses", {}).get("value", ""),
            })
        
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


def fetch_all_papers(venue: str, year: int, force: bool = False) -> None:
    """Fetch all papers from a conference with review data and save to disk.
    
    Args:
    ----
        venue: Conference name (e.g., "NeurIPS", "ICML", "ICLR")
        year: Conference year (e.g., 2025)
        force: If True, re-download even if cache exists
        
    Note:
    ----
        This function takes 60-90 minutes to complete due to API rate limits.
        However, it only needs to be run once. Progress is saved every 100 papers,
        so it can be safely interrupted and resumed.
    """
    # Setup output directory
    data_dir = Path(f"storage/papers_data/{venue}_{year}")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    papers_file = data_dir / "all_papers.json"
    metadata_file = data_dir / "metadata.json"
    
    # Check for existing cache
    if papers_file.exists() and not force:
        logger.info(f"Cache exists: {papers_file}")
        if metadata_file.exists():
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            logger.info(f"Cached: {metadata['total_papers']} papers from {metadata['fetch_date']}")
            logger.info(f"File size: {metadata['file_size_mb']:.2f} MB")
        logger.info("Use this cache by running the agent with any keywords")
        logger.info("To re-download, use --force flag")
        return
    
    # Display header
    logger.info("=" * 80)
    logger.info(f"Fetching all papers with review data from {venue} {year}")
    logger.info("This will take 60-90 minutes due to API rate limits (60 requests/min)")
    logger.info("But you only need to do this ONCE!")
    logger.info("=" * 80)
    
    # Initialize OpenReview client
    client = openreview.api.OpenReviewClient(baseurl="https://api2.openreview.net")
    venue_id = f"{venue}.cc/{year}/Conference"
    
    # Fetch all submissions with retry logic
    logger.info("Connecting to OpenReview API...")
    max_retries = 5
    retry_delay = 10  # seconds
    submissions = None
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching submissions (attempt {attempt + 1}/{max_retries})...")
            submissions = client.get_all_notes(
                invitation=f"{venue_id}/-/Submission",
                details="replies",
            )
            logger.success(f"Successfully fetched {len(submissions)} submissions")
            break
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error("Failed to fetch submissions after all retries")
                logger.error("")
                logger.error("Possible solutions:")
                logger.error("  1. Check your internet connection")
                logger.error("  2. Try again in a few minutes (OpenReview API may be overloaded)")
                logger.error("  3. Use existing cache if available (remove --force flag)")
                logger.error("")
                logger.error("If the problem persists, the OpenReview API may be experiencing issues.")
                logger.error("You can check the API status at: https://openreview.net")
                raise RuntimeError(f"Failed to fetch papers from OpenReview API after {max_retries} attempts") from e
    
    if submissions is None:
        raise RuntimeError("Failed to fetch submissions - this should not happen")
    
    papers: list[dict[str, Any]] = []
    processed_ids: set[str] = set()
    resume_from = 0
    
    # Check for checkpoint files (resume feature)
    temp_files = sorted(data_dir.glob("all_papers_temp_*.json"))
    if temp_files and not force:
        latest_temp_file = temp_files[-1]
        logger.info(f"Resume: Found checkpoint {latest_temp_file.name}")
        
        try:
            temp_data = json.loads(latest_temp_file.read_text(encoding="utf-8"))
            papers = temp_data
            processed_ids = {p["id"] for p in papers}
            resume_from = len(papers)
            
            logger.success(f"Resume: Loaded {resume_from} papers from checkpoint")
            logger.info(f"Resume: Starting from paper #{resume_from + 1}")
        except Exception as e:
            logger.warning(f"Resume: Failed to load checkpoint: {e}")
            logger.info("Resume: Starting from scratch")
            papers = []
            processed_ids = set()
            resume_from = 0
    elif force and temp_files:
        # Clean up temp files in force mode
        logger.info("Force mode: Cleaning up checkpoint files...")
        for temp_file in temp_files:
            temp_file.unlink()
            logger.debug(f"Cleaned up: {temp_file.name}")
    
    logger.info("Processing papers with review data...")
    logger.info("Progress will be saved every 100 papers to handle interruptions")
    if resume_from > 0:
        logger.info(f"Resuming from paper #{resume_from + 1}")
    
    start_time = time.time()
    request_count = 0
    
    for i, submission in enumerate(submissions, 1):
        # Skip already processed papers
        if submission.id in processed_ids:
            if i % 100 == 0:
                logger.debug(f"Skipping already processed papers up to #{i}")
            continue
        
        # Log progress with ETA
        if len(papers) % 100 == 0 and len(papers) > resume_from:
            elapsed = time.time() - start_time
            actual_processed = len(papers) - resume_from
            if actual_processed > 0:
                rate = actual_processed / elapsed * 60  # papers per minute
                remaining = len(submissions) - len(papers)
                eta_minutes = remaining / rate if rate > 0 else 0
                logger.info(
                    f"Progress: {len(papers)}/{len(submissions)} papers ({len(papers)/len(submissions)*100:.1f}%) | "
                    f"Rate: {rate:.1f}/min | ETA: {eta_minutes:.0f} min"
                )
        
        # Extract basic paper information
        title = submission.content.get("title", {})
        title_value = title.get("value", "") if isinstance(title, dict) else str(title)
        
        authors = submission.content.get("authors", {})
        authors_value = authors.get("value", []) if isinstance(authors, dict) else []
        
        abstract = submission.content.get("abstract", {})
        abstract_value = abstract.get("value", "") if isinstance(abstract, dict) else str(abstract)
        
        keywords_field = submission.content.get("keywords", {})
        keywords_value = keywords_field.get("value", []) if isinstance(keywords_field, dict) else []
        
        # Rate limiting: 60 requests/min = 1.2 sec/request
        # This ensures we stay under the API rate limit
        time.sleep(1.2)
        
        # Fetch review data
        review_data = fetch_paper_reviews(client, submission.id)
        request_count += 1
        
        # Build complete paper info
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
            # Review data
            "reviews": review_data["reviews"],
            "rating_avg": review_data["rating_avg"],
            "confidence_avg": review_data["confidence_avg"],
            "decision": review_data["decision"],
        }
        papers.append(paper_info)
        
        # Save checkpoint every 100 papers (interruption recovery)
        if len(papers) % 100 == 0:
            temp_file = data_dir / f"all_papers_temp_{len(papers)}.json"
            temp_file.write_text(
                json.dumps(papers, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            logger.info(f"Checkpoint: Saved {len(papers)} papers to {temp_file.name}")
    
    # Save final results
    logger.info("Saving final data to disk...")
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
        "average_rating": round(avg_rating, 2),
        "fetch_date": datetime.now().isoformat(),
        "file_size_mb": papers_file.stat().st_size / 1024 / 1024,
        "includes_review_data": True,
    }
    metadata_file.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    # Clean up checkpoint files
    for temp_file in data_dir.glob("all_papers_temp_*.json"):
        temp_file.unlink()
        logger.debug(f"Cleaned up: {temp_file.name}")
    
    # Display completion summary
    logger.success("=" * 80)
    logger.success(f"✓ Saved {len(papers)} papers to {papers_file}")
    logger.success(f"✓ Papers with reviews: {papers_with_reviews} ({papers_with_reviews/len(papers)*100:.1f}%)")
    logger.success(f"✓ Average rating: {avg_rating:.2f}/10")
    logger.success(f"✓ File size: {metadata['file_size_mb']:.2f} MB")
    logger.success(f"✓ Metadata: {metadata_file}")
    logger.success("=" * 80)
    logger.info("You can now run the agent with any keywords for instant filtering!")
    logger.info("All review data is cached locally - no more API rate limits!")


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Fetch all papers from a conference with review data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch NeurIPS 2025 papers
  python fetch_all_papers.py --venue NeurIPS --year 2025
  
  # Force re-download even if cache exists
  python fetch_all_papers.py --venue NeurIPS --year 2025 --force
  
  # Fetch from a different conference
  python fetch_all_papers.py --venue ICML --year 2024

Note:
  The first run will take 60-90 minutes, but subsequent runs use the cache.
  Progress is automatically saved every 100 papers.
        """
    )
    
    parser.add_argument(
        "--venue",
        type=str,
        default="NeurIPS",
        help="Conference name (default: NeurIPS)"
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2025,
        help="Conference year (default: 2025)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if cache exists"
    )
    
    args = parser.parse_args()
    
    try:
        fetch_all_papers(args.venue, args.year, args.force)
    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user. Progress has been saved.")
        logger.info("Run the script again to resume from the last checkpoint.")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        logger.info("Progress has been saved. Run the script again to resume.")
        raise


if __name__ == "__main__":
    main()
