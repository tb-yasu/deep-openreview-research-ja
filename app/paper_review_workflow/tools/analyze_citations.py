"""Tool for analyzing paper citations using Semantic Scholar API."""

import json
from typing import Any

import requests
from langchain_core.tools import tool
from loguru import logger


@tool
def analyze_citations(
    paper_title: str,
    doi: str | None = None,
    max_citations: int = 20,
    max_references: int = 20,
) -> str:
    """Semantic Scholar APIを使用して、論文の引用情報を分析します.

    Args:
    ----
        paper_title (str): 論文タイトル
        doi (str, optional): DOI（利用可能な場合）
        max_citations (int): 取得する引用元論文の最大件数（デフォルト: 20）
        max_references (int): 取得する参考文献の最大件数（デフォルト: 20）

    Returns:
    -------
        str: 引用分析結果のJSON。以下の情報が含まれます：
            - paper_id: Semantic Scholar上の論文ID
            - title: 論文タイトル
            - citation_count: 被引用数
            - reference_count: 参考文献数
            - influential_citation_count: 影響力のある引用数
            - year: 出版年
            - citations: 引用元論文のリスト（最大max_citations件）
            - references: 参考文献のリスト（最大max_references件）
            - citation_velocity: 年間平均引用数

    """
    try:
        base_url = "https://api.semanticscholar.org/graph/v1"
        
        # 論文を検索
        logger.info(f"Analyzing citations for: {paper_title}")
        if doi:
            # DOIがある場合は直接取得
            search_url = f"{base_url}/paper/DOI:{doi}"
        else:
            # タイトルで検索
            search_url = f"{base_url}/paper/search"
            params = {"query": paper_title, "limit": 1}
            response = requests.get(search_url, params=params, timeout=30)
            response.raise_for_status()
            search_results = response.json()
            
            if not search_results.get("data"):
                return json.dumps(
                    {"error": "Paper not found in Semantic Scholar"},
                    ensure_ascii=False,
                )
            
            paper_id = search_results["data"][0]["paperId"]
            search_url = f"{base_url}/paper/{paper_id}"

        # 論文詳細を取得（引用情報を含む）
        params = {
            "fields": "paperId,title,year,citationCount,referenceCount,influentialCitationCount,citations,citations.title,citations.year,citations.authors,references,references.title,references.year,references.authors"
        }
        response = requests.get(search_url, params=params, timeout=30)
        response.raise_for_status()
        paper_data = response.json()

        # 引用元論文（この論文を引用している論文）
        citations: list[dict[str, Any]] = []
        for citation in paper_data.get("citations", [])[:max_citations]:
            citations.append({
                "title": citation.get("title", ""),
                "year": citation.get("year"),
                "authors": [
                    author.get("name", "")
                    for author in citation.get("authors", [])[:3]  # 最初の3人のみ
                ],
            })

        # 参考文献（この論文が引用している論文）
        references: list[dict[str, Any]] = []
        for reference in paper_data.get("references", [])[:max_references]:
            references.append({
                "title": reference.get("title", ""),
                "year": reference.get("year"),
                "authors": [
                    author.get("name", "")
                    for author in reference.get("authors", [])[:3]
                ],
            })

        # 分析結果を構築
        paper_year = paper_data.get("year", 2025)
        citation_count = paper_data.get("citationCount", 0)
        years_since_publication = max(1, 2025 - paper_year) if paper_year else 1
        
        analysis = {
            "paper_id": paper_data.get("paperId"),
            "title": paper_data.get("title"),
            "year": paper_year,
            "citation_count": citation_count,
            "reference_count": paper_data.get("referenceCount", 0),
            "influential_citation_count": paper_data.get("influentialCitationCount", 0),
            "citations": citations,
            "references": references,
            "citation_velocity": citation_count / years_since_publication,
        }

        logger.info(
            f"Analyzed citations for: {analysis['title']} "
            f"(Citations: {analysis['citation_count']}, References: {analysis['reference_count']})"
        )
        return json.dumps(analysis, ensure_ascii=False, indent=2)

    except requests.exceptions.RequestException as e:
        error_msg = f"Error accessing Semantic Scholar API: {e!s}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg}, ensure_ascii=False)
    except Exception as e:
        error_msg = f"Error analyzing citations: {e!s}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg}, ensure_ascii=False)

