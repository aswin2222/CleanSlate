# CleanSlate - Known Limitations & Operational Boundaries
Document Version: 1.0.0

---

## 1. Dataset Scale & In-Memory Boundaries
- **In-Memory Threshold**: Datasets up to 2,000,000 rows can be fully transformed in-memory with exact deltas. Beyond 2,000,000 rows:
  - Profiling functions in streaming chunks.
  - Transformation planning is derived from a stratified representative sample.
  - Full dataset in-memory execution is declined with a clear structured error directing the operator to batch/distributed execution.
- **Extreme High-Dimensionality**: Maximum column limit is set to 2,000 columns to guard against quadratic memory inflation during correlation analysis.

## 2. LLM Capabilities & Boundaries
- **Zero Execution Privilege**: The LLM does not execute code, inspect raw unmasked data, or modify database entries directly.
- **Provider Latency**: Remote API calls (e.g. Gemini, OpenAI) may introduce variable latency. In production environments without external network access, the system operates seamlessly in heuristic mode (`LLM_PROVIDER=none`) or with local Ollama instances.

## 3. Formatting & Serialization
- **Parquet / Excel Nested Schemas**: Complex nested structs in Parquet or multi-level objects in JSON are flattened by one level at ingestion; arbitrarily deep tree structures are quarantined or parsed as text.
- **Fuzzy Deduplication Performance**: Deduplication via `rapidfuzz` runs on blocking keys or indexed subsets to maintain bounded execution time on large datasets.
