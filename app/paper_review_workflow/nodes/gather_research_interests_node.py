"""Node for gathering research interests interactively."""

import json
import re
from typing import Any

from langchain_openai import ChatOpenAI
from loguru import logger

from app.paper_review_workflow.models.state import PaperReviewAgentState


class GatherResearchInterestsNode:
    """対話的にユーザーの研究興味を収集するノード."""
    
    def __init__(self, min_keywords: int = 3):
        """GatherResearchInterestsNodeを初期化.
        
        Args:
        ----
            min_keywords: 最小キーワード数（デフォルト: 3）
        """
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0, max_tokens=500)
        self.min_keywords = min_keywords
    
    def __call__(self, state: PaperReviewAgentState) -> dict[str, Any]:
        """研究興味を対話的に収集.
        
        Args:
        ----
            state: 現在の状態
            
        Returns:
        -------
            更新された状態の辞書
        """
        criteria = state.evaluation_criteria
        
        # 初期キーワード抽出
        if criteria.research_description:
            logger.info("研究興味の説明からキーワードを抽出しています...")
            initial_keywords = self._extract_keywords(criteria.research_description)
        else:
            initial_keywords = criteria.research_interests or []
        
        logger.info(f"\n抽出されたキーワード ({len(initial_keywords)}個):")
        for i, kw in enumerate(initial_keywords, 1):
            logger.info(f"  {i}. {kw}")
        
        # キーワードが少ない場合、追加質問
        if len(initial_keywords) < self.min_keywords:
            logger.info(f"\nキーワードが{self.min_keywords}個未満のため、追加情報を収集します...\n")
            additional_keywords = self._ask_for_more_details(
                criteria.research_description or "",
                initial_keywords
            )
            
            # マージして重複削除
            all_keywords = list(set(initial_keywords + additional_keywords))
            
            logger.info(f"\n追加されたキーワード: {additional_keywords}")
        else:
            all_keywords = initial_keywords
        
        # 最終確認
        logger.info(f"\n{'='*80}")
        logger.info(f"📋 最終キーワードリスト ({len(all_keywords)}個):")
        for i, kw in enumerate(all_keywords, 1):
            logger.info(f"  {i}. {kw}")
        logger.info(f"{'='*80}\n")
        
        # 更新された基準を返す
        updated_criteria = criteria.model_copy(deep=True)
        updated_criteria.research_interests = all_keywords
        
        return {
            "evaluation_criteria": updated_criteria,
        }
    
    def _extract_keywords(self, description: str) -> list[str]:
        """自然言語の説明からキーワードを抽出.
        
        Args:
        ----
            description: 研究興味の自然言語説明
            
        Returns:
        -------
            抽出されたキーワードリスト
        """
        try:
            prompt = f"""Extract key research topics from the following description.
Return 5-8 important keywords or phrases that represent the main research interests.

Description:
{description}

Return ONLY a JSON array of keywords, like:
["keyword1", "keyword2", "keyword3", ...]

Rules:
- Use lowercase
- Be specific and technical
- Include 5-8 keywords
- Focus on the most important topics
"""
            
            response = self.llm.invoke(prompt)
            response_text = response.content.strip()
            
            # JSONパース
            keywords = self._parse_json_response(response_text)
            
            return keywords
            
        except Exception as e:
            logger.warning(f"Failed to extract keywords: {e}. Using empty list.")
            return []
    
    def _ask_for_more_details(
        self,
        initial_description: str,
        current_keywords: list[str]
    ) -> list[str]:
        """追加質問でキーワードを引き出す（サジェスション付き）.
        
        Args:
        ----
            initial_description: 初期の説明
            current_keywords: 現在のキーワードリスト
            
        Returns:
        -------
            追加されたキーワードリスト
        """
        try:
            # LLMに質問とサジェスションを生成させる
            question_prompt = f"""Based on this research description and current keywords, 
generate 2-3 specific follow-up questions in Japanese with keyword suggestions.

Initial description: {initial_description}
Current keywords: {current_keywords}

For each question, provide:
- The question in Japanese
- 3-5 example keywords (in English, lowercase) that would be relevant answers

Generate questions about:
- Specific methods or techniques they're interested in
- Application domains or use cases
- Related subfields or emerging topics

Return ONLY a JSON array of objects:
[
  {{
    "question": "質問1?",
    "suggestions": ["keyword1", "keyword2", "keyword3"]
  }},
  {{
    "question": "質問2?",
    "suggestions": ["keyword4", "keyword5"]
  }}
]
"""
            
            response = self.llm.invoke(question_prompt)
            questions_data = self._parse_json_response(response.content)
            
            # 質問を表示して回答を収集
            logger.info("\n追加の質問にお答えください:\n")
            answers = []
            
            for i, item in enumerate(questions_data, 1):
                if isinstance(item, dict):
                    question = item.get("question", "")
                    suggestions = item.get("suggestions", [])
                else:
                    # 互換性のため、文字列の場合も対応
                    question = str(item)
                    suggestions = []
                
                logger.info(f"{i}. {question}")
                
                # サジェスションを表示
                if suggestions:
                    suggestion_text = ", ".join(suggestions[:5])
                    logger.info(f"   [例: {suggestion_text}]")
                
                try:
                    answer = input("   回答: ")
                    if answer.strip():
                        answers.append(answer)
                    else:
                        logger.info("   （スキップされました）")
                except (EOFError, KeyboardInterrupt):
                    logger.info("\n（スキップされました）")
                    break
            
            # 回答から追加キーワードを抽出
            if answers:
                combined_answers = " ".join(answers)
                additional_prompt = f"""Extract additional research keywords from these answers:

{combined_answers}

Return 3-5 additional keywords as JSON array.
Avoid duplicating: {current_keywords}
Use lowercase and be specific.
"""
                
                response = self.llm.invoke(additional_prompt)
                additional_keywords = self._parse_json_response(response.content)
                
                return additional_keywords
            
            return []
            
        except Exception as e:
            logger.warning(f"Failed to ask for more details: {e}")
            return []
    
    def _parse_json_response(self, response_text: str) -> list:
        """LLMのレスポンスからJSON配列をパース.
        
        Args:
        ----
            response_text: LLMのレスポンステキスト
            
        Returns:
        -------
            パースされたリスト（文字列のリスト or オブジェクトのリスト）
        """
        try:
            # JSONブロックを抽出
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
            
            # JSONをパース
            result = json.loads(json_str)
            
            if isinstance(result, list):
                # リストの要素が辞書の場合はそのまま返す
                if result and isinstance(result[0], dict):
                    return result
                # 文字列の場合は小文字化して返す
                return [str(item).lower().strip() for item in result]
            
            return []
            
        except Exception as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response: {response_text[:200]}...")
            return []

