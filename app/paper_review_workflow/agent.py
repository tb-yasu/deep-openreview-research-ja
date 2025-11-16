"""Paper Review Agent implementation."""

from typing import Any

from langgraph.checkpoint.memory import InMemorySaver, MemorySaver
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from loguru import logger

from app.core.logging import LogLevel
from app.domain.base_agent import LangGraphAgent
from app.paper_review_workflow.models.state import (
    PaperReviewAgentState,
    PaperReviewAgentInputState,
    PaperReviewAgentOutputState,
)
from app.paper_review_workflow.nodes import (
    GatherResearchInterestsNode,
    SearchPapersNode,
    EvaluatePapersNode,  # 初期フィルタリング用に残す
    RankPapersNode,
    ReRankPapersNode,
    GeneratePaperReportNode,
)
from app.paper_review_workflow.nodes.unified_llm_evaluate_papers_node import (
    UnifiedLLMEvaluatePapersNode,
)
from app.paper_review_workflow.config import LLMConfig, ScoringWeights, DEFAULT_SCORING_WEIGHTS


class PaperReviewAgent(LangGraphAgent):
    """論文レビューエージェント.
    
    OpenReview APIを使用して学会の採択論文を検索・分析し、
    ユーザーの研究興味に基づいて有益な論文を抽出します。
    """
    
    def __init__(
        self,
        checkpointer: MemorySaver | None = None,
        log_level: LogLevel = LogLevel.INFO,
        recursion_limit: int = 100,
        llm_config: LLMConfig | None = None,
        scoring_weights: ScoringWeights | None = None,
    ) -> None:
        """PaperReviewAgentを初期化.
        
        Args:
        ----
            checkpointer: チェックポインタ（状態の永続化用）
            log_level: ログレベル
            recursion_limit: 再帰の最大回数
            llm_config: LLM評価の設定（省略時はデフォルト）
            scoring_weights: スコアリング重み設定（省略時はデフォルト）
        """
        weights = scoring_weights or DEFAULT_SCORING_WEIGHTS
        
        self.gather_interests_node = GatherResearchInterestsNode()
        self.search_papers_node = SearchPapersNode()
        self.evaluate_papers_node = EvaluatePapersNode(scoring_weights=weights)  # 初期フィルタリング
        self.rank_papers_node = RankPapersNode(llm_config=llm_config)
        # 統合LLM評価（1回の呼び出しで全スコア計算）
        self.unified_llm_evaluate_node = UnifiedLLMEvaluatePapersNode(
            llm_config=llm_config,
            scoring_weights=weights,
        )
        self.re_rank_papers_node = ReRankPapersNode()
        self.generate_report_node = GeneratePaperReportNode()
        
        super().__init__(
            log_level=log_level,
            checkpointer=checkpointer,
            recursion_limit=recursion_limit,
        )
    
    def _create_graph(self) -> CompiledStateGraph:
        """ワークフローグラフを作成.
        
        Returns:
        -------
            コンパイル済みのStateGraph
        """
        workflow = StateGraph(
            state_schema=PaperReviewAgentState,
            input_schema=PaperReviewAgentInputState,
            # output_schemaを削除して完全な状態を返す（将来的にはここで出力を整形）
        )
        
        # ノードを追加
        workflow.add_node("gather_interests", self.gather_interests_node)
        workflow.add_node("search_papers", self.search_papers_node)
        workflow.add_node("evaluate_papers", self.evaluate_papers_node)  # 初期フィルタリング
        workflow.add_node("rank_papers", self.rank_papers_node)
        # 統合LLM評価（1回で全スコア計算）
        workflow.add_node("unified_llm_evaluate", self.unified_llm_evaluate_node)
        workflow.add_node("re_rank_papers", self.re_rank_papers_node)
        workflow.add_node("generate_report", self.generate_report_node)
        
        # ワークフローのエッジを定義
        workflow.add_edge("gather_interests", "search_papers")
        workflow.add_edge("search_papers", "evaluate_papers")
        workflow.add_edge("evaluate_papers", "rank_papers")
        workflow.add_edge("rank_papers", "unified_llm_evaluate")  # 統合LLM評価
        workflow.add_edge("unified_llm_evaluate", "re_rank_papers")
        workflow.add_edge("re_rank_papers", "generate_report")
        
        # エントリーポイントと終了ポイントを設定
        workflow.set_entry_point("gather_interests")
        workflow.set_finish_point("generate_report")
        
        return workflow.compile(checkpointer=self.checkpointer)


def create_graph(
    llm_config: LLMConfig | None = None,
    scoring_weights: ScoringWeights | None = None,
) -> CompiledStateGraph:
    """PaperReviewAgentのグラフを作成.
    
    Args:
    ----
        llm_config: LLM評価の設定（省略時はデフォルト）
        scoring_weights: スコアリング重み設定（省略時はデフォルト）
    
    Returns:
    -------
        コンパイル済みのグラフ
    """
    checkpointer = InMemorySaver()
    agent = PaperReviewAgent(
        checkpointer=checkpointer,
        log_level=LogLevel.DEBUG,
        recursion_limit=100,
        llm_config=llm_config,
        scoring_weights=scoring_weights,
    )
    return agent.graph


def invoke_graph(
    graph: CompiledStateGraph,
    input_data: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """グラフを実行.
    
    Args:
    ----
        graph: 実行するグラフ
        input_data: 入力データ
        config: 実行設定
        
    Returns:
    -------
        実行結果
    """
    if config is None:
        config = {"recursion_limit": 100, "thread_id": "default"}
    
    logger.info("Starting PaperReviewAgent execution...")
    result = graph.invoke(
        input=input_data,
        config=config,
    )
    logger.info("PaperReviewAgent execution completed")
    
    return result

