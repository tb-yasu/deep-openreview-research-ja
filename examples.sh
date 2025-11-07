#!/bin/bash
# 論文レビューエージェント - 使用例スクリプト
#
# このスクリプトには、よくある使用例が含まれています。
# 各例をコメント解除して実行してください。

# 例1: グラフ生成と創薬（デフォルト設定）
# =========================================
echo "例1: グラフ生成と創薬（デフォルト設定）"
python run_paper_review.py \
  --venue NeurIPS \
  --year 2025 \
  --research-description "私はグラフ生成と創薬への応用に興味があります"

# 例2: 量子コンピューティング（GPT-4o使用）
# =========================================
# echo "例2: 量子コンピューティング（GPT-4o使用）"
# python run_paper_review.py \
#   --venue NeurIPS \
#   --year 2025 \
#   --research-description "量子コンピューティングとLLMへの応用に興味があります" \
#   --model gpt-4o \
#   --top-k 50

# 例3: LLM効率化（キーワード指定）
# =========================================
# echo "例3: LLM効率化（キーワード指定）"
# python run_paper_review.py \
#   --venue NeurIPS \
#   --year 2025 \
#   --research-interests "LLM,efficiency,fine-tuning,inference,PEFT" \
#   --top-k 100 \
#   --min-relevance-score 0.25

# 例4: 強化学習（高速評価）
# =========================================
# echo "例4: 強化学習（高速評価）"
# python run_paper_review.py \
#   --venue NeurIPS \
#   --year 2025 \
#   --research-interests "reinforcement learning,robotics,control" \
#   --top-k 30 \
#   --model gpt-4o-mini

# 例5: キーワードベースのみ（LLM評価なし）
# =========================================
# echo "例5: キーワードベースのみ（LLM評価なし）"
# python run_paper_review.py \
#   --venue NeurIPS \
#   --year 2025 \
#   --research-interests "computer vision,object detection" \
#   --no-llm-eval \
#   --top-n-display 20

# 例6: 詳細ログ付き実行
# =========================================
# echo "例6: 詳細ログ付き実行"
# python run_paper_review.py \
#   --venue NeurIPS \
#   --year 2025 \
#   --research-description "グラフニューラルネットワークの新しいアーキテクチャ" \
#   --verbose

# 例7: カスタム出力設定
# =========================================
# echo "例7: カスタム出力設定"
# python run_paper_review.py \
#   --venue NeurIPS \
#   --year 2025 \
#   --research-description "transformer architecture innovations" \
#   --output-dir ./my_results \
#   --output-file transformers_review.md \
#   --top-n-display 15

# 例8: 高精度評価（関連性スコア高め）
# =========================================
# echo "例8: 高精度評価（関連性スコア高め）"
# python run_paper_review.py \
#   --venue NeurIPS \
#   --year 2025 \
#   --research-description "diffusion models for image generation" \
#   --min-relevance-score 0.4 \
#   --top-k 50 \
#   --model gpt-4o

