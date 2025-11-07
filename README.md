# openreview-agent-ja

OpenReview論文を自動で発見・分析する日本語対応AIエージェント

## 📋 概要

Openreview-agent-jaは、学会の採択論文を自動的に検索・評価し、ユーザーの研究興味に基づいて有益な論文をランク付けするAIエージェントです。OpenReview APIとLLMを組み合わせて、効率的な論文調査を支援します。

## ✨ 主な機能

- 🔍 **自動論文検索**: 指定された学会・年の論文を自動検索
- 🤖 **AI評価**: LLMを使用した論文の関連性・新規性・実用性の評価
- 📊 **スコアリング**: OpenReviewの評価とAI評価を組み合わせた総合スコア
- 🔑 **同義語展開**: キーワードの同義語を自動生成して検索範囲を拡大
- 💬 **自然言語入力**: 研究興味を自然な文章で記述可能
- 📝 **詳細レポート**: Markdown形式の詳細レポートを自動生成

## 🚀 クイックスタート

### 1. インストール

```bash
# リポジトリをクローン
git clone https://github.com/yourusername/paper-review-agent.git
cd paper-review-agent

# 仮想環境を作成
python -m venv venv
source venv/bin/activate  # Windowsの場合: venv\Scripts\activate

# 依存パッケージをインストール
pip install -r requirements.txt
```

### 2. 環境変数の設定

```bash
# OpenAI APIキーを設定
export OPENAI_API_KEY="your-api-key-here"
```

### 3. 論文データの取得

最初に一度だけ、対象学会の論文データを取得します（60-90分程度）：

```bash
python fetch_all_papers.py --venue NeurIPS --year 2025
```

### 4. 論文レビューの実行

```bash
# 自然言語で研究興味を指定
python run_paper_review.py \
  --venue NeurIPS \
  --year 2025 \
  --research-description "グラフ生成と創薬への応用に興味があります"
```

または、クイックスタートスクリプトを使用：

```bash
./quickstart.sh
```

## 📖 詳細な使い方

詳細な使い方とオプションについては、[USAGE.md](USAGE.md)を参照してください。

### 基本的な使用例

```bash
# 例1: 自然言語で研究興味を指定
python run_paper_review.py \
  --venue NeurIPS \
  --year 2025 \
  --research-description "TensorNetworkに強い興味があります。その応用にも興味があります。"

# 例2: キーワードリストで指定
python run_paper_review.py \
  --venue NeurIPS \
  --year 2025 \
  --research-interests "LLM,efficiency,fine-tuning"

# 例3: 詳細設定
python run_paper_review.py \
  --venue NeurIPS \
  --year 2025 \
  --research-description "diffusion models for image generation" \
  --top-k 50 \
  --model gpt-4o \
  --min-relevance-score 0.3
```

## 🏗️ アーキテクチャ

```
paper-review-agent/
├── fetch_all_papers.py      # 論文データ取得スクリプト
├── run_paper_review.py      # メイン実行スクリプト
├── app/
│   ├── paper_review_workflow/  # 論文レビューワークフロー
│   │   ├── agent.py            # メインエージェント
│   │   ├── config.py           # 設定
│   │   ├── constants.py        # 定数
│   │   ├── models/             # データモデル
│   │   ├── nodes/              # ワークフローノード
│   │   └── tools/              # ツール関数
│   ├── core/                   # コア機能
│   ├── domain/                 # ドメイン層
│   └── infrastructure/         # インフラ層
└── storage/
    ├── cache/                  # キャッシュデータ
    ├── outputs/                # 出力レポート
    └── papers_data/            # 論文データ
```

## 🛠️ 技術スタック

- **Python**: 3.12+
- **フレームワーク**: LangGraph, LangChain
- **LLMプロバイダー**: OpenAI
- **API**: OpenReview API
- **データ検証**: Pydantic
- **コード品質**: Ruff, MyPy

## 📊 ワークフロー

1. **キーワード収集**: 自然言語から研究キーワードを抽出
2. **同義語生成**: 各キーワードの同義語をLLMで生成
3. **論文検索**: 指定された学会・年の論文を検索
4. **初期評価**: キーワードマッチングで関連性スコアを計算
5. **ランキング**: スコアに基づいて上位k件を選択
6. **LLM評価**: 上位論文をLLMで詳細評価
7. **再ランキング**: LLM評価を含めた最終スコアで再ランク付け
8. **レポート生成**: 詳細レポートを生成

## 📝 出力例

実行完了後、以下のような詳細レポートが生成されます：

```
storage/outputs/paper_review_report_NeurIPS_2025.md
```

レポートには以下の情報が含まれます：
- 検索条件と評価基準
- キーワードと同義語のリスト
- 統計情報
- トップ論文の詳細情報（タイトル、著者、概要、スコア、評価など）

## 🔧 カスタマイズ

### 評価基準の調整

```bash
# 関連性スコアの閾値を調整
--min-relevance-score 0.3

# LLM評価対象の論文数を調整
--top-k 50

# LLM評価をスキップ（キーワードベースのみ）
--no-llm-eval
```

### LLMモデルの変更

```bash
# GPT-4oを使用（より高精度）
--model gpt-4o

# GPT-4o-miniを使用（デフォルト、コスト効率的）
--model gpt-4o-mini
```

### 出力のカスタマイズ

```bash
# 出力ディレクトリを指定
--output-dir ./my_results

# 出力ファイル名を指定
--output-file my_review.md

# コンソール表示数を調整
--top-n-display 20
```

## 📚 ドキュメント

- [USAGE.md](USAGE.md) - 詳細な使用ガイド
- [CODE_QUALITY_REPORT.md](CODE_QUALITY_REPORT.md) - コード品質レポート
- [examples.sh](examples.sh) - 使用例スクリプト集

## 🤝 コントリビューション

コントリビューションを歓迎します！以下の手順でお願いします：

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add some amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 🙏 謝辞

このプロジェクトは以下の素晴らしいツールとサービスを使用しています：

- [OpenReview](https://openreview.net/) - 学術論文のピアレビュープラットフォーム
- [LangGraph](https://github.com/langchain-ai/langgraph) - LLMアプリケーションフレームワーク
- [LangChain](https://github.com/langchain-ai/langchain) - LLM統合フレームワーク
- [OpenAI](https://openai.com/) - LLM API

## 📞 サポート

問題が発生した場合や質問がある場合は、以下の方法でお問い合わせください：

- **Issue**: [GitHub Issues](https://github.com/yourusername/paper-review-agent/issues)
- **Email**: your-email@example.com

## 🔄 更新履歴

### v1.0.0 (2025-11-07)
- 初回リリース
- 基本的な論文検索・評価機能
- LLM統合
- 同義語展開機能
- 詳細レポート生成

---

**Happy Paper Reviewing! 📚✨**

