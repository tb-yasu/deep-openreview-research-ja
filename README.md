# Deep OpenReview Research (日本語版)

AIを活用した深い論文レビュー・分析エージェント

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

## 📋 概要

**Deep OpenReview Research** は、学会の採択論文を自動的に検索・評価し、ユーザーの研究興味に基づいて有益な論文をランク付けするAIエージェントです。OpenReview APIとLLMを組み合わせて、Meta Review、レビュー詳細、採択理由など、論文の深い情報を抽出し、効率的な論文調査を支援します。

## ✨ 主な機能

- 🔍 **自動論文検索**: 指定された学会・年の論文を自動検索
- 🤖 **統合LLM評価**: 1回の呼び出しで関連性・新規性・インパクト・実用性を総合評価
- 📊 **スコアリング**: OpenReviewの評価とAI評価を組み合わせた総合スコア
- 🔑 **同義語展開**: キーワードの同義語を自動生成して検索範囲を拡大
- 💬 **自然言語入力**: 研究興味を自然な文章で記述可能
- 📝 **詳細レポート**: Markdown形式の詳細レポートを自動生成
- 🎤 **発表形式表示**: Oral/Spotlight/Posterの区別を自動抽出
- 📋 **深いレビュー分析**: レビュー要約、スコア平均、採択理由、著者コメントを表示
- 🔄 **動的フィールド検出**: ICLR/NeurIPS/ICML等、各会議の評価項目に自動対応

## 🚀 クイックスタート

```bash
# 1. リポジトリをクローン
git clone https://github.com/tb-yasu/deep-openreview-research-ja.git
cd deep-openreview-research-ja

# 2. 仮想環境を作成してパッケージをインストール
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. OpenAI APIキーを設定（.envファイル）
cp .env.example .env
# .env ファイルを編集して実際のAPIキーを設定してください

# 4. 論文データを取得（初回のみ、60-90分）
python fetch_all_papers.py --venue NeurIPS --year 2025

# 5. 論文レビューを実行
python run_deep_research.py \
  --venue NeurIPS \
  --year 2025 \
  --research-description "グラフ生成と創薬への応用に興味があります"
```

## 📦 インストール

### 前提条件

- Python 3.12以上
- OpenAI APIキー
- インターネット接続（論文データ取得時のみ）

### 手順

#### 1. リポジトリのクローン

```bash
git clone https://github.com/tb-yasu/deep-openreview-research-ja.git
cd deep-openreview-research-ja
```

#### 2. 仮想環境の作成

```bash
python -m venv venv

# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

#### 3. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

主な依存パッケージ:
- `langchain` / `langgraph` - LLMアプリケーションフレームワーク
- `langchain-openai` - OpenAI統合
- `openreview-py` - OpenReview API クライアント
- `pydantic` - データ検証
- `loguru` - ログ出力

#### 4. 環境変数の設定

**推奨: .envファイルを使用**

```bash
# .env.example をコピーして .env ファイルを作成
cp .env.example .env

# .env ファイルを編集して実際のAPIキーを設定
# エディタで .env を開いて以下のように編集:
# OPENAI_API_KEY=sk-your-actual-api-key-here
```

`.env` ファイルは `.gitignore` に含まれているため、誤ってGitにコミットされることはありません。

**代替方法: 環境変数として直接設定**

一時的なテストなどでは、環境変数を直接設定することもできます：

```bash
# macOS/Linux
export OPENAI_API_KEY="your-api-key-here"

# Windows (コマンドプロンプト)
set OPENAI_API_KEY=your-api-key-here

# Windows (PowerShell)
$env:OPENAI_API_KEY="your-api-key-here"
```

**注意**: この方法では、ターミナルを閉じると設定が失われます。

#### 5. 論文データの取得

```bash
python fetch_all_papers.py --venue NeurIPS --year 2025
```

**注意**: 初回実行時は60-90分程度かかりますが、一度取得すればローカルキャッシュを使用します。

## 💻 基本的な使い方

### パターン1: 自然言語で研究興味を指定（推奨）

```bash
python run_deep_research.py \
  --venue NeurIPS \
  --year 2025 \
  --research-description "グラフ生成に強い興味があります。関連して創薬への応用に興味があります"
```

### パターン2: キーワードリストで指定

```bash
python run_deep_research.py \
  --venue NeurIPS \
  --year 2025 \
  --research-interests "graph generation,drug discovery,molecular design"
```

### パターン3: クイックスタートスクリプト

```bash
./quickstart.sh
```

## 🎛️ コマンドラインオプション

### 必須オプション

| オプション | 説明 | 例 |
|-----------|------|-----|
| `--venue` | 学会名 | `NeurIPS`, `ICML`, `ICLR` |
| `--year` | 開催年 | `2025` |
| `--research-description` または `--research-interests` | 研究興味 | 下記参照 |

### 評価基準のオプション

| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| `--min-relevance-score` | 0.2 | 最小関連性スコア（0.0-1.0） |
| `--top-k` | 100 | LLM評価対象とする論文の上位件数 |
| `--max-papers` | 9999 | 検索する最大論文数 |
| `--focus-on-novelty` | True | 新規性を重視 |
| `--focus-on-impact` | True | インパクトを重視 |

### LLM設定のオプション

| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| `--model` | gpt-4o-mini | 使用するLLMモデル |
| `--temperature` | 0.0 | LLM温度パラメータ（0.0-1.0） |
| `--max-tokens` | 1000 | LLM最大トークン数 |

### 出力設定のオプション

| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| `--output-dir` | storage/outputs | 出力ディレクトリ |
| `--output-file` | 自動生成 | 出力ファイル名 |
| `--top-n-display` | 10 | コンソールに表示する論文数 |

### その他のオプション

| オプション | 説明 |
|-----------|------|
| `--verbose`, `-v` | 詳細ログを表示 |
| `--no-llm-eval` | LLM評価をスキップ |
| `--help`, `-h` | ヘルプを表示 |

## 📚 使用例

### 例1: 基本的な使い方

```bash
python run_deep_research.py \
  --venue NeurIPS \
  --year 2025 \
  --research-description "大規模言語モデルの効率化に興味があります"
```

### 例2: 詳細設定を指定

```bash
python run_deep_research.py \
  --venue NeurIPS \
  --year 2025 \
  --research-description "強化学習とその応用に興味があります。" \
  --top-k 50 \
  --min-relevance-score 0.3 \
  --model gpt-4o
```

### 例3: キーワードベースのみ（高速）

```bash
python run_deep_research.py \
  --venue NeurIPS \
  --year 2025 \
  --research-interests "reinforcement learning,robotics" \
  --no-llm-eval \
  --top-n-display 20
```

### 例4: 詳細ログ付き実行

```bash
python run_deep_research.py \
  --venue NeurIPS \
  --year 2025 \
  --research-description "グラフニューラルネットワーク" \
  --verbose
```

### 例5: カスタム出力設定

```bash
python run_deep_research.py \
  --venue NeurIPS \
  --year 2025 \
  --research-description "transformer architecture" \
  --output-dir ./my_results \
  --output-file transformers_review.md
```

## 🏗️ アーキテクチャ

```
deep-openreview-research-ja/
├── fetch_all_papers.py      # 論文データ取得スクリプト
├── run_deep_research.py     # メイン実行スクリプト
├── quickstart.sh            # クイックスタートスクリプト
├── app/
│   ├── paper_review_workflow/  # 論文レビューワークフロー
│   │   ├── agent.py            # メインエージェント
│   │   ├── config.py           # 設定
│   │   ├── constants.py        # 定数
│   │   ├── models/             # データモデル
│   │   ├── nodes/              # ワークフローノード
│   │   │   ├── unified_llm_evaluate_papers_node.py  # 統合LLM評価
│   │   │   ├── generate_paper_report_node.py        # レポート生成
│   │   │   └── ...
│   │   ├── tools/              # ツール関数
│   │   └── utils/              # ユーティリティ
│   ├── core/                   # コア機能
│   ├── domain/                 # ドメイン層
│   └── infrastructure/         # インフラ層
└── storage/
    ├── cache/                  # キャッシュデータ
    ├── outputs/                # 出力レポート
    └── papers_data/            # 論文データ
```

## 🔄 ワークフロー

1. **キーワード収集**: 自然言語から研究キーワードを抽出（または直接指定）
2. **同義語生成**: 各キーワードの同義語をLLMで生成
3. **論文検索**: 指定された学会・年の論文を検索
4. **初期評価**: キーワードマッチングで関連性スコアを計算
5. **ランキング**: スコアに基づいて上位k件を選択
6. **統合LLM評価**: 1回の呼び出しで以下を総合評価
   - 関連性スコア（relevance）
   - 新規性スコア（novelty）
   - インパクトスコア（impact）
   - 実用性スコア（practicality）
   - レビュー要約（review_summary）
   - 評価データソース（field_insights）
   - AI評価理由（ai_rationale）
7. **再ランキング**: LLM評価スコアで最終ランク付け
8. **レポート生成**: 詳細レポートを生成（レビュースコア平均も含む）

## 📝 出力

実行完了後、以下のファイルが生成されます：

```
storage/outputs/paper_review_report_NeurIPS_2025.md
```

レポートには以下の情報が含まれます：
- 検索条件と評価基準
- キーワードと同義語のリスト
- 統計情報（平均スコア等）
- トップ論文の詳細情報
  - タイトル、著者、キーワード
  - 概要
  - スコア詳細（関連性、新規性、インパクト、実用性）
  - 採択判定と発表形式（Oral/Spotlight/Poster）
  - **🤖 AI評価** - 統合LLM評価による詳細な分析
  - **📊 レビュー要約** - 全レビューワーの評価を統合した要約
  - **🔍 評価データソース** - 使用したレビューフィールドの説明
  - **📝 採択理由（Decision Comment）** - Program Chairsによる採択判定コメント
  - **📊 レビュースコアの平均** - 各評価項目の平均値（会議により異なる）
  - **💬 著者からのコメント（Author Remarks）**
  - リンク（OpenReview、PDF）

## 🔧 トラブルシューティング

### ModuleNotFoundError が発生する

仮想環境が有効化されていることを確認してください：

```bash
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### OPENAI_API_KEY not found エラー

環境変数が正しく設定されているか確認してください：

```bash
echo $OPENAI_API_KEY  # macOS/Linux
echo %OPENAI_API_KEY%  # Windows
```

### 論文データが見つからない

まず論文データを取得してください：

```bash
python fetch_all_papers.py --venue NeurIPS --year 2025
```

### 論文データ取得が途中で止まる

進捗は自動保存されているため、再度実行すれば続きから再開します：

```bash
python fetch_all_papers.py --venue NeurIPS --year 2025
```

### メモリ不足エラー

`--top-k` の値を小さくしてください：

```bash
python run_deep_research.py ... --top-k 30
```

### AI評価やレビュー要約が表示されない

古いキャッシュを使用している場合、動的フィールド検出機能が含まれていない可能性があります。論文データを再取得してください：

```bash
python fetch_all_papers.py --venue NeurIPS --year 2025 --force
```

**注意**: 再取得には60-90分程度かかります。

### ICMLでレビュースコアが1つしか表示されない

これは正常な動作です。ICML 2025のレビューシステムは数値スコアが`overall_recommendation`のみで、他の評価項目（実験設計、手法など）はテキスト記述形式です。これらのテキスト評価は「📊 レビュー要約」セクションで統合LLMによって要約されています。

### 実行が遅い

以下のオプションで高速化できます：

```bash
# LLM評価をスキップ
python run_deep_research.py ... --no-llm-eval

# 評価対象論文数を減らす
python run_deep_research.py ... --top-k 50

# より高速なモデルを使用
python run_deep_research.py ... --model gpt-4o-mini
```

## 🛠️ 技術スタック

- **Python**: 3.12+
- **フレームワーク**: LangGraph, LangChain
- **LLMプロバイダー**: OpenAI
- **API**: OpenReview API
- **データ検証**: Pydantic
- **コード品質**: Ruff, MyPy

## 🤝 コントリビューション

コントリビューションを歓迎します！以下の手順でお願いします：

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add some amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📄 ライセンス

このプロジェクトは **CC BY-NC-SA 4.0（Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License）** の下で公開されています。

### ✅ 許可されること
- **学術・研究目的**での自由な使用
- ソースコードの共有・改変
- 個人的な学習・研究での利用

### ❌ 禁止されること
- **商用利用**（営利目的での使用）
- このソフトウェアを使った有料サービスの提供
- 商用製品への組み込み

### 📋 条件
- **表示** - 適切なクレジットを表示し、ライセンスへのリンクを提供
- **継承** - 改変版も同じライセンスで配布
- **非営利** - 営利目的での使用禁止

商用利用をご希望の場合は、別途ライセンス契約が必要です。詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 🙏 謝辞

このプロジェクトは以下の素晴らしいツールとサービスを使用しています：

- [OpenReview](https://openreview.net/) - 学術論文のピアレビュープラットフォーム
- [LangGraph](https://github.com/langchain-ai/langgraph) - LLMアプリケーションフレームワーク
- [LangChain](https://github.com/langchain-ai/langchain) - LLM統合フレームワーク
- [OpenAI](https://openai.com/) - LLM API

## 📞 サポート

問題が発生した場合や質問がある場合は、[GitHub Issues](https://github.com/tb-yasu/openreview-agent-ja/issues)でお問い合わせください。

---

**Happy Paper Reviewing! 📚✨**
