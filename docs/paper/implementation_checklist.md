# 実装チェックリスト - Deep OpenReview Research 論文化

## 📋 Phase 1: 準備（Week 1-2）

### クエリセット作成
- [ ] 10個のクエリを選定
  - [ ] Graph ML（2個）: グラフ生成、GNN
  - [ ] NLP/LLM（2個）: 効率化、評価
  - [ ] Computer Vision（2個）: Transformer、生成モデル
  - [ ] RL（1個）: ロボティクス
  - [ ] 基盤技術（2個）: Federated Learning、AutoML
  - [ ] 応用（1個）: 創薬/時系列/セキュリティ
- [ ] 日本語3-4個、英語6-7個のバランス確認
- [ ] 各クエリの詳細説明文作成

### アノテーションツール
- [ ] Google Forms または専用UI作成
- [ ] アノテーションガイドライン完成（Stage A: 0/1/2）
- [ ] アノテーションガイドライン完成（Stage B: 1-5スケール）
- [ ] 練習セット20件を準備
- [ ] データ収集スプレッドシート準備

### ベースライン実装
- [ ] A1: Keywordマッチのみ実装
- [ ] A2: BM25実装（rank_bm25ライブラリ）
- [ ] A3: SPECTER/Sentence-BERT実装
- [ ] B1: BM25ランキング
- [ ] B2: Cross-Encoder Re-ranker実装
- [ ] 評価スクリプト（metrics.py）作成

### アノテーター確保
- [ ] もう1名のアノテーターに依頼
- [ ] 作業スケジュール合意
- [ ] 共著者 or 謝礼の合意

---

## 📝 Phase 2: データ収集（Week 3-4）

### Stage A: 初期検索評価
- [ ] パイロット100件（2名独立）
  - [ ] アノテーター1（あなた）: 100件
  - [ ] アノテーター2: 100件
- [ ] Cohen's kappa計算（目標: > 0.60）
- [ ] 不一致ケース特定（20-30件程度）
- [ ] 不一致ケースのLLM判定実装
- [ ] 多数決で最終ラベル確定
- [ ] 残り200件完了
  - [ ] アノテーター1: 100件
  - [ ] アノテーター2: 100件

### Stage B: ランキング評価
- [ ] 候補プール100件を固定（各手法のTop結果統合）
- [ ] Top 20のみ詳細評価（1-5スケール）
  - [ ] 10クエリ × 20論文 = 200件
  - [ ] アノテーター1: 全200件
  - [ ] アノテーター2: 全200件
- [ ] 不一致の議論・調整

---

## 🤖 Phase 3: LLM妥当性検証（Week 5）

### LLM-as-Judge実装
- [ ] GPT-4o Judge実装
- [ ] Claude Sonnet Judge実装
- [ ] Gemini Pro Judge実装
- [ ] アンサンブル投票機能実装

### 妥当性検証
- [ ] Stage Aの300件を3モデルで評価
- [ ] 各モデルと人間のCohen's kappa計算
- [ ] アンサンブルと人間のkappa計算（目標: > 0.65）
- [ ] 不一致パターン分析
- [ ] 検証レポート作成

### LLM拡張（条件: kappa > 0.65）
- [ ] 追加4,000件のLLMラベル生成
- [ ] 10%ランダムサンプリング（400件）
- [ ] サンプルの人間再確認
- [ ] 品質レポート作成

---

## 🧪 Phase 4: メイン実験（Week 6-7）

### Stage A実験（NeurIPS 2025）
- [ ] 4手法で検索実行
  - [ ] A1: Keyword Only
  - [ ] A2: BM25
  - [ ] A3: SPECTER
  - [ ] A4: Ours
- [ ] 評価メトリクス計算
  - [ ] Recall@10,20,50,100
  - [ ] nDCG@10,20,50
  - [ ] MAP, MRR
- [ ] 統計的有意性検定
  - [ ] Paired t-test
  - [ ] Wilcoxon signed-rank test
  - [ ] Cohen's d（効果量）

### Stage B実験（NeurIPS 2025）
- [ ] 4手法でランキング実行
  - [ ] B1: BM25
  - [ ] B2: Cross-Encoder
  - [ ] B3: LLM (no review)
  - [ ] B4: LLM (with review)
- [ ] 評価メトリクス計算
  - [ ] nDCG@10,20
  - [ ] Kendall's tau
  - [ ] Spearman's rho
  - [ ] Pairwise Accuracy
- [ ] 統計的有意性検定

### Ablation Study
- [ ] 同義語展開あり vs なし
- [ ] レビューデータあり vs なし
- [ ] 各スコア次元の寄与分析
- [ ] モデル比較（gpt-4o-mini vs gpt-4o）

### クロスベニュー検証（オプション）
- [ ] ICML 2024: 3クエリ × 20論文 = 60件
  - [ ] BM25 vs Ours比較
  - [ ] 人間ラベル付け
  - [ ] メトリクス計算
- [ ] ICLR 2024: 3クエリ × 20論文 = 60件
  - [ ] BM25 vs Ours比較
  - [ ] 人間ラベル付け
  - [ ] メトリクス計算

---

## 📊 Phase 5: 結果分析・可視化（Week 8）

### 図表作成
- [ ] **Table 1**: Stage A メトリクス比較
  - [ ] Recall@K, nDCG@K
  - [ ] 4手法 × 複数K値
  - [ ] p値、信頼区間
- [ ] **Table 2**: Stage B メトリクス比較
  - [ ] nDCG@K, Kendall's tau
  - [ ] 4手法の比較
  - [ ] p値、効果量
- [ ] **Table 3**: Cross-Venue結果（オプション）
- [ ] **Figure 1**: Recall/nDCG比較（棒グラフ）
- [ ] **Figure 2**: コスト vs 品質（Paretoプロット）
- [ ] **Figure 3**: Ablation Study結果（ヒートマップ）
- [ ] **Figure 4**: Per-query breakdown（箱ひげ図）

### 統計レポート
- [ ] すべてのp値、信頼区間、効果量を集計
- [ ] Per-query詳細結果
- [ ] エラー分析・失敗ケース収集

### ケーススタディ
- [ ] 成功例3-5件の詳細分析
- [ ] 失敗例2-3件の分析
- [ ] システムが見つけた「隠れた名論文」の例

---

## ✍️ Phase 6: 論文執筆（Week 9-10）

### セクション執筆
- [ ] Abstract（150-200語）
- [ ] 1. Introduction（2ページ）
- [ ] 2. Related Work（1.5ページ）
- [ ] 3. System Overview（1ページ）
- [ ] 4. Method（3ページ）
  - [ ] 4.1 Interest Parsing
  - [ ] 4.2 Synonym Expansion
  - [ ] 4.3 Retrieval
  - [ ] 4.4 Unified LLM Evaluation
  - [ ] 4.5 Review-Aware Features
- [ ] 5. Evaluation Setup（1.5ページ）
- [ ] 6. Main Results（2.5ページ）
- [ ] 7. Cross-Venue Generalization（1ページ、オプション）
- [ ] 8. Analysis（1.5ページ）
- [ ] 9. Conclusion（0.5ページ）
- [ ] References

### Appendix
- [ ] 詳細なプロンプト
- [ ] 追加実験結果
- [ ] アノテーションガイドライン完全版
- [ ] 実装詳細

### アーティファクト準備
- [ ] コードのクリーンアップ
- [ ] READMEの充実
- [ ] 再現実験スクリプト
- [ ] クエリセット公開
- [ ] アノテーションガイド公開
- [ ] 匿名化されたラベルデータ

---

## 🔍 Phase 7: レビュー・投稿準備（Week 11）

### 内部レビュー
- [ ] 共著者レビュー
- [ ] 研究室内レビュー
- [ ] 図表の最終確認
- [ ] 文法・スペルチェック

### KDD要件確認
- [ ] ページ数制限確認
- [ ] フォーマット準備（LaTeX）
- [ ] ブラインドレビュー対応
- [ ] Ethics Statement作成
- [ ] Reproducibility Statement作成

### 最終チェック
- [ ] すべての図表に番号・キャプション
- [ ] すべての主張に引用
- [ ] 統計的有意性の記載確認
- [ ] アーティファクトリンク確認
- [ ] 補足資料の準備

### 投稿
- [ ] PDFエクスポート
- [ ] 補足資料ZIP作成
- [ ] 投稿システムへアップロード
- [ ] メタデータ入力（タイトル、著者、キーワード）
- [ ] 🎉 Submit!

---

## 📅 タイムライン

| Week | フェーズ | マイルストーン |
|------|---------|----------------|
| 1-2  | Phase 1 | ツール・ベースライン完成 |
| 3-4  | Phase 2 | 人間アノテーション完了（500件） |
| 5    | Phase 3 | LLM妥当性検証、拡張 |
| 6-7  | Phase 4 | メイン実験完了 |
| 8    | Phase 5 | 図表・統計完備 |
| 9-10 | Phase 6 | ドラフト完成 |
| 11   | Phase 7 | 投稿！ |

---

## 🎯 成功基準（再掲）

### 必須目標
- [ ] Stage A: nDCG@50 改善 > +10% (p<0.05)
- [ ] Stage B: nDCG@10 改善 > +8% (p<0.05)
- [ ] Cohen's kappa (人間間) > 0.60
- [ ] Cohen's kappa (LLM vs 人間) > 0.65

### 推奨目標
- [ ] Recall@100 改善 > +15%
- [ ] Kendall's tau > 0.65
- [ ] クロスベニュー検証でトレンド一致
- [ ] コスト < $2/query

---

## 📞 連絡先・リソース

### チームメンバー
- アノテーター1: [あなた]
- アノテーター2: [TBD]
- レビューワー: [TBD]

### リポジトリ
- コード: `openreview-agent-ja/`
- データ: `openreview-agent-ja/storage/`
- 論文: `openreview-agent-ja/paper/`

### ドキュメント
- 評価戦略詳細: `evaluation_strategy_summary.md`
- 評価計画: `evaluation_plan.md`
- 論文アウトライン: `outline.md`

---

**最終更新**: 2025-01-08  
**ステータス**: 準備開始  
**次のアクション**: Phase 1のチェックボックスを埋めていく！

