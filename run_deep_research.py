"""論文レビューエージェント - 公開版実行プログラム.

このスクリプトは、指定された学会の論文を検索・評価し、
研究興味に関連する論文をランク付けして報告します。
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file
load_dotenv()

from app.paper_review_workflow.agent import create_graph, invoke_graph
from app.paper_review_workflow.models.state import (
    PaperReviewAgentInputState,
    EvaluationCriteria,
)
from app.paper_review_workflow.config import LLMConfig, LLMModel


def setup_logger(verbose: bool = False) -> None:
    """ロガーを設定."""
    logger.remove()
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<level>{message}</level>"
    )
    logger.add(
        sys.stderr,
        format=log_format,
        level="DEBUG" if verbose else "INFO",
    )


def parse_arguments() -> argparse.Namespace:
    """コマンドライン引数を解析."""
    parser = argparse.ArgumentParser(
        description="論文レビューエージェント - 研究興味に基づいて論文を検索・評価します",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 自然言語で研究興味を指定
  python run_paper_review.py --venue NeurIPS --year 2025 \\
    --research-description "グラフ生成と創薬への応用に興味があります"

  # キーワードリストで指定
  python run_paper_review.py --venue NeurIPS --year 2025 \\
    --research-interests "graph generation,drug discovery,molecular design"

  # 詳細設定
  python run_paper_review.py --venue NeurIPS --year 2025 \\
    --research-description "量子コンピューティングとLLMへの応用" \\
    --top-k 50 --min-relevance-score 0.3 --model gpt-4o
        """,
    )
    
    # 必須引数
    parser.add_argument(
        "--venue",
        type=str,
        required=True,
        help="学会名（例: NeurIPS, ICML, ICLR）",
    )
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="開催年（例: 2025）",
    )
    
    # 研究興味の指定方法（どちらか一方を指定）
    research_group = parser.add_mutually_exclusive_group(required=True)
    research_group.add_argument(
        "--research-description",
        type=str,
        help="研究興味を自然言語で記述（推奨）",
    )
    research_group.add_argument(
        "--research-interests",
        type=str,
        help="研究興味のキーワードをカンマ区切りで指定（例: 'LLM,efficiency,fine-tuning'）",
    )
    
    # 評価基準
    parser.add_argument(
        "--min-relevance-score",
        type=float,
        default=0.2,
        help="最小関連性スコア（0.0-1.0、デフォルト: 0.2）",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=100,
        help="LLM評価対象とする論文の上位件数（デフォルト: 100）",
    )
    parser.add_argument(
        "--max-papers",
        type=int,
        default=9999,
        help="検索する最大論文数（デフォルト: 9999）",
    )
    parser.add_argument(
        "--focus-on-novelty",
        action="store_true",
        default=True,
        help="新規性を重視（デフォルト: True）",
    )
    parser.add_argument(
        "--focus-on-impact",
        action="store_true",
        default=True,
        help="インパクトを重視（デフォルト: True）",
    )
    
    # LLM設定
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        choices=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        help="使用するLLMモデル（デフォルト: gpt-4o-mini）",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="LLM温度パラメータ（0.0-1.0、デフォルト: 0.0）",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=1000,
        help="LLM最大トークン数（デフォルト: 1000）",
    )
    
    # 出力設定
    parser.add_argument(
        "--output-dir",
        type=str,
        default="storage/outputs",
        help="出力ディレクトリ（デフォルト: storage/outputs）",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="出力ファイル名（デフォルト: paper_review_report_{venue}_{year}.md）",
    )
    parser.add_argument(
        "--top-n-display",
        type=int,
        default=10,
        help="コンソールに表示する論文数（デフォルト: 10）",
    )
    
    # その他のオプション
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="詳細ログを表示",
    )
    parser.add_argument(
        "--no-llm-eval",
        action="store_true",
        help="LLM評価をスキップ（キーワードベースのみ）",
    )
    
    return parser.parse_args()


def get_llm_model(model_name: str) -> LLMModel:
    """モデル名からLLMModelを取得."""
    model_map = {
        "gpt-4o": LLMModel.GPT4O,
        "gpt-4o-mini": LLMModel.GPT4O_MINI,
        "gpt-4-turbo": LLMModel.GPT4_TURBO,
    }
    return model_map.get(model_name, LLMModel.GPT4O_MINI)


def run_paper_review(args: argparse.Namespace) -> None:
    """論文レビューを実行."""
    logger.info("=" * 100)
    logger.info("📚 論文レビューエージェント")
    logger.info("=" * 100)
    
    try:
        # LLM設定
        llm_config = LLMConfig(
            model=get_llm_model(args.model),
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
        
        # グラフを作成
        logger.info("🔧 ワークフローを初期化中...")
        graph = create_graph(llm_config=llm_config)
        
        # 研究興味を取得
        if args.research_description:
            research_description = args.research_description
            research_interests = []  # 自動抽出される
        else:
            research_description = None
            research_interests = [k.strip() for k in args.research_interests.split(",")]
        
        # 入力データを準備
        input_data = PaperReviewAgentInputState(
            venue=args.venue,
            year=args.year,
            keywords=None,  # 同義語マッチングを活用
            max_papers=args.max_papers,
            evaluation_criteria=EvaluationCriteria(
                research_description=research_description,
                research_interests=research_interests,
                min_relevance_score=args.min_relevance_score,
                min_rating=None,  # 採択論文は品質が保証されている
                enable_preliminary_llm_filter=False,
                top_k_papers=args.top_k if not args.no_llm_eval else None,
                focus_on_novelty=args.focus_on_novelty,
                focus_on_impact=args.focus_on_impact,
            ),
        )
        
        # 実行条件を表示
        logger.info(f"\n📋 実行条件:")
        logger.info(f"   学会: {args.venue} {args.year}")
        if research_description:
            logger.info(f"   研究興味: {research_description}")
        else:
            logger.info(f"   キーワード: {', '.join(research_interests)}")
        logger.info(f"   LLMモデル: {args.model}")
        logger.info(f"   最小関連性スコア: {args.min_relevance_score}")
        logger.info(f"   最大論文数: {args.max_papers}")
        if not args.no_llm_eval:
            logger.info(f"   LLM評価対象: 上位{args.top_k}件")
        else:
            logger.info(f"   LLM評価: スキップ")
        
        # エージェントを実行
        logger.info("\n🚀 エージェント実行中...")
        result = invoke_graph(
            graph=graph,
            input_data=input_data.model_dump(),
            config={
                "recursion_limit": 100,
                "thread_id": f"{args.venue}_{args.year}",
            },
        )
        
        # 結果を取得
        papers = result.get("papers", [])
        evaluated_papers = result.get("evaluated_papers", [])
        ranked_papers = result.get("ranked_papers", [])
        llm_evaluated_papers = result.get("llm_evaluated_papers", [])
        re_ranked_papers = result.get("re_ranked_papers", [])
        top_papers = result.get("top_papers", [])
        paper_report = result.get("paper_report", "")
        synonyms = result.get("synonyms", {})
        
        # サマリー表示
        logger.info("\n" + "=" * 100)
        logger.info("📊 実行結果サマリー")
        logger.info("=" * 100)
        logger.success(f"✓ 検索: {len(papers)}件の論文を発見")
        logger.success(f"✓ 評価: {len(evaluated_papers)}件の論文を評価")
        logger.success(f"✓ ランキング: {len(ranked_papers)}件の論文をランク付け")
        if not args.no_llm_eval:
            logger.success(f"✓ LLM評価: {len(llm_evaluated_papers)}件の論文を評価")
            logger.success(f"✓ 再ランキング: {len(re_ranked_papers)}件の論文を再ランク付け")
        logger.success(f"✓ 選出: {len(top_papers)}件の論文を選出")
        
        # キーワードと同義語を表示
        if synonyms:
            logger.info("\n" + "=" * 100)
            logger.info("🔑 検索キーワードと同義語")
            logger.info("=" * 100)
            for keyword, syns in synonyms.items():
                syns_display = ", ".join(syns[:5])
                if len(syns) > 5:
                    syns_display += f" 他{len(syns) - 5}個"
                logger.info(f"📌 {keyword}")
                logger.info(f"   └ 同義語: {syns_display}")
        
        # トップN論文を表示
        if top_papers and args.top_n_display > 0:
            logger.info("\n" + "=" * 100)
            logger.info(f"🏆 トップ{args.top_n_display}論文")
            logger.info("=" * 100)
            
            for paper in top_papers[:args.top_n_display]:
                logger.info(f"\n{'=' * 80}")
                logger.info(f"【第{paper['rank']}位】 {paper['title']}")
                logger.info("")
                
                # 著者
                authors_list = paper['authors']
                authors_display = ', '.join(authors_list[:5])
                if len(authors_list) > 5:
                    authors_display += f" 他{len(authors_list) - 5}名"
                logger.info(f"**著者**: {authors_display}")
                
                # キーワード
                if paper.get('keywords'):
                    keywords_list = paper['keywords']
                    keywords_display = ', '.join(keywords_list[:8])
                    if len(keywords_list) > 8:
                        keywords_display += f" 他{len(keywords_list) - 8}個"
                    logger.info(f"**キーワード**: {keywords_display}")
                logger.info("")
                
                # 概要
                if paper.get('abstract'):
                    logger.info("#### 概要")
                    logger.info("")
                    abstract = paper['abstract']
                    if len(abstract) > 400:
                        abstract = abstract[:400] + "..."
                    logger.info(abstract)
                    logger.info("")
                
                # スコア
                logger.info("#### スコア")
                logger.info("")
                if paper.get('final_score') is not None:
                    logger.info(f"| **最終スコア**         | **{paper['final_score']:.3f}** |")
                if paper.get('overall_score') is not None:
                    logger.info(f"| OpenReview総合         | {paper['overall_score']:.3f} |")
                if paper.get('relevance_score') is not None:
                    logger.info(f"| 　├ 関連性             | {paper['relevance_score']:.3f} |")
                if paper.get('novelty_score') is not None:
                    logger.info(f"| 　├ 新規性             | {paper['novelty_score']:.3f} |")
                if paper.get('impact_score') is not None:
                    logger.info(f"| 　└ インパクト         | {paper['impact_score']:.3f} |")
                if paper.get('llm_relevance_score') is not None:
                    logger.info(f"| AI評価（関連性）       | {paper['llm_relevance_score']:.3f} |")
                if paper.get('llm_novelty_score') is not None:
                    logger.info(f"| AI評価（新規性）       | {paper['llm_novelty_score']:.3f} |")
                if paper.get('llm_practical_score') is not None:
                    logger.info(f"| AI評価（実用性）       | {paper['llm_practical_score']:.3f} |")
                if paper.get('rating_avg') is not None:
                    logger.info(f"| OpenReview評価         | {paper['rating_avg']:.2f}/10 |")
                logger.info("")
                
                # OpenReview評価
                if not args.no_llm_eval:
                    logger.info("#### OpenReview評価")
                    logger.info("")
                    rationale = paper.get('evaluation_rationale', '')
                    if rationale:
                        logger.info(rationale[:300] + ("..." if len(rationale) > 300 else ""))
                    else:
                        review_count = len(paper.get('reviews', []))
                        rating_info = f"平均{paper['rating_avg']:.2f}/10" if paper.get('rating_avg') else "評価なし"
                        decision = paper.get('decision', 'N/A')
                        logger.info(f"この論文は{review_count}件のレビューを受け、{rating_info}の評価を獲得しました。")
                        logger.info(f"採択判定は「{decision}」です。")
                        
                        # 発表形式を表示（NeurIPSなどの場合）
                        if decision and decision != 'N/A':
                            decision_lower = decision.lower()
                            if "oral" in decision_lower:
                                logger.info("  └ 🎤 発表形式: Oral Presentation（口頭発表）")
                            elif "spotlight" in decision_lower:
                                logger.info("  └ ✨ 発表形式: Spotlight Presentation")
                            elif "poster" in decision_lower:
                                logger.info("  └ 📊 発表形式: Poster Presentation")
                    logger.info("")
                    
                    # Meta Review（エリアチェアのまとめ）
                    if paper.get('meta_review') and paper['meta_review'].strip():
                        logger.info("#### 📋 Meta Review（エリアチェアのまとめ）")
                        logger.info("")
                        meta_review = paper['meta_review']
                        if len(meta_review) > 200:
                            meta_review = meta_review[:200] + "..."
                        logger.info(meta_review)
                        logger.info("")
                    
                    # レビューの要約（最初の1件のみ表示）
                    reviews = paper.get('reviews', [])
                    if reviews and len(reviews) > 0:
                        first_review = reviews[0]
                        if first_review.get('summary') or first_review.get('strengths'):
                            logger.info("#### 📊 レビューハイライト")
                            logger.info("")
                            if first_review.get('strengths'):
                                strengths = first_review['strengths']
                                logger.info("**強み:**")
                                logger.info(strengths[:150] + ("..." if len(strengths) > 150 else ""))
                    logger.info("")
                    
                    # AI評価
                    if paper.get('llm_rationale'):
                        logger.info("#### AI評価（内容分析）")
                        logger.info("")
                        llm_rationale = paper['llm_rationale']
                        if len(llm_rationale) > 250:
                            llm_rationale = llm_rationale[:250] + "..."
                        logger.info(llm_rationale)
                        logger.info("")
                
                # リンク
                logger.info("**🔗 リンク**:")
                logger.info(f"- OpenReview: {paper['forum_url']}")
                if paper.get('pdf_url'):
                    logger.info(f"- PDF: {paper['pdf_url']}")
        
        # レポートをファイルに保存
        if paper_report:
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            if args.output_file:
                output_file = output_dir / args.output_file
            else:
                output_file = output_dir / f"paper_review_report_{args.venue}_{args.year}.md"
            
            output_file.write_text(paper_report, encoding="utf-8")
            
            logger.info("\n" + "=" * 100)
            logger.success(f"📝 レポートを保存しました: {output_file}")
            logger.info(f"   ファイルサイズ: {len(paper_report) / 1024:.1f} KB")
            logger.info(f"   行数: {len(paper_report.splitlines())}行")
            logger.info("=" * 100)
        
        # エラーがあれば表示
        errors = result.get("error_messages", [])
        if errors:
            logger.warning(f"\n⚠️  {len(errors)}件のエラーが発生しました:")
            for i, error in enumerate(errors[:3], 1):
                logger.warning(f"  {i}. {error}")
            if len(errors) > 3:
                logger.warning(f"  ...他{len(errors) - 3}件")
        
        logger.info("\n✨ 処理が完了しました！")
    
    except KeyboardInterrupt:
        logger.warning("\n⚠️  ユーザーによって中断されました")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ エラーが発生しました: {e}")
        if args.verbose:
            import traceback
            logger.error(traceback.format_exc())
        sys.exit(1)


def main() -> None:
    """メイン実行関数."""
    args = parse_arguments()
    setup_logger(verbose=args.verbose)
    run_paper_review(args)


if __name__ == "__main__":
    main()

