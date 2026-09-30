# CleanSlate - System Architecture
Document Version: 1.0.0
Compliance: Levels L1-L4

---

## 1. High-Level Architecture Overview

CleanSlate provides an enterprise-grade agentic data cleaning framework designed for safety, mathematical reversibility, and resilience against adversarial inputs. It couples deterministic profiling, validation, and rollback verification with decoupled AI inference.

```mermaid
graph TD
    User([User / Browser UI]) <-->|HTTPS / REST / SSE| API[FastAPI Gateway]
    
    subgraph Security & Ingestion Layer
        API --> UploadGuard[Upload Guard & Magic Bytes Sniffer]
        UploadGuard --> Decompressor[Decompression & Zip Bomb Defense]
        Decompressor --> Readers[Readers: CSV/JSON/XLSX/Parquet]
        Readers --> Quarantine[(Quarantine Storage)]
        Readers --> IngestionEngine[Ingestion Engine: Raw Strings + _rid]
        IngestionEngine --> RawStorage[(Encrypted Raw Storage: Fernet)]
    end

    subgraph Profiling & Sparsity
        IngestionEngine --> Profiler[Chunked Profiler & Statistics]
        Profiler --> SparsityModule[Sparsity & Evidence Evaluator]
        Profiler --> Cache[(Redis / In-Memory Cache)]
    end

    subgraph Semantic Inference & Rule Induction
        Profiler --> DeterministicRules[DSL Rule Inducer]
        SparsityModule --> DeterministicRules
        DeterministicRules --> Verifier[Empirical Rule Verifier: Support & Confidence]
        
        Verifier --> SemanticBridge{LLM Available?}
        SemanticBridge -->|Yes| LLMClient[LLM Client: Masked Metadata Only]
        SemanticBridge -->|No / Timeout / Error| HeuristicFallback[Heuristic Taxonomy Fallback]
        
        LLMClient --> OutputValidator[Pydantic JSON Schema Validator]
        OutputValidator --> RuleRegistry[(Active & Review Rules)]
        HeuristicFallback --> RuleRegistry
    end

    subgraph Planning & Loss Estimation
        RuleRegistry --> Planner[Transformation Planner]
        Planner --> DryRunEngine[Dry-Run Engine: Virtual Scratch Copy]
        DryRunEngine --> LossModel[Loss Estimator: Entropy, Wasserstein, JSD]
        LossModel --> PlanReview[Plan Review & Approval Matrix]
    end

    subgraph Safe Execution & Ledger
        PlanReview --> Executor[Reversible Executor]
        Executor --> TransformRegistry[Transform Registry: Apply / Invert]
        TransformRegistry --> Ledger[(Append-Only Audit Ledger)]
        TransformRegistry --> CanonicalHash[Canonical SHA-256 Verifier]
        CanonicalHash --> CleanStorage[(Clean Dataset Storage)]
    end

    subgraph Verification & Test Generation
        PlanReview --> TestGen[Test Generator: Pandera, Pytest, Integration]
        CleanStorage --> TestRunner[Subprocess Test Runner: Pre & Post]
        TestRunner --> MutationChecker[Mutation Fault Injector]
    end

    subgraph Observability
        API -.-> Prometheus[(Prometheus Metrics)]
        Prometheus -.-> Grafana[Grafana Dashboards & Alerts]
        API -.-> AuditLog[(Append-Only Audit Log)]
    end
```

---

## 2. Component Architecture & Separation of Concerns

```mermaid
classDiagram
    class Transformation {
        <<abstract>>
        +name: str
        +description: str
        +plan(df, params) PlanStep
        +dry_run(df, params) DryRunResult
        +apply(df, params) Tuple[DataFrame, Delta]
        +invert(df, delta) DataFrame
    }

    class Delta {
        +cell_edits: List[CellEdit]
        +dropped_rows: List[DroppedRow]
        +added_rows: List[AddedRow]
        +column_ops: List[ColumnOp]
        +metadata: Dict
        +to_dict() Dict
        +from_dict(d) Delta
    }

    class DryRunResult {
        +rows_removed: int
        +rows_removed_pct: float
        +cells_modified: int
        +cells_modified_pct: float
        +non_null_cells_destroyed: int
        +column_metrics: Dict
        +loss_score: float
        +loss_label: str
        +human_summary: str
    }

    class CanonicalHashVerifier {
        +compute_hash(df) str
        +verify_equality(df1, df2) bool
    }

    class LedgerEntry {
        +run_id: str
        +seq: int
        +step_id: str
        +transformation: str
        +params: Dict
        +hash_before: str
        +hash_after: str
        +delta_ref: str
        +predicted_loss: Dict
        +actual_loss: Dict
        +applied_at: datetime
        +actor: str
        +reverted: bool
    }

    Transformation <|-- NormalizeMissingMarkers
    Transformation <|-- TrimWhitespace
    Transformation <|-- NormalizeCase
    Transformation <|-- StandardizeDates
    Transformation <|-- ParseNumeric
    Transformation <|-- NormalizePhone
    Transformation <|-- DedupeExact
    Transformation <|-- DedupeFuzzy
    Transformation <|-- FixArithmetic
    Transformation <|-- CapOutliers
    Transformation <|-- ImputeMedian
    Transformation <|-- MergeCategories
    Transformation <|-- DropRowsViolating
    Transformation <|-- FlagOnly

    Transformation --> Delta : emits
    Transformation --> DryRunResult : produces
    LedgerEntry --> Delta : references
```

---

## 3. Data Flow & Security Boundary

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Client
    participant API as FastAPI Gateway
    participant Guard as Upload Guard
    participant Engine as Ingestion & Profiler
    participant Inference as Semantic / LLM Engine
    participant Planner as Plan & Loss Estimator
    participant Exec as Reversible Executor
    participant TestGen as Test Runner & Mutation

    User->>API: Upload Dataset (CSV/JSON/XLSX/Parquet)
    API->>Guard: Validate size, magic bytes, zip limits, strip nulls
    Guard-->>API: Status (Accepted / Quarantine)
    API->>Engine: Ingest as exact strings + assign _rid
    Engine->>Engine: Streamed Profiling & Sparsity evaluation
    API->>Inference: Induce candidate rules
    Inference->>Inference: Verify empirical support & confidence
    opt LLM Available
        Inference->>Inference: Send masked summary stats only (No raw data)
        Inference->>Inference: Validate returned DSL rules
    end
    API->>Planner: Generate transformation plan
    Planner->>Planner: Dry-run loss estimation (Entropy, JSD, Wasserstein)
    API-->>User: Present Interactive Plan & Loss Meter
    User->>API: Approve Steps & Request Apply
    API->>Exec: Verify hash_before & Execute approved steps
    Exec->>Exec: Write atomic ledger delta & calculate actual loss
    API->>TestGen: Generate Pandera & Pytest suite
    TestGen->>TestGen: Execute PRE vs POST suites in subprocess
    TestGen->>TestGen: Run Mutation Fault Checker
    API-->>User: Return Clean Data, Ledger, Verification Report
    
    opt Rollback Requested
        User->>API: Request Rollback All
        API->>Exec: Invert deltas in reverse sequence
        Exec->>Exec: Verify restored canonical hash == original hash
        API-->>User: Hash match confirmed (100% reversible)
    end
```
