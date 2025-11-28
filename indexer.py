"""Vector index builder for hybrid search.

This module provides functionality to build and update ChromaDB vector indices
from paper data. It uses OpenAI Embeddings (text-embedding-3-small) to vectorize
paper titles and abstracts for semantic search.

Features:
- Builds ChromaDB index from paper JSON data
- Supports incremental updates (add new papers to existing index)
- Provides clean rebuild option
- Can be called standalone or integrated with fetch_all_papers.py

Usage:
    # Build index from existing papers
    python indexer.py --venue NeurIPS --year 2025
    
    # Force rebuild (delete existing index first)
    python indexer.py --venue NeurIPS --year 2025 --rebuild
    
    # Integrate with fetch_all_papers.py (called automatically)

Author: Paper Review Agent Team
License: MIT
"""

import argparse
import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from loguru import logger

# Load environment variables
load_dotenv()

# Configuration
VECTOR_DB_DIRECTORY = "storage/vector_db"
EMBEDDING_MODEL = "text-embedding-3-small"


def get_collection_name(venue: str, year: int) -> str:
    """Generate collection name from venue and year.
    
    Args:
    ----
        venue: Conference name (e.g., "NeurIPS")
        year: Conference year (e.g., 2025)
        
    Returns:
    -------
        Collection name in lowercase (e.g., "neurips_2025")
    """
    return f"{venue.lower()}_{year}"


def get_db_path(venue: str, year: int) -> Path:
    """Get the path to the vector database for a given venue and year.
    
    Args:
    ----
        venue: Conference name (e.g., "NeurIPS")
        year: Conference year (e.g., 2025)
        
    Returns:
    -------
        Path to the vector database directory
    """
    collection_name = get_collection_name(venue, year)
    return Path(VECTOR_DB_DIRECTORY) / collection_name


def load_papers_from_json(venue: str, year: int) -> list[dict[str, Any]]:
    """Load papers from local JSON cache.
    
    Args:
    ----
        venue: Conference name
        year: Conference year
        
    Returns:
    -------
        List of paper dictionaries
        
    Raises:
    ------
        FileNotFoundError: If papers file doesn't exist
    """
    papers_file = Path(f"storage/papers_data/{venue}_{year}/all_papers.json")
    
    if not papers_file.exists():
        raise FileNotFoundError(
            f"Papers file not found: {papers_file}\n"
            f"Run 'python fetch_all_papers.py --venue {venue} --year {year}' first."
        )
    
    logger.info(f"📂 Loading papers from {papers_file}")
    papers = json.loads(papers_file.read_text(encoding="utf-8"))
    logger.success(f"✓ Loaded {len(papers)} papers")
    
    return papers


def build_vector_index(
    papers: list[dict[str, Any]],
    venue: str,
    year: int,
    rebuild: bool = False,
) -> Chroma:
    """Build or update ChromaDB vector index from paper data.
    
    This function vectorizes paper titles and abstracts using OpenAI Embeddings
    and stores them in a ChromaDB collection for semantic search.
    
    Args:
    ----
        papers: List of paper dictionaries with 'id', 'title', 'abstract' fields
        venue: Conference name (e.g., "NeurIPS")
        year: Conference year (e.g., 2025)
        rebuild: If True, delete existing index and rebuild from scratch
        
    Returns:
    -------
        Chroma vectorstore instance
        
    Note:
    ----
        Cost estimate: ~$0.03 for 5,000 papers (text-embedding-3-small)
        Time estimate: 2-5 minutes for 5,000 papers
    """
    collection_name = get_collection_name(venue, year)
    db_path = Path(VECTOR_DB_DIRECTORY) / collection_name
    
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"🚀 Building Vector Index: {collection_name}")
    logger.info("=" * 60)
    logger.info(f"  Papers: {len(papers)}")
    logger.info(f"  Model: {EMBEDDING_MODEL}")
    logger.info(f"  DB Path: {db_path}")
    logger.info("")
    
    # Handle rebuild option
    if rebuild and db_path.exists():
        logger.warning(f"🗑️  Deleting existing index at {db_path}")
        import shutil
        shutil.rmtree(db_path)
        logger.info("✓ Existing index deleted")
    
    # Initialize embedding function
    logger.info("🔌 Initializing OpenAI Embeddings...")
    embedding_function = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    
    # Check for existing index
    existing_ids: set[str] = set()
    if db_path.exists() and not rebuild:
        try:
            logger.info("📊 Checking existing index...")
            existing_store = Chroma(
                persist_directory=str(db_path),
                embedding_function=embedding_function,
                collection_name=collection_name,
            )
            # Get existing IDs
            existing_data = existing_store.get()
            if existing_data and existing_data.get("metadatas"):
                existing_ids = {m["id"] for m in existing_data["metadatas"] if "id" in m}
            logger.info(f"  Found {len(existing_ids)} papers already indexed")
        except Exception as e:
            logger.warning(f"⚠ Could not read existing index: {e}")
            existing_ids = set()
    
    # Filter papers that need indexing
    papers_to_index = [p for p in papers if p.get("id") not in existing_ids]
    
    if not papers_to_index:
        logger.success("✓ All papers already indexed. Nothing to do.")
        return Chroma(
            persist_directory=str(db_path),
            embedding_function=embedding_function,
            collection_name=collection_name,
        )
    
    logger.info(f"📝 Preparing {len(papers_to_index)} papers for indexing...")
    
    # Convert papers to LangChain Documents
    documents: list[Document] = []
    skipped = 0
    
    for paper in papers_to_index:
        paper_id = paper.get("id", "")
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")
        
        # Skip papers with missing essential data
        if not paper_id or not title:
            skipped += 1
            continue
        
        # Construct text for embedding
        # Title is included twice for emphasis
        text_to_embed = f"Title: {title}\n\nAbstract: {abstract or 'No abstract available.'}"
        
        # Build metadata for filtering and retrieval
        metadata = {
            "id": paper_id,
            "title": title,
            "venue": venue,
            "year": year,
            "keywords": ", ".join(paper.get("keywords", [])[:5]),  # First 5 keywords
            "rating_avg": paper.get("rating_avg"),
            "decision": paper.get("decision", "N/A"),
        }
        
        documents.append(Document(page_content=text_to_embed, metadata=metadata))
    
    if skipped > 0:
        logger.warning(f"⚠ Skipped {skipped} papers with missing ID or title")
    
    logger.info(f"📤 Indexing {len(documents)} documents to ChromaDB...")
    logger.info("  (This may take a few minutes for large datasets)")
    
    # Create or update vectorstore
    # Using batch processing for efficiency
    BATCH_SIZE = 500
    
    if existing_ids and db_path.exists():
        # Add to existing index
        vectorstore = Chroma(
            persist_directory=str(db_path),
            embedding_function=embedding_function,
            collection_name=collection_name,
        )
        
        for i in range(0, len(documents), BATCH_SIZE):
            batch = documents[i:i + BATCH_SIZE]
            vectorstore.add_documents(batch)
            logger.info(f"  Progress: {min(i + BATCH_SIZE, len(documents))}/{len(documents)} documents")
    else:
        # Create new index
        db_path.mkdir(parents=True, exist_ok=True)
        
        # Process in batches for large datasets
        if len(documents) > BATCH_SIZE:
            # Create with first batch
            vectorstore = Chroma.from_documents(
                documents=documents[:BATCH_SIZE],
                embedding=embedding_function,
                persist_directory=str(db_path),
                collection_name=collection_name,
            )
            logger.info(f"  Progress: {BATCH_SIZE}/{len(documents)} documents")
            
            # Add remaining batches
            for i in range(BATCH_SIZE, len(documents), BATCH_SIZE):
                batch = documents[i:i + BATCH_SIZE]
                vectorstore.add_documents(batch)
                logger.info(f"  Progress: {min(i + BATCH_SIZE, len(documents))}/{len(documents)} documents")
        else:
            vectorstore = Chroma.from_documents(
                documents=documents,
                embedding=embedding_function,
                persist_directory=str(db_path),
                collection_name=collection_name,
            )
    
    # Verify index
    total_count = vectorstore._collection.count()
    
    logger.success("")
    logger.success("=" * 60)
    logger.success("✅ Vector Index Built Successfully!")
    logger.success("=" * 60)
    logger.success(f"  Collection: {collection_name}")
    logger.success(f"  Total indexed: {total_count} papers")
    logger.success(f"  New additions: {len(documents)} papers")
    logger.success(f"  DB location: {db_path}")
    logger.success("")
    logger.info("💡 You can now use hybrid search with:")
    logger.info(f"   from search_engine import hybrid_search")
    logger.info("")
    
    return vectorstore


def main() -> None:
    """Main entry point for standalone execution."""
    parser = argparse.ArgumentParser(
        description="Build vector index for hybrid paper search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build index from existing papers
  python indexer.py --venue NeurIPS --year 2025
  
  # Force rebuild (delete existing index first)
  python indexer.py --venue NeurIPS --year 2025 --rebuild

Note:
  This requires papers to be fetched first using fetch_all_papers.py
  Cost: ~$0.03 for 5,000 papers using text-embedding-3-small
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
        "--rebuild",
        action="store_true",
        help="Delete existing index and rebuild from scratch"
    )
    
    args = parser.parse_args()
    
    try:
        # Load papers from JSON
        papers = load_papers_from_json(args.venue, args.year)
        
        # Build index
        build_vector_index(
            papers=papers,
            venue=args.venue,
            year=args.year,
            rebuild=args.rebuild,
        )
        
    except FileNotFoundError as e:
        logger.error(str(e))
        raise SystemExit(1)
    except Exception as e:
        logger.error(f"❌ Failed to build index: {e}")
        raise


if __name__ == "__main__":
    main()

