"""Hybrid search engine combining vector search and keyword search.

This module provides hybrid search functionality using:
- Vector Search: ChromaDB with OpenAI Embeddings for semantic similarity
- Keyword Search: Traditional text matching on title/abstract
- RRF (Reciprocal Rank Fusion): Combines results from both search methods

Features:
- Semantic search finds conceptually similar papers even without exact keyword matches
- Keyword search ensures papers with specific terms are included
- RRF balances both methods for robust ranking
- Configurable weights for vector vs keyword search

Usage:
    from search_engine import hybrid_search
    
    results = hybrid_search(
        query_text="graph neural networks for drug discovery",
        keywords=["GNN", "molecular", "drug"],
        venue="NeurIPS",
        year=2025,
        top_k=100,
    )

Author: Paper Review Agent Team
License: MIT
"""

import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from loguru import logger

from indexer import VECTOR_DB_DIRECTORY, EMBEDDING_MODEL, get_collection_name, get_db_path

# Load environment variables
load_dotenv()

# Configuration
DEFAULT_RRF_K = 60  # Standard RRF constant
DEFAULT_TOP_K = 100


def reciprocal_rank_fusion(
    results_dict: dict[str, list[str]],
    k: int = DEFAULT_RRF_K,
    weights: dict[str, float] | None = None,
) -> list[tuple[str, float]]:
    """Combine multiple ranked lists using Reciprocal Rank Fusion (RRF).
    
    RRF Score = sum(weight * 1 / (k + rank)) for each search method
    
    This algorithm is robust because:
    1. It only uses rank positions, not raw scores (which may have different scales)
    2. Papers appearing in multiple lists get higher combined scores
    3. The k parameter prevents giving too much weight to top positions
    
    Args:
    ----
        results_dict: Dictionary mapping search method name to ranked list of paper IDs
                      e.g., {"vector": ["id1", "id2", ...], "keyword": ["id3", "id1", ...]}
        k: RRF constant (default: 60). Higher values reduce the impact of rank differences.
        weights: Optional weights for each search method
                 e.g., {"vector": 1.5, "keyword": 1.0} to prioritize vector search
                 
    Returns:
    -------
        List of (paper_id, rrf_score) tuples sorted by score descending
        
    Example:
    -------
        >>> results = {"vector": ["a", "b", "c"], "keyword": ["b", "a", "d"]}
        >>> rrf = reciprocal_rank_fusion(results)
        >>> # "a" and "b" appear in both lists, so they get higher scores
    """
    weights = weights or {algo: 1.0 for algo in results_dict}
    fused_scores: dict[str, float] = {}
    
    for algo, ranked_ids in results_dict.items():
        weight = weights.get(algo, 1.0)
        
        for rank, paper_id in enumerate(ranked_ids):
            if paper_id not in fused_scores:
                fused_scores[paper_id] = 0.0
            # Rank is 0-based, so add 1 for RRF formula
            fused_scores[paper_id] += weight * (1.0 / (k + rank + 1))
    
    # Sort by score descending
    sorted_results = sorted(
        fused_scores.items(),
        key=lambda x: x[1],
        reverse=True,
    )
    
    return sorted_results


def vector_search(
    query_text: str,
    venue: str,
    year: int,
    top_k: int = DEFAULT_TOP_K,
) -> list[tuple[str, float]]:
    """Search papers using semantic similarity via ChromaDB.
    
    Args:
    ----
        query_text: Natural language query describing research interest
        venue: Conference name (e.g., "NeurIPS")
        year: Conference year (e.g., 2025)
        top_k: Maximum number of results to return
        
    Returns:
    -------
        List of (paper_id, similarity_score) tuples sorted by similarity descending
        
    Raises:
    ------
        FileNotFoundError: If vector index doesn't exist for the venue/year
    """
    collection_name = get_collection_name(venue, year)
    db_path = Path(VECTOR_DB_DIRECTORY) / collection_name
    
    if not db_path.exists():
        raise FileNotFoundError(
            f"Vector index not found: {db_path}\n"
            f"Run 'python indexer.py --venue {venue} --year {year}' first."
        )
    
    logger.debug(f"🔍 Vector search: '{query_text[:50]}...' in {collection_name}")
    
    # Load vectorstore
    embedding_function = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    vectorstore = Chroma(
        persist_directory=str(db_path),
        embedding_function=embedding_function,
        collection_name=collection_name,
    )
    
    # Search with scores
    results = vectorstore.similarity_search_with_score(query_text, k=top_k)
    
    # Extract (id, score) pairs
    # Note: ChromaDB returns distance (lower is better), so we convert to similarity
    ranked_results = []
    for doc, distance in results:
        paper_id = doc.metadata.get("id")
        if paper_id:
            # Convert distance to similarity (1 - normalized_distance)
            similarity = 1.0 / (1.0 + distance)
            ranked_results.append((paper_id, similarity))
    
    logger.debug(f"  Found {len(ranked_results)} results")
    return ranked_results


def keyword_search(
    keywords: list[str],
    venue: str,
    year: int,
    top_k: int = DEFAULT_TOP_K,
    accepted_only: bool = True,
) -> list[tuple[str, float]]:
    """Search papers using keyword matching on title and abstract.
    
    Papers are ranked by the number of keyword matches, with keyword matches
    in the paper's keywords field weighted higher than matches in title/abstract.
    
    Args:
    ----
        keywords: List of search keywords (case-insensitive)
        venue: Conference name (e.g., "NeurIPS")
        year: Conference year (e.g., 2025)
        top_k: Maximum number of results to return
        accepted_only: If True, only search accepted papers
        
    Returns:
    -------
        List of (paper_id, match_score) tuples sorted by score descending
        
    Raises:
    ------
        FileNotFoundError: If papers JSON file doesn't exist
    """
    papers_file = Path(f"storage/papers_data/{venue}_{year}/all_papers.json")
    
    if not papers_file.exists():
        raise FileNotFoundError(
            f"Papers file not found: {papers_file}\n"
            f"Run 'python fetch_all_papers.py --venue {venue} --year {year}' first."
        )
    
    logger.debug(f"🔍 Keyword search: {keywords} in {venue}_{year}")
    
    # Load papers
    all_papers = json.loads(papers_file.read_text(encoding="utf-8"))
    
    # Normalize keywords for matching
    keywords_lower = [kw.lower().strip() for kw in keywords if kw]
    
    # Score each paper
    scored_papers: list[tuple[str, float]] = []
    
    for paper in all_papers:
        # Filter by acceptance status
        if accepted_only:
            decision = paper.get("decision", "").lower()
            if "accept" not in decision:
                continue
        
        paper_id = paper.get("id")
        if not paper_id:
            continue
        
        # Calculate match score
        title = paper.get("title", "").lower()
        abstract = paper.get("abstract", "").lower()
        paper_keywords = [kw.lower() for kw in paper.get("keywords", [])]
        
        # Combined text for searching
        text = f"{title} {abstract}"
        
        score = 0.0
        matched_keywords = 0
        
        for keyword in keywords_lower:
            # Check paper's keyword field (higher weight)
            if any(keyword in pk for pk in paper_keywords):
                score += 2.0  # Higher weight for keyword field match
                matched_keywords += 1
            # Check title/abstract
            elif keyword in text:
                score += 1.0
                matched_keywords += 1
        
        # Add coverage bonus (percentage of keywords matched)
        if keywords_lower:
            coverage = matched_keywords / len(keywords_lower)
            score += coverage * 0.5
        
        if score > 0:
            scored_papers.append((paper_id, score))
    
    # Sort by score descending
    scored_papers.sort(key=lambda x: x[1], reverse=True)
    
    # Return top k
    result = scored_papers[:top_k]
    logger.debug(f"  Found {len(result)} results (from {len(scored_papers)} matches)")
    
    return result


def hybrid_search(
    query_text: str,
    keywords: list[str],
    venue: str,
    year: int,
    top_k: int = DEFAULT_TOP_K,
    accepted_only: bool = True,
    vector_weight: float = 1.0,
    keyword_weight: float = 1.0,
    rrf_k: int = DEFAULT_RRF_K,
) -> list[dict[str, Any]]:
    """Perform hybrid search combining vector and keyword search with RRF.
    
    This function:
    1. Runs vector search on the query text (semantic similarity)
    2. Runs keyword search on the keywords list (lexical matching)
    3. Combines results using Reciprocal Rank Fusion (RRF)
    4. Returns paper metadata for top results
    
    Args:
    ----
        query_text: Natural language query for semantic search
        keywords: List of keywords for lexical search
        venue: Conference name (e.g., "NeurIPS")
        year: Conference year (e.g., 2025)
        top_k: Maximum number of results to return
        accepted_only: If True, only search accepted papers
        vector_weight: Weight for vector search in RRF (default: 1.0)
        keyword_weight: Weight for keyword search in RRF (default: 1.0)
        rrf_k: RRF constant (default: 60)
        
    Returns:
    -------
        List of paper dictionaries with full metadata, sorted by RRF score
        Each paper dict includes an additional "rrf_score" field
        
    Example:
    -------
        results = hybrid_search(
            query_text="neural network architectures for graph data",
            keywords=["GNN", "graph neural network", "message passing"],
            venue="NeurIPS",
            year=2025,
            top_k=50,
            vector_weight=1.5,  # Prioritize semantic search
        )
    """
    logger.info(f"🔍 Hybrid search in {venue} {year}")
    logger.info(f"  Query: '{query_text[:60]}...'")
    logger.info(f"  Keywords: {keywords[:5]}{'...' if len(keywords) > 5 else ''}")
    
    # 1. Vector Search (Semantic)
    try:
        vector_results = vector_search(query_text, venue, year, top_k=top_k * 2)
        vector_ids = [paper_id for paper_id, score in vector_results]
        logger.info(f"  📊 Vector search: {len(vector_ids)} results")
    except FileNotFoundError as e:
        logger.warning(f"  ⚠ Vector search unavailable: {e}")
        logger.warning("  ⚠ Falling back to keyword search only")
        vector_ids = []
    
    # 2. Keyword Search (Lexical)
    try:
        keyword_results = keyword_search(
            keywords, venue, year, 
            top_k=top_k * 2, 
            accepted_only=accepted_only,
        )
        keyword_ids = [paper_id for paper_id, score in keyword_results]
        logger.info(f"  📊 Keyword search: {len(keyword_ids)} results")
    except FileNotFoundError as e:
        logger.warning(f"  ⚠ Keyword search unavailable: {e}")
        keyword_ids = []
    
    # 3. RRF Fusion
    if not vector_ids and not keyword_ids:
        logger.warning("  ❌ No results from either search method")
        return []
    
    results_dict = {}
    weights = {}
    
    if vector_ids:
        results_dict["vector"] = vector_ids
        weights["vector"] = vector_weight
    
    if keyword_ids:
        results_dict["keyword"] = keyword_ids
        weights["keyword"] = keyword_weight
    
    fused_results = reciprocal_rank_fusion(results_dict, k=rrf_k, weights=weights)
    
    # Calculate statistics
    vector_only = set(vector_ids) - set(keyword_ids) if vector_ids else set()
    keyword_only = set(keyword_ids) - set(vector_ids) if keyword_ids else set()
    both = set(vector_ids) & set(keyword_ids) if vector_ids and keyword_ids else set()
    
    logger.info(f"  📊 RRF fusion: {len(fused_results)} unique papers")
    logger.info(f"     - Vector only: {len(vector_only)}")
    logger.info(f"     - Keyword only: {len(keyword_only)}")
    logger.info(f"     - Both: {len(both)}")
    
    # 4. Load paper metadata
    papers_file = Path(f"storage/papers_data/{venue}_{year}/all_papers.json")
    if not papers_file.exists():
        logger.error(f"  ❌ Papers file not found: {papers_file}")
        return []
    
    all_papers = json.loads(papers_file.read_text(encoding="utf-8"))
    papers_by_id = {p["id"]: p for p in all_papers if "id" in p}
    
    # Build result list with metadata
    result_papers = []
    for paper_id, rrf_score in fused_results[:top_k]:
        if paper_id in papers_by_id:
            paper = papers_by_id[paper_id].copy()
            paper["rrf_score"] = rrf_score
            paper["search_source"] = (
                "both" if paper_id in both
                else "vector" if paper_id in vector_only
                else "keyword"
            )
            result_papers.append(paper)
    
    logger.success(f"  ✅ Returning {len(result_papers)} papers")
    
    return result_papers


def search_papers_hybrid(
    query_text: str,
    keywords: list[str],
    venue: str,
    year: int,
    **kwargs,
) -> str:
    """Wrapper for hybrid_search that returns JSON string.
    
    This function provides compatibility with the existing search_papers interface.
    
    Args:
    ----
        query_text: Natural language query
        keywords: List of keywords
        venue: Conference name
        year: Conference year
        **kwargs: Additional arguments passed to hybrid_search
        
    Returns:
    -------
        JSON string of paper results
    """
    results = hybrid_search(query_text, keywords, venue, year, **kwargs)
    return json.dumps(results, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # Test execution
    import argparse
    
    parser = argparse.ArgumentParser(description="Test hybrid search")
    parser.add_argument("--query", type=str, default="graph neural networks for molecular property prediction")
    parser.add_argument("--keywords", type=str, nargs="+", default=["GNN", "molecular", "graph"])
    parser.add_argument("--venue", type=str, default="NeurIPS")
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--top-k", type=int, default=10)
    
    args = parser.parse_args()
    
    results = hybrid_search(
        query_text=args.query,
        keywords=args.keywords,
        venue=args.venue,
        year=args.year,
        top_k=args.top_k,
    )
    
    print(f"\n{'='*60}")
    print(f"Top {len(results)} results:")
    print(f"{'='*60}")
    
    for i, paper in enumerate(results, 1):
        print(f"\n{i}. [{paper['search_source'].upper()}] {paper['title'][:70]}...")
        print(f"   RRF Score: {paper['rrf_score']:.4f}")
        print(f"   Decision: {paper.get('decision', 'N/A')}")

