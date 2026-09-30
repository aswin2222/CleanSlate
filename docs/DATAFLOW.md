# CleanSlate - Data Flow Specification
Document Version: 1.0.0

---

## 1. End-to-End Pipeline Data Flow

The following state machine details data progression from initial ingestion to verified export or complete rollback:

```
[Raw File Upload]
       │
       ▼
[Upload Guard & Sanitization] ──(Violation)──► [Quarantine Table] / [Rejection Code]
       │
       ▼ (Valid Rows)
[String Normalization & _rid Ingestion]
       │
       ├──► [Canonical Hash Calculation (Original SHA-256)]
       │
       ▼
[Chunked Streaming Profiler] ──► [Profile Cache (Keyed by SHA-256)]
       │
       ▼
[Sparsity & Low-Evidence Evaluator]
       │
       ▼
[Rule Candidate Generation (DSL)]
       │
       ▼
[Empirical Rule Verification (Support >= 0.90, N >= 30)]
       │
       ├───► [Masked Metadata Extractor (Max 5 PII-masked samples)]
       │              │
       │              ▼
       │      [LLM Semantic Inference (Optional)]
       │              │ (Timeout or Failure)
       │              ▼
       │      [Heuristic Fallback Taxonomy]
       │              │
       ▼              ▼
[Active Rules & Insufficient Evidence Rules]
       │
       ▼
[Planner: Transformation Ordering Engine]
       │
       ▼
[Virtual Scratch Dry-Run: Loss Estimator (Pre-Apply)]
       │
       ├──► [Per-Step Metrics: Row %, Cell %, Dist Shift, Entropy, Card, Corr]
       ├──► [Multi-Component Loss Score (0 - 100)]
       └──► [Human-Readable Loss Impact Sentence]
       │
       ▼
[User Approval Matrix (Interactive UI)]
       │
       ▼
[Reversible Executor]
       │
       ├──► Apply step 1..k (Approved steps only)
       ├──► Record Delta (cell_edits, dropped_rows, added_rows, column_ops)
       ├──► Compute hash_before & hash_after
       ├──► Record Actual Loss Metrics
       └──► Append to Atomic Ledger
       │
       ▼
[Clean Data Snapshot]
       │
       ├──► [Test Generator: Pandera Schema, Rule Pytests, Integration Tests]
       │            │
       │            ▼
       │    [Subprocess Runner: PRE vs POST Execution]
       │            │
       │            ▼
       │    [Mutation Testing: Injected Fault Detection Rate]
       │
       ├──► [Export Engine: CSV / Parquet with Formula Neutralization]
       │
       ▼ (If Rollback Triggered)
[Rollback Engine]
       │
       ├──► Iterate deltas in reverse sequence
       ├──► Invert cell edits and restore dropped rows by _rid
       └──► Recompute Canonical Hash
              │
              ├── Matches Original ──► State Restored (100% Reversibility Verified)
              └── Mismatch ──────────► Corrupted State Alert & Metric Trigger
```

---

## 2. Canonical Hash Data Flow & Specification

The Canonical Hash guarantees strict state equivalence before and after transformations and validates rollback round-trips.

```
DataFrame
  │
  ├── 1. Sort rows by immutable internal row identifier: `_rid`
  ├── 2. Order columns alphabetically (excluding internal temporary columns)
  ├── 3. For each row:
  │         For each column value v:
  │             Encode UTF-8 bytes
  │             Prefix with byte length: "<len>:<utf8_bytes>|"
  │         Terminate row with newline "\n"
  └── 4. Feed stream into SHA-256 hasher
```
This guarantees platform-independent, whitespace-exact, delimiter-agnostic reproducibility.
