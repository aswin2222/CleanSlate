# Software Requirements Specification (SRS)
## Project CleanSlate: Autonomous, Safe, Reversible Data Cleaning Agent
**Document Version:** 1.0.0  
**Target Compliance:** Levels L1 - L4  

---

## 1. Introduction
CleanSlate is an agentic, test-driven data cleaning planner engineered for messy, heterogeneous enterprise datasets. It combines deterministic data profiling and rule verification with semantic LLM inference, predictive information loss modeling, and guaranteed round-trip reversibility via an append-only audit ledger and canonical cryptographic hashing.

### 1.1 Purpose
This specification documents the functional requirements (R1–R5), non-functional constraints (P1–P8), data models, system boundaries, and verification criteria for CleanSlate across enterprise tiers L1 (Planning), L2 (MVP & Logic), L3 (Security & CI/CD), and L4 (DevOps & Observability).

### 1.2 Core Architectural Principles
- **P1: Separation of Powers**: LLM proposes; deterministic engine executes and verifies. LLM never writes or executes code.
- **P2: Tripartite Transformation**: Every transformation must implement `dry_run`, `apply`, and `invert`.
- **P3: Immutability & Exact Strings**: All ingested cells are raw strings. Original uploads are immutable. Rollback guarantees exact canonical hash equality.
- **P4: Hostile Data Isolation**: Cell content is treated as untrusted text, guarding against prompt injection, CSV/formula injection, and SQL injection.
- **P5: Guarded Inference**: Low evidence leads to flagging and skipping rather than silent guessing or hazardous imputation.
- **P6: Append-Only Auditability**: All actions record actor, confidence, rationale, and timestamps.
- **P7: Grounded Metrics**: No fabricated benchmark scores. All metrics reflect genuine programmatic execution.
- **P8: Decoupled LLM Dependability**: Fully functional in zero-LLM heuristic mode, with pluggable support for OpenAI, Ollama, Gemini, and Groq.

---

## 2. Functional Requirements

### 2.1 Ingestion & Profiling (R1)
- **REQ-1.1 Format Ingestion**: Support CSV, TSV (with automatic delimiter sniffing), JSON, JSONL/NDJSON (1-level flattening), XLSX (multi-sheet selectable), and Apache Parquet.
- **REQ-1.2 Type Preservation**: Ingest all cells as `str` (`keep_default_na=False`). Assign stable internal row identifier `_rid` (0..n-1).
- **REQ-1.3 Encoding Normalization**: Detect encodings (UTF-8, UTF-16, Latin-1) using `charset-normalizer`. Replace and tally undecodable bytes.
- **REQ-1.4 Streamed Chunking**: Process large datasets in chunks (default 50,000 rows/chunk). Refuse in-memory transformation above 2,000,000 rows with structured guidance.
- **REQ-1.5 Quarantine Engine**: Isolate malformed or ragged rows to `quarantine_rows` with line numbers and failure reasons without aborting valid rows.
- **REQ-1.6 Deep Profiling**: Tally semantic-neutral types, missing markers, distinct counts, numeric descriptive statistics, IQR/MAD outliers, string patterns, duplicate/near-duplicate counts, and extreme sparsity flags.

### 2.2 Semantic Inference & DSL (R2)
- **REQ-2.1 Candidate Rule Generation**: Deterministically identify candidates using the DSL: `not_null`, `unique`, `range`, `non_negative`, `allowed_values`, `pattern`, `type`, `date_order`, `arithmetic`, `functional_dependency`, `length`, `not_future`, `cross_field_consistency`, `referential`.
- **REQ-2.2 Empirical Verification**: Compute support, violation counts, and sample violators. Promote candidates to `ACTIVE` only if support $\ge 0.90$ and $N \ge 30$.
- **REQ-2.3 LLM Semantic Enrichment**: Transmit masked summary metadata to LLM. Receive validated Pydantic schema mappings and rule recommendations.
- **REQ-2.4 Heuristic Fallback**: Instantly switch to column keyword taxonomy if `LLM_PROVIDER=none` or upon connection/validation failures.
- **REQ-2.5 Rule Lifecycle Management**: Support state transitions (`active`, `needs_review`, `insufficient_evidence`, `rejected_by_user`).

### 2.3 Loss Estimation & Reversible Execution (R3)
- **REQ-3.1 Pre-Execution Loss Estimation**: Compute multi-component loss score $S \in [0, 100]$:
  $$S = 100 \times (0.35 R_{row} + 0.15 R_{cell} + 0.20 D_{dist} + 0.15 E_{entropy} + 0.10 C_{card} + 0.05 K_{corr})$$
  Categorize into LOW ($<20$), MEDIUM ($20-50$), HIGH ($>50$).
- **REQ-3.2 Plain-English Impact Summaries**: Generate human-readable explanations of data alterations prior to user commitment.
- **REQ-3.3 Cumulative Pipeline Modeling**: Evaluate compound loss iteratively across scratch copies.
- **REQ-3.4 Reversible Ledger**: Maintain atomic delta structures (`cell_edits`, `dropped_rows`, `added_rows`, `column_ops`).
- **REQ-3.5 Canonical Verification**: Compute SHA-256 canonical hash before and after execution. Guarantee 100% hash equality upon rollback.

### 2.4 Automated Test Generation (R4)
- **REQ-4.1 Suite Generation**: Produce deterministic test files under `generated_tests/<run_id>/`:
  - `test_schema.py`: Pandera DataFrameSchema assertions.
  - `test_rules.py`: Parametrized pytest verifying rule fulfillment.
  - `test_integration.py`: Row reconciliation, immutability of untouched columns, ledger integrity, rollback round-trip.
- **REQ-4.2 Pre/Post Test Runner**: Execute test suite via isolated subprocess on pre-cleaned and post-cleaned data. Compare violation rates and verify regressions.
- **REQ-4.3 Mutation Testing**: Inject controlled synthetic mutations (e.g. broken arithmetic, null injections) to compute and report suite fault detection rate.

### 2.5 Adversarial Defense & Evaluation (R5)
- **REQ-5.1 Upload Guardrail**: Enforce 200 MB max payload, MIME/magic byte checks, 2,000 max columns, 100,000 max char field length, and decompression ratio limits.
- **REQ-5.2 Injection Neutralization**: Neutralize CSV formula injection triggers (`=`, `+`, `-`, `@`) upon export and render.
- **REQ-5.3 Adversarial Benchmark Corpus**: Maintain $\ge 25$ synthetic attack files to verify zero HTTP 500 errors and measure survival rate.
- **REQ-5.4 Synthetic Corruptor & Benchmark**: Benchmark pipeline accuracy against known corruption ground truths.

---

## 3. Non-Functional Requirements
- **NFR-1 Performance**: Profile $\ge 50,000$ rows in under 5.0 seconds on standard compute.
- **NFR-2 Reliability**: Zero unhandled exceptions or hangs on adversarial or corrupt payloads.
- **NFR-3 Security**: Fernet encryption at rest, JWT authentication with bcrypt hashing, strict rate limiting, role-based access control.
- **NFR-4 Observability**: Prometheus instrumentation across all pipeline stages, structured JSON logging, Grafana dashboard provisioning.
- **NFR-5 Portability**: Docker multi-stage containerization, Kubernetes readiness with HPA, cross-platform dev environment.
