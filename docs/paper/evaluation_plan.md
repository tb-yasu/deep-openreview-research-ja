# Evaluation Plan: Retrieval from User Input and LLM-Based Ranking

This plan isolates and rigorously evaluates the two core contributions:
1) Retrieval quality from natural-language user input (query parsing + synonym expansion + candidate retrieval).
2) Final ranking quality using the unified LLM rubric with review-aware features.

## 0. Datasets and Scope
- Venues/Years: NeurIPS 2025, ICML 2024, ICLR 2024 (OpenReview-indexed).
- Items: Papers with title, abstract, decision, meta-review, review comments, presentation type; author responses if available.
- Caching: Use local cache snapshots to ensure reproducibility and stable inputs across runs.

## 1. Query Set
- 20–50 natural-language descriptions representing diverse subfields (e.g., GNNs, RL, LLM efficiency, generative models, causality, graphs for drug discovery).
- Bilingual coverage (Japanese and English) where applicable; measure language effects.
- Store queries with unique IDs and brief rationales; include example positives if known.

## 2. Ground Truth Annotations
- Relevance scale: 0 (irrelevant), 1 (partially relevant), 2 (highly relevant).
- Annotators: ≥3; blind to method; adjudication process for disagreements.
- Inter-annotator reliability: Cohen’s/Fleiss’ kappa and Krippendorff’s alpha.
- Annotation guide: clear inclusion/exclusion criteria; examples and edge cases.

## 3. Stage A — Retrieval Evaluation (from initial user input)
### 3.1 Methods
- A1 Keyword-Baseline: OpenReview keyword match on seeds only (no expansion).
- A2 BM25/TF-IDF: Classic IR baseline over title+abstract.
- A3 Dense Retrieval: Sentence-BERT / Instructor / e5 / ColBERT (pick 1–2 strong baselines).
- A4 LLM Expansion (Ours): Natural-language → seeds → synonym expansion by LLM → retrieval (can reuse BM25/Dense as backends).
- Variants:
  - Expansion size m ∈ {10, 25, 50}.
  - Normalization/lemmatization on/off.
  - Language of query (ja/en).

### 3.2 Candidate Pool and Cutoffs
- For each query, retrieve top K candidates (K ∈ {50, 100, 200}).
- Save pools per method for downstream Stage B analysis; ensure identical K across methods where compared.

### 3.3 Metrics
- Recall@k (k ∈ {10, 20, 50, 100}).
- nDCG@k (graded relevance using {0,1,2}).
- MAP, MRR (optional).
- Efficiency: latency (per query), system throughput, API cost (if LLM is used for expansion).

### 3.4 Protocol
- Fix random seeds; enable caching.
- Cross-validate hyperparameters on a small development subset (e.g., 20% queries).
- Statistical testing: paired t-test and Wilcoxon signed-rank on per-query metrics.

## 4. Stage B — Ranking Evaluation (final ordering with LLM rubric)
### 4.1 Candidate Pool
- Use a fixed strong pool per query (e.g., top 100 from A3 Dense Retrieval or union of A2/A3/A4). The pool must be identical when comparing ranking methods.

### 4.2 Ranking Methods
- B1 Heuristic Rank: keyword/bm25 score only.
- B2 Cross-Encoder Ranker: e.g., MS MARCO–tuned cross-encoder re-ranker.
- B3 LLM Rubric (Ours, no review): unified LLM scoring of relevance/novelty/impact/practicality from title+abstract only.
- B4 LLM Rubric (Ours, with review): add meta-review, decision, presentation type, distilled review snippets.
- Ablations:
  - Remove individual rubric dimensions (e.g., practicality off).
  - Remove specific review-aware features (e.g., no decision or no presentation type).
  - Model choice (gpt-4o-mini vs gpt-4o).
  - Re-ranking only top m ∈ {20, 50, 100}.

### 4.3 Metrics
- nDCG@k, MAP, MRR using graded labels.
- Pairwise accuracy against human preference on sampled pairs.
- Rank correlation: Kendall’s tau / Spearman to human ranking on a subset.
- Efficiency: token usage, latency, and cost per query; throughput under batch settings.

### 4.4 Robustness and Calibration
- Output schema enforcement and retry policy; measure formatting failure rate.
- Score calibration stability across seeds; variance of LLM outputs across repeated runs (n=3).

## 5. User Study (Optional but Valuable)
- Participants: 8–12 (students/practitioners).
- Task: From candidate pool to top-N shortlist; measure time-to-insight, SUS score, perceived trust/usefulness.
- Compare B1/B2 vs B4 qualitatively and quantitatively.

## 6. Reporting
### 6.1 Main Tables/Figures
- Table A: Retrieval metrics (Recall@k, nDCG@k) across A1–A4.
- Table B: Ranking metrics (nDCG@k, MAP, MRR) across B1–B4.
- Figure: Cost/latency vs quality (Pareto curves) for Stage B methods.
- Figure: Ablation impacts (bar plots).

### 6.2 Statistical Significance
- Report p-values for paired comparisons; include effect sizes (Cliff’s delta).

### 6.3 Reproducibility
- Release: queries, annotation guide, anonymized labels, candidate pools, scripts to regenerate all tables/figures, prompts, and configs.
- Pin dependencies; record exact model versions; seed control; cache snapshots with content hashes.

## 7. Risks and Mitigations
- Annotation load: limit to top-K pools; pre-filter obvious negatives; adjudication schedule.
- API cost/time: batch LLM calls; use mini models for most runs; sample efficiency analyses.
- Venue data drift: lock snapshot dates; record commit hashes of data fetchers.

## 8. Acceptance Criteria (Success Targets)
- Stage A: +5–10 absolute points nDCG@20 vs Keyword/BM25 baselines on average; consistent Recall@100 gains.
- Stage B: LLM+review-aware (B4) significantly outperforms strong cross-encoder and LLM-no-review (B3) on nDCG@20 and pairwise accuracy, with acceptable cost (<$1/query, default settings).
- Efficiency: Demonstrate tunable trade-off (fast mode within 10–20% of best quality at fraction of cost).

## 9. Implementation Checklist
- [ ] Finalize query set and annotation guide.
- [ ] Implement A1–A4 retrieval pipelines with caching and logging.
- [ ] Build labeling tool or protocol; collect labels; compute IAA.
- [ ] Construct fixed candidate pools for Stage B.
- [ ] Implement B1–B4 rankers with unified evaluation harness.
- [ ] Run ablations, cost/latency logging, and significance tests.
- [ ] Generate all plots/tables from scripts; package artifacts.


