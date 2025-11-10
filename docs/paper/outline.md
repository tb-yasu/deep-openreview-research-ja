# Deep OpenReview Research: LLM-Augmented Discovery and Ranking of Peer-Reviewed Papers

- Track: Applied Data Science (ADS) — recommended fit for system-focused, real-world impact
- Venue Target: KDD (next cycle)
- Repo: ../

## Abstract (150–200 words)
We present Deep OpenReview Research, an AI-assisted system that discovers and ranks peer-reviewed papers from OpenReview using a hybrid of information retrieval and large language model (LLM) evaluation. Users describe research interests in natural language; the system expands them into diverse synonyms, retrieves candidate papers across venues/years, integrates review-aware signals (meta-review, review comments, decision, presentation type), and performs a single-pass LLM evaluation to score relevance, novelty, impact, and practicality. A cost-aware workflow and caching enable fast, reproducible runs. In experiments over NeurIPS/ICML/ICLR proceedings, the system improves nDCG@k and Recall@k over keyword and embedding baselines while reducing time-to-insight. Case studies with researchers show reduced screening effort and higher satisfaction. We release code, prompts, and artifacts.

## 1 Introduction
- Problem: Keyword search often misses semantically relevant work; volume of accepted papers is large; review signals are underutilized for discovery.
- Opportunity: Combine OpenReview’s structured review ecosystem with LLMs’ semantic understanding to build a discovery and triage workflow for researchers and practitioners.
- Contributions:
  1) An LLM-augmented pipeline that transforms natural-language interests into robust synonym sets and retrieves/reranks papers using paper content and review metadata.
  2) A unified, single-pass LLM rubric scoring relevance, novelty, impact, and practicality, integrated with review-aware features into a final ranking.
  3) A cost/performance–tunable workflow (top-k, model choice, no-LLM fast mode) with caching for reproducibility.
  4) A comprehensive evaluation suite (IR metrics, cost/time, ablations, user study) and open-source artifact.

## 2 Related Work
- Scholarly discovery and literature review tools (Semantic Scholar, Elicit, OpenAlex; topic tagging; citation graph mining).
- IR with LLMs: re-ranking, query expansion, instruction retrieval, synthetic queries.
- Systems leveraging peer review metadata for search/recommendation.
- Agentic literature review assistants and workflow automation.

## 3 System Overview
- Workflow (seven steps): keyword extraction → synonym expansion (LLM) → retrieval (OpenReview) → initial scoring → candidate selection (top-k) → unified LLM evaluation → final ranking and report.
- Architecture: data fetcher, cache layer, scoring/ranking, LLM chain, report generation, CLI.
- Data model: papers, decisions, meta-reviews, reviews, presentation type, author responses.
- Cost knobs: top-k, model, skip LLM eval; deterministic mode/seeding where possible.

## 4 Method
### 4.1 Interest Parsing and Synonym Expansion
- Prompt design for extracting seed terms from natural-language description.
- Controlled expansion: domain synonyms, phrase variants, related subareas; de-dup, normalization.

### 4.2 Retrieval from OpenReview
- Venue/year filters; API usage; caching; rate limits; paper fields used (title, abstract, decision, meta-review, reviews).

### 4.3 Initial Scoring
- Keyword/phrase matching, TF-IDF/BM25 (optional), heuristic boosts (decision/presentation type), normalization.

### 4.4 Unified LLM Evaluation
- Single-pass rubric: relevance, novelty, impact, practicality. Scoring scales and calibration protocol.
- Input context packing: title/abstract + distilled review signals; token budgeting.
- Output schema and safety/robustness (format constraints, retries, consistency checks).

### 4.5 Review-Aware Features
- Meta-review summary signal, review sentiment/strength cues, decision and presentation type (Oral/Spotlight/Poster).
- Optional aggregation of reviewer numeric scores if available.

### 4.6 Final Ranking
- Score aggregation formula combining IR, review-aware, and LLM rubric scores; weight selection; normalization.
- Fast mode (no-LLM) and hybrid mode (LLM only for re-ranking top-m).

## 5 Evaluation
### 5.1 Datasets
- NeurIPS 2025, ICML 2024, ICLR 2024 (OpenReview-indexed). Specify counts and inclusion criteria.

### 5.2 Queries
- 20–50 natural-language research descriptions across subfields (GNNs, RL, vision, LLM efficiency, generative models, causality, graphs-for-drug-discovery, etc.).

### 5.3 Ground Truth
- Primary: human annotations (3+ annotators, 3-level or 4-level relevance, adjudication).
- Secondary proxies: area/track tags, Oral/Spotlight as higher-relevance indicators (used cautiously).

### 5.4 Baselines
- OpenReview keyword search; BM25/TF-IDF; dense retrieval (e.g., SBERT/Instructor/ColBERT) with optional re-rankers.
- LLM re-ranker without review signals; synonym expansion ablated; commercial tools if allowed (reported carefully).

### 5.5 Metrics and Protocol
- nDCG@k, MAP, Recall@k, MRR; time-to-first-meaningful-result; cost per query; throughput.
- Statistical testing; per-domain breakdown; sensitivity to k and model choice.

### 5.6 Results
- Main table: IR metrics across methods; cost/latency Pareto plots.
- Case studies: qualitative wins and failure modes.

## 6 Ablations and Analysis
- Without synonym expansion; without review-aware features; without unified rubric.
- Model variants (gpt-4o-mini vs gpt-4o, etc.); prompt/rubric variants.
- Budget sensitivity (top-k, m for re-rank); caching effects; robustness across venues/years.

## 7 User Study (Optional but Valuable)
- 8–12 participants (students/practitioners). Tasks: screening to top-N; measure time saved and satisfaction (SUS).
- Report qualitative feedback on usefulness and trust.

## 8 Reproducibility and Artifact
- Public code, exact prompts, default seeds, pinned dependencies.
- Cached paper snapshots (IDs + fields), query sets, annotation guidelines, scripts to reproduce tables/figures.
- Cost reporting and compute budget.

## 9 Ethics and Limitations
- LLM biases; cautious use of review content; privacy and terms-of-use; generalization beyond OpenReview venues.
- Failure modes: overfitting to popular phrases; hallucinated rubric justifications; domain coverage gaps.

## 10 Conclusion
- Summary of contributions; impact for researchers/industry; future work (multi-source ingestion, citation graphs, interactive refinement).

## References

---

## Submission Prep Checklist
- [ ] Track: ADS (or Research) finalized; CfP requirements validated (format/page limit/blindness).
- [ ] Queries and domains fixed; annotation protocol IRB/consent (if required).
- [ ] Baselines implemented and tuned; metrics scripted.
- [ ] Main/ablation results complete; figures/tables generated from scripts.
- [ ] Artifact: code, cached data indices, prompts, README, run scripts.
- [ ] Reproducibility checklist; ethics statement.

## Timeline (suggested)
- Week 1–2: Finalize scope, write Related Work, lock evaluation design.
- Week 3–4: Implement/tune baselines, run main experiments.
- Week 5: Ablations, user study (if any), figures/tables.
- Week 6: Full write-up, polish, artifact packaging, internal reviews.

---

## Mapping blog content → paper sections (for drafting)
- Blog “主な機能/ワークフロー/出力例” → Sections 3–4 + Appendix (prompts/rubric).
- Blog “使用例/ケース” → Case studies (5.6) and qualitative analysis.
- Blog “技術スタック/始め方” → Artifact and reproducibility guidance.


