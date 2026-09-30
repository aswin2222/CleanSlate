# CleanSlate - Known Limitations & Operational Boundaries
Document Version: 1.0.0

---

## 1. Dataset Scale & In-Memory Boundaries
- **In-Memory Threshold**: Datasets up to 2,000,000 rows can be fully transformed in-memory with exact deltas. Beyond 2,000,000 rows:
  - Profiling functions in streaming chunks.
  - Transformation planning is derived from a stratified representative sample.
  - Full dataset in-memory execution is declined with a clear structured error directing the operator to batch/distributed execution.
- **Extreme High-Dimensionality**: Maximum column limit is set to 200 columns (configurable up to 2,000) to guard against quadratic memory inflation during pairwise correlation and fuzzy match analysis.

## 2. LLM Capabilities & Boundaries
- **Zero Execution Privilege**: The LLM does not execute code, inspect raw unmasked data, or modify database entries directly. All mutations are performed by audited, deterministic Python transforms.
- **Provider Latency & Rate Limits**: Remote API calls (e.g. Gemini, OpenAI) may introduce variable latency. In production environments without external network access or during network partitions, the system operates seamlessly in deterministic heuristic mode (`llm_mode=heuristic_only`).
- **Prompt Injection Defense**: All LLM proposed rules pass through strict empirical verification (support >= 0.90, confidence >= 0.80) against observed data before being presented to the operator.

## 3. Formatting & Serialization
- **Parquet / Excel Nested Schemas**: Complex nested structs in Parquet or multi-level objects in JSON are flattened at ingestion; arbitrarily deep tree structures are quarantined or parsed as text.
- **Fuzzy Deduplication Performance**: Deduplication via `rapidfuzz` runs on sliding window chunks or indexed subsets (capped at 500 rows for pairwise O(N^2) comparisons) to maintain bounded execution time on large datasets.

## 4. Reversible Ledger Storage Considerations
- **Delta Growth on Destructive Steps**: Non-destructive transformations (whitespace trimming, date standardization, case normalization) only store cell coordinate diffs. Destructive steps like `drop_rows_violating` store the complete serialized row values in compressed gzip format to guarantee 100% exact inverse reconstruction. For datasets with massive row purges (>50%), delta storage volume may equal the original dataset size.
- **Extreme Sparsity Conservatism**: When a dataset has >90% null rate, automatic statistical imputation (mean/median/mode) is intentionally suppressed. Imputing values on 99% missing data creates synthetic hallucinations; CleanSlate flags these columns as `EXTREME_SPARSE` and requires explicit human configuration.
