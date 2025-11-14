# 国際会議論文の効率的な発見・分析のための Deep OpenReview Research を公開しました

## この記事でわかること

- 数千件の採択論文から研究に本当に関連する論文を見つける方法
- 従来のキーワード検索では難しかった「深い論文分析」の概要
- AIによる論文評価とレビュー情報活用の具体像

## 問題：膨大な論文の中で重要な研究を見逃している

AI分野の主要国際会議では、毎年膨大な数の論文が採択されています。

- **NeurIPS 2025**: 5,290件
- **ICLR 2025**: 3,704件
- **ICML 2025**: 3,260件

これらは世界中の研究者が何ヶ月もかけて取り組んできた成果ですが、**ほとんどの論文が読まれずに埋もれてしまう**のが現実です。

**従来のキーワード検索の限界：**

研究者Aは「graph generation（グラフ生成）」に興味がありますが、重要な論文が「latent space controlled molecular graph synthesis」というタイトルで投稿されている場合、単純なキーワード検索だけでは見つからないことがあります。

さらに、OpenReviewには各論文に対する Meta Review や Decision Comment などの価値ある情報が含まれていますが、通常の検索ではこれらを十分に活用できません。

この問題を解決するために、**Deep OpenReview Research**を開発しました。

## 解決策：Deep OpenReview Research

OpenReview上の採択論文を対象とした、AIを活用した論文発見・分析エージェントです。OpenReview APIとLLMを組み合わせ、研究興味に関連する論文を自動的に発見し、ランク付けしたうえでレポートとして出力します。

### "Deep"が意味する3つの深さ

| 従来の検索 | Deep OpenReview Research |
|-----------|-------------------------|
| **キーワード完全一致** | **意味理解による検索**<br>LLMが同義語を自動生成（"graph generation"→"molecular graph synthesis"など数十の関連表現）し、表記揺れで見逃していた論文を発見 |
| **タイトルとAbstractのみ** | **レビュー情報の深い分析**<br>Meta Review・Decision Comment・レビュースコア・著者応答まで解析。なぜAcceptされたかを理解 |
| **関連性のみで評価** | **多軸評価**<br>関連性・新規性・インパクト・実用性の4軸で総合評価。研究目的に応じた優先順位付けが可能 |

## 主な機能

### 1. 自然言語で研究興味を指定

キーワードリストではなく、自然な文章で研究興味を記述できます。

```bash
python run_deep_research.py \
  --venue NeurIPS --year 2025 \
  --research-description "グラフ生成と創薬への応用に興味があります"
```

### 2. LLMによる4軸評価

1回のLLM呼び出しで、関連性・新規性・インパクト・実用性の4つの観点から論文を評価します。これにより、「面白いが実用性が低い論文」と「実装しやすいが新規性が低い論文」を区別しやすくなります。

### 3. OpenReviewのレビュー情報を完全活用

Meta Review、Decision Comment、レビュースコア、著者応答、発表形式（Oral/Spotlight/Poster）まで分析し、なぜその論文がAcceptされたかを理解できます。

### 4. 自動レポート生成

すべての分析結果をMarkdown形式のレポートとして出力。研究メモとして活用できます。

## 使用例

### ケース1: 分子グラフ生成の研究調査

```bash
python run_deep_research.py \
  --venue NeurIPS --year 2025 \
  --research-description "分子グラフ生成と創薬への応用に興味があります"
```

**結果：** 5,290件から関連上位100件を抽出しLLM評価。真に関連性の高い論文トップ50をランク付けしたレポートを生成。

### ケース2: LLM効率化技術の調査

```bash
python run_deep_research.py \
  --venue NeurIPS --year 2025 \
  --research-description "LLMの量子化や推論高速化技術"
```

**結果：** 実用性を重視した評価により、実装可能な技術論文を優先的に発見。

## 処理フロー

1. 自然言語から研究キーワードを抽出
2. LLMが同義語を自動生成
3. OpenReview APIで論文を検索
4. キーワードマッチングで初期フィルタリング
5. 上位k件（デフォルト100件）をLLMで多軸評価
6. 最終スコアでランク付けしレポート生成

## 出力レポートの例

```markdown
# 【第1位】MolGen: Controllable Molecular Graph Generation

**スコア**
- 最終スコア: 0.892
- 関連性: 0.950 | 新規性: 0.850 | インパクト: 0.825 | 実用性: 0.850
- レビュー平均: 8.2/10

**AI評価**
グラフ生成と創薬応用の両方において高い関連性。拡散モデルを用いた
制御可能な分子生成という新規性の高いアプローチを提案...

**採択理由（Decision Comment）**
Significant contribution to molecular design. Oral presentation.

**発表形式**: Oral Presentation（最上位クラスの論文）
```

## 技術スタック

Python 3.12+、LangGraph/LangChain、OpenAI GPT-4、OpenReview API

## 始め方

```bash
git clone https://github.com/tb-yasu/deep-openreview-research-ja.git
cd deep-openreview-research-ja
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# .envファイルにOpenAI APIキーを設定
cp .env.example .env

# 論文データを取得（初回のみ。環境にもよりますが目安として60〜90分程度）
python fetch_all_papers.py --venue NeurIPS --year 2025

# 実行
python run_deep_research.py \
  --venue NeurIPS --year 2025 \
  --research-description "あなたの研究興味"
```

詳細な設定オプションは[GitHubリポジトリ（日本語版）](https://github.com/tb-yasu/deep-openreview-research-ja)を参照してください。

英語版のリポジトリは[こちら](https://github.com/tb-yasu/deep-openreview-research)です。

## 他ツールとの違い

| 機能 | Google Scholar | Semantic Scholar | Deep OpenReview Research |
|------|---------------|------------------|-------------------------|
| 同義語自動生成 | × | × | ○ |
| レビュー情報解析 | × | × | ○ |
| 多軸評価 | × | △（簡易な指標のみ） | ○（関連性・新規性・インパクト・実用性） |
| 採択理由の分析 | × | × | ○ |
| カスタムレポート生成 | × | × | ○ |

Deep OpenReview ResearchはOpenReview APIを完全活用し、Meta ReviewやDecision Commentなど、採択プロセスの深い情報まで分析する点が最大の特徴です。

## 活用シーン

- **文献レビュー**: 論文執筆時の関連研究調査を効率化
- **技術調査**: 実装可能性を重視した論文の発見
- **研究動向把握**: 複数年・複数会議の横断調査
- **論文輪読選定**: Oral/Spotlightなど発表形式も参考に選定

## FAQ

**Q: 処理時間とコストは？**

A: 100件の論文をGPT-4o-miniで評価する場合、プロンプト設計にもよりますが、目安として約5〜10分、$0.05〜0.1程度で動作するように設計しています。

**Q: オフライン使用は可能？**

A: 論文データはローカルキャッシュされますが、LLM評価にはAPI接続が必要です。

**Q: 対応学会は？**

A: NeurIPS、ICML、ICLRなどOpenReviewを使用する学会に対応。

## まとめ

年間数千件の採択論文から、研究に本当に関連する論文を見つけることは困難です。Deep OpenReview Researchは、以下の3つのアプローチでこの問題を解決します。

1. **同義語自動生成による検索範囲の拡大** - キーワードの表記揺れによる見逃しを防止
2. **レビュー情報の深い分析** - Meta ReviewやDecision Commentからなぜ採択されたかを理解
3. **4軸評価による優先順位付け** - 関連性・新規性・インパクト・実用性で総合判断

従来のキーワード検索では数日かかっていた論文調査を、数分から数十分のオーダーまで短縮することを目指しています。

---

**リンク**

- GitHubリポジトリ（日本語版）: https://github.com/tb-yasu/deep-openreview-research-ja
- GitHubリポジトリ（英語版）: https://github.com/tb-yasu/deep-openreview-research
- ライセンス: MIT License
- 必要要件: Python 3.12+, OpenAI API Key

ご質問は各リポジトリのGitHub Issuesへ。

