# 論文レビューエージェント 使い方ガイド

## 概要

このエージェントは、指定された学会の論文を検索・評価し、研究興味に関連する論文をランク付けして報告します。

## 主な機能

- 🔍 **自動論文検索**: 指定された学会・年の論文を自動検索
- 🤖 **AI評価**: LLMを使用した論文の関連性・新規性・実用性の評価
- 📊 **スコアリング**: OpenReviewの評価とAI評価を組み合わせた総合スコア
- 🔑 **同義語展開**: キーワードの同義語を自動生成して検索範囲を拡大
- 💬 **自然言語入力**: 研究興味を自然な文章で記述可能
- 📝 **詳細レポート**: Markdown形式の詳細レポートを自動生成

## インストール

```bash
# リポジトリをクローン
git clone <repository-url>
cd openreview-agent-ja

# 仮想環境を作成
python -m venv venv
source venv/bin/activate  # Windowsの場合: venv\Scripts\activate

# 依存パッケージをインストール
pip install -r requirements.txt

# 環境変数を設定
export OPENAI_API_KEY="your-api-key-here"
```

## 基本的な使い方

### 1. 自然言語で研究興味を指定（推奨）

```bash
python run_paper_review.py \
  --venue NeurIPS \
  --year 2025 \
  --research-description "グラフ生成と創薬への応用に興味があります。"
```

### 2. キーワードリストで指定

```bash
python run_paper_review.py \
  --venue NeurIPS \
  --year 2025 \
  --research-interests "graph generation,drug discovery,molecular design"
```

## 詳細オプション

### 必須引数

| オプション | 説明 | 例 |
|-----------|------|-----|
| `--venue` | 学会名 | `NeurIPS`, `ICML`, `ICLR` |
| `--year` | 開催年 | `2025` |
| `--research-description` または `--research-interests` | 研究興味（どちらか必須） | 下記参照 |

### 研究興味の指定方法

**方法1: 自然言語（推奨）**

```bash
--research-description "私はgraph generationに強い興味があります。その創薬への応用に興味があります。"
```

**方法2: キーワードリスト**

```bash
--research-interests "LLM,its application, machine learning"
```

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
| `--model` | gpt-4o-mini | 使用するLLMモデル（gpt-4o, gpt-4o-mini, gpt-4-turbo） |
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
| `--no-llm-eval` | LLM評価をスキップ（キーワードベースのみ） |

## 使用例

### 例1: 基本的な使い方

```bash
python run_paper_review.py \
  --venue NeurIPS \
  --year 2025 \
  --research-description "私は大規模言語モデルの効率化に興味があります"
```

### 例2: 詳細設定を指定

```bash
python run_paper_review.py \
  --venue NeurIPS \
  --year 2025 \
  --research-description "グラフ生成と創薬への応用に興味があります。" \
  --top-k 50 \
  --min-relevance-score 0.3 \
  --model gpt-4o
```

### 例3: キーワードベースのみ（LLM評価なし）

```bash
python run_paper_review.py \
  --venue NeurIPS \
  --year 2025 \
  --research-interests "reinforcement learning,robotics" \
  --no-llm-eval \
  --top-n-display 20
```

### 例4: 詳細ログを表示

```bash
python run_paper_review.py \
  --venue NeurIPS \
  --year 2025 \
  --research-description "グラフニューラルネットワーク" \
  --verbose
```

### 例5: カスタム出力設定

```bash
python run_paper_review.py \
  --venue NeurIPS \
  --year 2025 \
  --research-description "transformer architecture" \
  --output-dir ./my_results \
  --output-file my_review_report.md
```

## 出力ファイル

実行が完了すると、以下のファイルが生成されます：

```
storage/outputs/
└── paper_review_report_NeurIPS_2025.md  # 詳細レポート
```

レポートには以下の情報が含まれます：

1. **検索条件**: 学会、年、キーワード
2. **キーワードと同義語**: 各キーワードの同義語リスト
3. **統計情報**: 平均スコア、最高・最低スコア
4. **トップ論文**: 各論文の詳細情報
   - タイトル、著者、キーワード
   - 概要
   - スコア詳細（関連性、新規性、インパクト、AI評価）
   - OpenReview評価とAI評価
   - リンク（OpenReview、PDF）

## ワークフロー

1. **キーワード収集**: 自然言語から研究キーワードを抽出（または直接指定）
2. **同義語生成**: 各キーワードの同義語をLLMで生成
3. **論文検索**: 指定された学会・年の論文を検索
4. **初期評価**: キーワードマッチングで関連性スコアを計算
5. **ランキング**: スコアに基づいて上位k件を選択
6. **LLM評価**: 上位論文をLLMで詳細評価（関連性、新規性、実用性）
7. **再ランキング**: LLM評価を含めた最終スコアで再ランク付け
8. **レポート生成**: 詳細レポートを生成

## トラブルシューティング

### OpenAI APIキーが設定されていない

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 論文データが見つからない

まず、論文データを取得する必要があります：

```bash
python fetch_all_papers.py
```

### メモリ不足エラー

`--top-k` の値を小さくしてください：

```bash
python run_paper_review.py ... --top-k 50
```

### 実行が遅い

以下のオプションで高速化できます：

- `--no-llm-eval`: LLM評価をスキップ
- `--top-k 50`: 評価対象論文数を減らす
- `--model gpt-4o-mini`: より高速なモデルを使用

## ヘルプの表示

```bash
python run_paper_review.py --help
```

## ライセンス

このプロジェクトのライセンスについては、LICENSEファイルを参照してください。

## サポート

問題が発生した場合は、Issueを作成してください。

