#!/bin/bash
# 論文レビューエージェント - クイックスタートスクリプト
#
# このスクリプトは、最も基本的な使用例を実行します。

echo "=========================================="
echo "論文レビューエージェント - クイックスタート"
echo "=========================================="
echo ""

# OpenAI APIキーが設定されているか確認
if [ -z "$OPENAI_API_KEY" ]; then
    # .env ファイルの存在を確認
    if [ ! -f ".env" ]; then
        echo "❌ エラー: OPENAI_API_KEY が設定されていません"
        echo ""
        echo "方法1: .env ファイルを作成（推奨）"
        echo "  cp .env.example .env"
        echo "  # .env ファイルを編集してAPIキーを設定"
        echo ""
        echo "方法2: 環境変数として設定"
        echo "  export OPENAI_API_KEY='your-api-key-here'"
        echo ""
        exit 1
    else
        echo "ℹ️  .env ファイルが見つかりました"
        echo "   Pythonスクリプトが自動的に読み込みます"
        echo ""
    fi
fi

# 論文データが存在するか確認
if [ ! -f "storage/papers_data/NeurIPS_2025/all_papers.json" ]; then
    echo "⚠️  警告: 論文データが見つかりません"
    echo "先に論文データを取得してください:"
    echo "  python fetch_all_papers.py"
    echo ""
    read -p "今すぐ取得しますか? (y/N): " response
    if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
        echo "論文データを取得中..."
        python fetch_all_papers.py
        if [ $? -ne 0 ]; then
            echo "❌ 論文データの取得に失敗しました"
            exit 1
        fi
    else
        echo "論文データを取得してから再度実行してください"
        exit 1
    fi
fi

echo "✅ 環境チェック完了"
echo ""
echo "📚 実行条件:"
echo "  - 学会: NeurIPS 2025"
echo "  - 研究興味: グラフ生成と創薬への応用"
echo "  - モデル: GPT-4o-mini"
echo "  - 評価対象: 上位100件"
echo ""
echo "実行を開始します..."
echo ""

# 公開版スクリプトを実行
python run_paper_review.py \
  --venue NeurIPS \
  --year 2025 \
  --research-description "私はグラフ生成と創薬への応用に興味があります。特に、分子グラフの生成やドラッグデザインに関連する研究を探しています。" \
  --top-k 100 \
  --model gpt-4o-mini

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ 処理が完了しました！"
    echo "=========================================="
    echo ""
    echo "📝 レポートは以下に保存されています:"
    echo "  storage/outputs/paper_review_report_NeurIPS_2025.md"
    echo ""
    echo "次のステップ:"
    echo "  1. レポートファイルを確認する"
    echo "  2. 他の研究興味で試す（./examples.sh 参照）"
    echo "  3. カスタムオプションを使用する（USAGE.md 参照）"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "❌ エラーが発生しました"
    echo "=========================================="
    echo ""
    echo "トラブルシューティング:"
    echo "  1. OpenAI APIキーが正しく設定されているか確認"
    echo "  2. 論文データが存在するか確認"
    echo "  3. --verbose オプションで詳細ログを確認"
    echo ""
    echo "詳細は USAGE.md を参照してください"
    echo ""
    exit 1
fi

