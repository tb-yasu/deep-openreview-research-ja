# 評価戦略まとめ：Deep OpenReview Research 論文化

**目標**: KDD 2025 Data Science Track への投稿  
**作成日**: 2025年1月  
**ステータス**: 評価計画確定

---

## 📊 Executive Summary

本システムの論文化にあたり、**2つの主要な技術的貢献を定量評価**する戦略を策定しました：

1. **Stage A（初期検索）**: 自然言語クエリ → LLM同義語展開 → 関連論文発見
2. **Stage B（最終ランキング）**: レビュー統合LLM評価 → 多角的ランキング

**実行可能なスコープ**:
- **最小構成**: NeurIPS 2025のみ、2名のアノテーター、30-40時間
- **推奨構成**: +ICML/ICLRサンプル評価、40-50時間
- **コスト**: $200-500（LLM API料金）+ 人件費

---

## 🎯 評価の2つの柱

### Stage A: 初期検索の性能評価

**評価目的**: キーワード抽出 + 同義語展開による関連論文発見の精度

```python
evaluation_focus = {
    "入力": "自然言語の研究興味記述",
    "処理": {
        "1. キーワード抽出": "LLMが5-8個のキーワードを抽出",
        "2. 同義語展開": "各キーワードに対し5-10個の同義語生成",
        "3. マッチング": "論文のkeywords/title/abstractと照合",
        "4. スコアリング": "関連性スコアの計算"
    },
    "出力": "関連度順の論文リスト（Top 100）",
    
    "評価メトリクス": {
        "Recall@K": "関連論文の網羅率（K=10,20,50,100）",
        "nDCG@K": "順位を考慮した検索品質",
        "MAP": "平均適合率",
        "MRR": "最初の関連論文の位置"
    }
}
```

**ベースライン比較**:
- A1: キーワードマッチのみ（同義語なし）
- A2: BM25（古典的IR）
- A3: Dense Retrieval（SPECTER/Sentence-BERT）
- **A4: Ours（LLM同義語展開 + マッチング）**

**期待される主張**: "LLMベースの同義語展開により、nDCG@50が+15%向上"

---

### Stage B: 最終ランキングの性能評価

**評価目的**: レビュー統合LLM評価による順位品質

```python
evaluation_focus = {
    "入力": "候補論文プール（固定100件）",
    "処理": {
        "統合LLM評価": {
            "入力コンテキスト": "title + abstract + reviews + meta-review + decision",
            "評価軸": [
                "関連性 (relevance)",
                "新規性 (novelty)", 
                "インパクト (impact)",
                "実用性 (practicality)"
            ],
            "重み付け統合": "0.4×rel + 0.25×nov + 0.25×imp + 0.1×prac"
        }
    },
    "出力": "最終ランキング（Top 20-50）",
    
    "評価メトリクス": {
        "nDCG@K": "人間評価との順位品質比較",
        "Kendall's tau": "順位相関係数",
        "Spearman's rho": "順位相関（もう1つの指標）",
        "Pairwise Accuracy": "ペアワイズ判定の正確性"
    }
}
```

**ベースライン比較**:
- B1: BM25スコアのみ
- B2: Cross-Encoder Re-ranker（強ベースライン）
- B3: LLMルーブリック（レビューデータなし）
- **B4: LLMルーブリック（レビューデータあり）← 我々の提案**

**期待される主張**: "レビューデータ統合により、nDCG@10が+10%向上"

---

## 👥 アノテーション戦略

### 基本構成: 2名の人間 + LLMハイブリッド

```python
annotation_strategy = {
    "人間アノテーター": {
        "人数": "2名（あなた + 1名の研究者）",
        "専門性": "機械学習分野のPhD学生/研究者",
        "役割": "ゴールドスタンダード作成"
    },
    
    "LLM-as-Judge": {
        "モデル": ["GPT-4o", "Claude Sonnet 4.5", "Gemini 2.0 Pro"],
        "役割": [
            "人間の不一致時のタイブレーカー",
            "妥当性検証後のスケールアップ"
        ]
    }
}
```

### プロトコル

#### Phase 1: パイロット評価（必須）

```markdown
**目的**: 人間とLLMの一致率確認

**データ**: 
- 10クエリ × 30論文 = 300件（Stage A用）
- 10クエリ × 20論文 = 200件（Stage B用、Top 20のみ）

**作業手順**:
1. 2名が独立に100件をラベル付け
2. 一致率（Cohen's kappa）を計算
   - 目標: κ > 0.60（substantial agreement）
3. 不一致ケース（20-30%）をLLMで判定
4. 多数決で最終ラベル確定
5. 残り400件を完了

**時間**: 各人15-20時間 = 合計30-40時間
```

#### Phase 2: LLM拡張（条件付き）

```markdown
**前提条件**: Phase 1でLLMと人間のκ > 0.65

**データ**: 
- 追加40クエリ × 100論文 = 4,000件

**方法**:
- 3モデルアンサンブル（多数決）
- 10%をランダムサンプリングして人間が再確認

**時間**: LLM自動実行（1-2日）+ 人間確認5時間
```

### アノテーションスケール

**Stage A（初期検索）**:
```python
relevance_scale = {
    "0": "無関係 - トピックが完全に異なる",
    "1": "部分的関連 - 周辺的な関連性あり",
    "2": "高関連 - 直接関連、必読レベル"
}
```

**Stage B（ランキング）**:
```python
ranking_scale = {
    "方法1": "1-5段階の詳細スコア（上位20件のみ）",
    "方法2": "ペアワイズ比較（効率的）",
    "方法3": "Top 20の順位付け"
}

# 推奨: 方法1（1-5スケール）
detailed_scale = {
    "5": "必読、研究に直接役立つ",
    "4": "高関連、読む価値が高い",
    "3": "関連あり、参考になる",
    "2": "やや関連、背景知識として",
    "1": "ほぼ無関係"
}
```

---

## 📚 データセット戦略

### メインデータセット: NeurIPS 2025（詳細評価）

```python
neurips_2025 = {
    "選定理由": [
        "最も新しい（2025年）",
        "規模が最大（5,290件の採択論文）",
        "レビューデータが最も充実",
        "Oral/Spotlight/Poster区別あり"
    ],
    
    "評価内容": {
        "Stage A": {
            "クエリ": 10,
            "論文/クエリ": 30,
            "合計ラベル": 300,
            "手法比較": "全4手法（Keyword, BM25, SPECTER, Ours）"
        },
        
        "Stage B": {
            "クエリ": 10,
            "論文/クエリ": 20,
            "合計ラベル": 200,
            "手法比較": "全4手法（BM25, Cross-Enc, LLM-no-review, LLM-with-review）"
        },
        
        "Ablation Study": [
            "同義語展開の有無",
            "レビューデータの有無",
            "各スコア次元の寄与",
            "モデル選択（gpt-4o-mini vs gpt-4o）"
        ]
    },
    
    "論文での扱い": "Section 6: Main Results（メイン実験）"
}
```

### サブデータセット: ICML/ICLR（サンプル検証）

```python
cross_venue_validation = {
    "目的": "汎化性能の確認（完全な統計検定は不要）",
    
    "ICML 2024": {
        "クエリ": 3（NeurIPSと同じドメイン）,
        "例": ["LLM efficiency", "RL robotics", "graph generation"],
        "論文/クエリ": 20,
        "合計": 60件,
        "評価": "BM25 vs Ours のみ（簡易比較）"
    },
    
    "ICLR 2024": {
        "クエリ": 3（異なるドメイン）,
        "例": ["multimodal learning", "adversarial robustness", "meta-learning"],
        "論文/クエリ": 20,
        "合計": 60件,
        "評価": "BM25 vs Ours のみ"
    },
    
    "論文での扱い": "Section 7: Cross-Venue Generalization（補足実験）"
}
```

### クエリセット設計

```python
query_design = {
    "多様性の確保": [
        "Graph ML（グラフ生成、GNN）",
        "NLP/LLM（効率化、評価）",
        "Computer Vision（Transformer、生成モデル）",
        "Reinforcement Learning（ロボティクス、シミュレーション）",
        "機械学習基盤（Federated Learning、AutoML）",
        "応用分野（創薬、時系列、セキュリティ）"
    ],
    
    "言語バランス": {
        "日本語": 3-4クエリ,
        "英語": 6-7クエリ,
        "目的": "多言語対応の評価"
    },
    
    "例": [
        "グラフニューラルネットワークによる分子グラフ生成と創薬への応用",
        "large language model efficiency through quantization and pruning",
        "reinforcement learning for robotic manipulation and sim-to-real transfer",
        "multimodal learning combining vision and language",
        # ... 計10クエリ
    ]
}
```

---

## 📊 評価メトリクスと統計検定

### Stage A メトリクス

```python
stage_a_metrics = {
    "主要メトリクス": {
        "Recall@K": "関連論文の網羅率（K=10,20,50,100）",
        "nDCG@K": "順位を考慮した品質（K=10,20,50）",
    },
    
    "補助メトリクス": {
        "MAP": "Mean Average Precision",
        "MRR": "Mean Reciprocal Rank"
    },
    
    "統計検定": {
        "方法": "Paired t-test + Wilcoxon signed-rank test",
        "対象": "10クエリでの各メトリクス値",
        "有意水準": "p < 0.05",
        "効果量": "Cohen's d"
    }
}
```

### Stage B メトリクス

```python
stage_b_metrics = {
    "主要メトリクス": {
        "nDCG@K": "人間評価との順位品質（K=10,20）",
        "Kendall's tau": "順位相関係数（ノンパラメトリック）",
    },
    
    "補助メトリクス": {
        "Spearman's rho": "順位相関（もう1つの指標）",
        "Pairwise Accuracy": "Top 20でのペアワイズ判定精度"
    },
    
    "効率性メトリクス": {
        "Latency": "1クエリあたりの処理時間",
        "API Cost": "1クエリあたりのコスト",
        "Throughput": "並列実行時の処理量"
    }
}
```

---

## 🚀 実装チェックリスト

### Phase 1: 基盤実装（Week 1-2）

- [ ] **クエリセット作成**
  - [ ] 10クエリの選定（多様性確保）
  - [ ] 日本語・英語のバランス確認
  - [ ] 各クエリの説明文作成

- [ ] **アノテーションツール準備**
  - [ ] Google Forms または専用UIの作成
  - [ ] アノテーションガイドライン作成
  - [ ] 練習セット（20件）の準備

- [ ] **ベースライン実装**
  - [ ] A1: Keywordマッチのみ
  - [ ] A2: BM25実装
  - [ ] A3: SPECTER/Sentence-BERT実装
  - [ ] B1: BM25ランキング
  - [ ] B2: Cross-Encoder Re-ranker

### Phase 2: データ収集（Week 3-4）

- [ ] **人間アノテーション（Stage A）**
  - [ ] 2名が各自100件をラベル
  - [ ] 一致率（Cohen's kappa）計算
  - [ ] 不一致ケースのLLM判定
  - [ ] 残り200件完了

- [ ] **人間アノテーション（Stage B）**
  - [ ] Top 20論文の詳細評価（1-5スケール）
  - [ ] 10クエリ × 20論文 = 200件

### Phase 3: LLM妥当性検証（Week 5）

- [ ] **LLM-as-Judge検証**
  - [ ] 3モデル（GPT-4o, Claude, Gemini）で300件評価
  - [ ] 人間ラベルとの一致率（κ）計算
  - [ ] κ > 0.65 なら次フェーズへ

- [ ] **LLM拡張**（条件付き）
  - [ ] 4,000件の追加ラベル生成
  - [ ] 10%スポットチェック

### Phase 4: 実験実行（Week 6-7）

- [ ] **メイン実験（NeurIPS 2025）**
  - [ ] Stage A: 4手法比較
  - [ ] Stage B: 4手法比較
  - [ ] Ablation Study実行
  - [ ] 統計的有意性検定

- [ ] **クロスベニュー検証**（オプション）
  - [ ] ICML: 3クエリ × 20論文
  - [ ] ICLR: 3クエリ × 20論文

### Phase 5: 結果分析・可視化（Week 8）

- [ ] **図表作成**
  - [ ] Table 1: Stage A メトリクス比較
  - [ ] Table 2: Stage B メトリクス比較
  - [ ] Figure 1: Recall/nDCG比較（棒グラフ）
  - [ ] Figure 2: コスト vs 品質（Paretoプロット）
  - [ ] Figure 3: Ablation Study結果

- [ ] **統計レポート生成**
  - [ ] p値、信頼区間、効果量
  - [ ] Per-query breakdown

---

## 💰 コスト見積もり

### 人件費

```python
human_cost = {
    "アノテーター2名": {
        "作業時間": "各15-20時間",
        "時給": "$50（研究者相当）",
        "合計": "$1,500-2,000"
    },
    
    "代替案": {
        "共著者として貢献を認める": "$0",
        "謝礼金": "$100-200/人"
    }
}
```

### API料金

```python
api_cost = {
    "LLM同義語展開": {
        "回数": "10キーワード × 10クエリ = 100回",
        "コスト": "$0.5-1/回",
        "合計": "$50-100"
    },
    
    "統合LLM評価": {
        "Stage A": "100論文（top-k）× 10クエリ = 1,000回",
        "Stage B": "100論文 × 10クエリ = 1,000回",
        "コスト/回": "$0.10-0.15",
        "合計": "$200-300"
    },
    
    "LLM-as-Judge": {
        "妥当性検証": "300件 × 3モデル = 900回",
        "拡張": "4,000件 × 1モデル = 4,000回",
        "コスト": "$200-300"
    },
    
    "総計": "$450-700"
}
```

### 合計

- **最小構成**: $200（APIのみ） + 謝礼$200 = **$400**
- **推奨構成**: $500（API） + 謝礼$400 = **$900**
- **完全構成**: $700（API） + 人件費$2,000 = **$2,700**

---

## 📝 論文構成案

### タイトル案

> **Deep OpenReview Research: LLM-Augmented Discovery and Ranking of Peer-Reviewed Papers with Review-Aware Evaluation**

### アブストラクト要旨

```
膨大な採択論文から関連研究を発見する困難さを解決するため、
LLM拡張型の論文発見・ランキングシステムを提案する。

【貢献1】自然言語クエリ→LLM同義語展開→関連論文発見
【貢献2】レビューデータ統合の多角的LLM評価による高品質ランキング
【貢献3】LLM-as-Judge検証済みの評価プロトコル

NeurIPS 2025での実験により、従来手法比+15% nDCG向上を実証。
```

### セクション構成

```markdown
1. Introduction
   - 問題: キーワードミスマッチ、レビューデータの未活用
   - 貢献: 3つの技術的貢献

2. Related Work
   - 学術文献検索システム
   - LLMベースのIR
   - ピアレビュー活用研究

3. System Overview
   - 7ステップワークフロー
   - アーキテクチャ

4. Method
   4.1 Interest Parsing and Synonym Expansion
   4.2 Retrieval from OpenReview
   4.3 Initial Scoring
   4.4 Unified LLM Evaluation
   4.5 Review-Aware Features
   4.6 Final Ranking

5. Evaluation Setup
   5.1 Datasets (NeurIPS 2025 main, ICML/ICLR validation)
   5.2 Query Set (10 diverse topics)
   5.3 Ground Truth Annotations (2 humans + LLM-as-Judge)
   5.4 Baselines
   5.5 Metrics

6. Main Results (NeurIPS 2025)
   6.1 Stage A: Retrieval Performance
       - Table 1: Recall@K, nDCG@K comparison
       - Key finding: +15% nDCG@50 with synonym expansion
   
   6.2 Stage B: Ranking Performance
       - Table 2: nDCG@K, Kendall's tau comparison
       - Key finding: +10% nDCG@10 with review-aware features
   
   6.3 Ablation Study
       - Figure: Contribution of each component

7. Cross-Venue Generalization (ICML/ICLR)
   - Table 3: Consistent improvements across venues
   - Discussion: Generalization despite format differences

8. Analysis
   8.1 Cost-Quality Trade-offs
   8.2 Qualitative Examples
   8.3 Failure Cases

9. Related Work (Extended)

10. Conclusion & Future Work
```

---

## 🎯 成功基準

### 論文採択のための目標値

```python
acceptance_criteria = {
    "Stage A (必須)": {
        "nDCG@50 improvement": "> +10% vs BM25",
        "Recall@100": "> +15% vs BM25",
        "Statistical significance": "p < 0.05",
    },
    
    "Stage B (必須)": {
        "nDCG@10 improvement": "> +8% vs Cross-Encoder",
        "Kendall's tau": "> 0.65",
        "Human preference": "> 70% prefer our system",
    },
    
    "効率性 (推奨)": {
        "Latency": "< 2 minutes/query",
        "Cost": "< $2/query (with gpt-4o-mini)",
    },
    
    "汎化性能 (推奨)": {
        "Cross-venue consistency": "Improvement trend holds on ICML/ICLR",
    }
}
```

### マイルストーン

- **Week 4終了**: NeurIPSメイン実験完了 → ドラフト執筆可能
- **Week 6終了**: クロスベニュー検証完了 → 論文ほぼ完成
- **Week 8終了**: 図表・統計完備 → 投稿準備完了

---

## ⚠️ リスクと対策

### リスク1: 人間アノテーター不足

**対策**:
- 2名（あなた+1名）でも十分（LLMハイブリッド）
- 研究室ネットワークで募集
- 共著者としての貢献を認める

### リスク2: LLM-as-Judgeの妥当性が低い

**対策**:
- κ < 0.60の場合、人間アノテーションを追加
- アンサンブル投票で信頼性向上
- 不一致ケースの分析を論文に含める

### リスク3: ベースラインとの差が小さい

**対策**:
- Ablation Studyで各コンポーネントの貢献を示す
- 質的分析（ケーススタディ）を充実
- ユーザースタディで実用性を強調

### リスク4: 時間不足

**対策**:
- Phase 1-4を優先（NeurIPSのみで投稿可能）
- クロスベニュー検証は時間があれば
- ユーザースタディは完全にオプション

---

## 📚 参考文献（方法論）

### 評価プロトコル関連

- **LLM-as-a-Judge**: 
  - "Judging LLM-as-a-Judge" (NeurIPS 2023)
  - "Large Language Models are not Fair Evaluators" (ACL 2024)

- **人間評価プロトコル**:
  - "Measuring Interrater Reliability" (Fleiss' kappa, Cohen's kappa)
  - TREC Guidelines for Relevance Judgment

- **IR評価メトリクス**:
  - "Evaluation Measures for Search and Recommendation" (Järvelin & Kekäläinen)

### 関連システム

- Semantic Scholar Recommendations
- ResearchRabbit, Connected Papers
- Elicit, Consensus (LLM-based literature review)
- PaperQA, LlamaIndex (Document QA)

---

## 🎉 まとめ

### 実行可能性: ★★★★★

- 2名のアノテーター + LLMで実現可能
- 30-40時間の作業で論文執筆に必要なデータ取得
- API料金は$500程度（十分手頃）

### 新規性: ★★★★☆

- LLMベースの同義語展開（既存だが組み合わせが新しい）
- **レビューデータ統合の4軸LLM評価**（新規性高い）
- LLM-as-Judge with tiebreaking（方法論的貢献）

### インパクト: ★★★★☆

- 実用的なツールとして公開済み
- 研究者の文献調査時間を劇的短縮
- OpenReview以外にも拡張可能

### 実行計画

```
Week 1-2: クエリ設計、ツール準備、ベースライン実装
Week 3-4: 人間アノテーション（NeurIPS 300+200件）
Week 5:   LLM妥当性検証、拡張
Week 6:   メイン実験実行、統計検定
Week 7:   クロスベニュー検証（オプション）
Week 8:   図表作成、ドラフト執筆
Week 9-10: 内部レビュー、ブラッシュアップ
Week 11:  投稿！
```

**次のアクション**: 
1. もう1名のアノテーターに声をかける
2. 10個のクエリを具体的に選定
3. アノテーションガイドライン作成
4. ベースライン（BM25, SPECTER）を実装

---

**作成者**: システム分析に基づく戦略立案  
**更新**: 必要に応じて随時更新  
**連絡先**: 進捗共有・相談は随時

