# CleanSlate - System Assumptions & Design Decisions
Document Version: 1.0.0
Last Updated: 2026-09-30

Pursuant to the mission directive to work continuously and autonomously without blocking, this document logs all engineering assumptions made during the design and implementation of CleanSlate.

---

## 1. Data Ingestion & Storage
- **String Ingestion Representation**: In accordance with Principle P3, all ingested cells are loaded as raw string objects (`dtype=str`, `keep_default_na=False`). Missing markers (e.g., `""`, `"N/A"`, `"null"`, `"?"`, `"-"`) remain explicit strings until normalized by the transformation pipeline.
- **Row ID Assignment**: An internal, zero-indexed immutable integer column `_rid` is assigned upon ingestion. All delta tracking, ledger records, and rollback operations bind to `_rid`.
- **In-Memory Transformation Threshold**: Default threshold is set to 2,000,000 rows. Beyond this limit, profiling operates in streaming chunks, planning is derived from a stratified sample, and in-memory transformations will require explicit distributed/batched execution flags (logged in `KNOWN_LIMITATIONS.md`).
- **File System Encryption**: Dataset files at rest are encrypted using AES-128-CBC via Fernet. If `DATA_ENCRYPTION_KEY` is not provided in production, the application will refuse to boot. In development/testing environments, a deterministic fallback test key is generated if unset.

## 2. Security & Adversarial Defense
- **Formula Injection Mitigation**: Neutralization occurs strictly at export time and UI rendering by prefixing untrusted formula triggers (`=`, `+`, `-`, `@`, `\t`, `\r`) with a single quote (`'`). Data stored within SQLite/PostgreSQL and DataFrame memory remains untouched to preserve round-trip reversibility.
- **Quarantine Handling**: Malformed or ragged rows that violate CSV/delimiter structure are extracted into `quarantine_rows` with line numbers and raw text rather than terminating the ingestion process.
- **Prompt Injection Defense**: The LLM is restricted to observing anonymized column statistics, schema metadata, and up to 5 PII-masked sample values per column. All data appears inside isolated delimiter fences (`<<<DATA>>>...<<<END_DATA>>>`) accompanied by strict system instructions stating cell contents are untrusted data.

## 3. Semantic Inference & LLM Boundaries
- **Heuristic-First Reliability**: If no LLM endpoint or key is configured (`LLM_PROVIDER=none`), or upon any timeout or JSON parsing error, the system transparently falls back to deterministic heuristic semantic profiling and DSL rule generation.
- **Deterministic Code Execution**: The LLM never writes, compiles, or executes code, nor does it directly mutate data (Principle P1). Its role is restricted to proposing semantic tags and suggesting candidate rules from an allowlisted registry.
- **Confidence Calibration**: Candidate rules must achieve a support threshold of at least 0.90 and an applicable row count $\ge 30$ to achieve `ACTIVE` status. Absence of nulls in a sample does not constitute sufficient proof of a `not_null` constraint.

## 4. Reversibility & Canonical Hashing
- **Canonical Hash Definition**: SHA-256 computed over rows sorted by `_rid`, columns preserved in original sequence, each cell UTF-8 encoded with length-prefixed framing to eliminate delimiter ambiguity.
- **Ledger Invertibility**: Every transformation registers an exact inverse operation. The rollback mechanism asserts that `hash(restored_data) == hash(original_data)`. Any discrepancy sets status to `corrupted` and fires a high-priority alert.

## 5. Deployment & Execution Environment
- **Platform Compatibility**: Designed for cross-platform execution on Linux (Docker/Kubernetes) and Windows development hosts (PowerShell / cmd / WSL).
- **Default Database**: SQLite 3 with WAL mode enabled for single-node development and testing; PostgreSQL 16 for multi-replica Kubernetes / container deployment.
- **Cache Fallback**: In-memory LRU cache serves as the transparent fallback if Redis is unavailable.
