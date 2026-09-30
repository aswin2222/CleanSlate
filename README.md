# CleanSlate
> **Autonomous, Safe, Reversible, Test-Driven Data-Cleaning Agent for Messy Enterprise Datasets**  
> Hackathon Project PNG6 (Levels L1 - L4 Complete)

---

## 🌟 Overview & Problem Statement
CleanSlate is an enterprise agentic data cleaning system that autonomously profiles messy datasets, infers semantic constraints, and generates reversible, test-driven cleaning pipelines while calculating exact information loss.

### Non-Negotiable Core Principles
1. **P1. Separation of Powers**: LLM only proposes. Deterministic code executes and verifies.
2. **P2. Tripartite Transformation**: Every single transformation implements `dry_run`, `apply`, and exact `invert`.
3. **P3. String Immutability**: All data ingested as exact strings (`dtype=str`, `keep_default_na=False`). Rollback reproduces exact original canonical SHA-256 hash.
4. **P4. Hostile Data Posture**: Cell contents are untrusted data, never instructions (prompt injection, formula injection, SQL injection defended).
5. **P5. Safe Caution**: Weak evidence triggers flagging and human review—never silent guessing or hazardous imputation.
6. **P6. Append-Only Auditability**: Comprehensive audit trail with reasons, confidence, and actor stamps.
7. **P7. Grounded Metrics**: No fake numbers. All benchmarks, test results, and loss metrics derive from real executions.
8. **P8. Dual Heuristic/LLM Engine**: Operates with zero LLM configured (deterministic heuristics) or with any OpenAI-compatible provider (Ollama, Gemini, Groq, OpenAI).

---

## 🏗 Architecture
```
[Raw Enterprise Data] -> [Upload Guard & Quarantine] -> [Exact String Ingest + _rid]
                                                                  │
                                                      [Canonical Hash SHA-256]
                                                                  │
                                                        [Chunked Profiler]
                                                                  │
                                                   [DSL & Semantic Inference]
                                                                  │
                                                    [Dry-Run Loss Estimator]
                                                                  │
                                                [Reversible Executor & Ledger]
                                                                  │
                                                [Automated Tests (PRE / POST)]
                                                                  │
                                                  [Verified Clean Data / Rollback]
```

---

## 🚀 Quickstart (3 Commands)
```bash
# 1. Clone & Setup
git clone <repo-url> cleanslate && cd cleanslate
make setup

# 2. Run Backend & Frontend in Development
make dev

# 3. Execute Verification Suite (All Requirements R1-R5, L1-L4)
make verify
```

---

## 📊 Verification & Demo Walkthrough
Run the end-to-end self-verifying test suite:
```bash
bash scripts/verify_all.sh
```
Or run the automated demo:
```bash
python scripts/generate_demo_data.py --run-flow
```
