# CleanSlate - Implementation Roadmap & Milestones
Document Version: 1.0.0
Target: Full Levels L1-L4 Delivery

---

## Milestone Schedule

| Phase | Duration | Scope | Deliverables & Status |
|---|---|---|---|
| **Phase 0** | 15 min | Repo Scaffold & Planning | Directory tree, config, git init, docs (SRS, ARCHITECTURE, DATAFLOW, WIREFRAMES, TECH_STACK, ROADMAP, ASSUMPTIONS), Makefile, CI skeletons. |
| **Phase 1** | 30 min | Ingestion, Guard & Profiling | Multiformat readers (CSV/TSV/JSON/NDJSON/XLSX/Parquet), encoding normalization, rowid, upload guard, quarantine engine, chunked profiler, sparsity analysis, unit tests. |
| **Phase 2** | 40 min | Reversible Engine & Ledger (CORE) | Base `Transformation`, registry, 14 transforms, atomic `Delta`, `CanonicalHash`, `Ledger`, `Executor`, `Rollback`, Hypothesis property tests. |
| **Phase 3** | 20 min | Loss Estimation Engine | Entropy (Shannon), Wasserstein, Jensen-Shannon, correlation drift, multi-component loss score, plain-English impact, predicted vs actual tracking, tests. |
| **Phase 4** | 35 min | Semantic Inference & Planner | DSL, deterministic candidates, empirical verifiers (support, confidence), LLM client with Pydantic validation, heuristic fallback, planner ordering, red-team prompt tests. |
| **Phase 5** | 20 min | Automated Test Generation | Pandera schema generator, pytest rules generator, integration test generator, subprocess runner (PRE/POST), mutation fault injection checker. |
| **Phase 6** | 30 min | Database, Security & API | SQLAlchemy 2 models, Alembic migrations, JWT auth, Fernet encryption at rest, rate limiting, audit logger, SSE event streamer, REST routes, API test suite. |
| **Phase 7** | 45 min | Frontend User Experience | Vite + React + TS + Tailwind, 11 responsive screens, interactive loss meter, rollback match animation, Adversarial Lab, Benchmarks page. |
| **Phase 8** | 20 min | Adversarial & Evaluation Suite | Synthetic corruptor, benchmark runner, 25-vector adversarial corpus generator, real execution, `benchmarks/results.json`, `benchmarks/report.md`. |
| **Phase 9** | 25 min | DevOps, Cloud & Monitoring | Multi-stage Dockerfiles, docker-compose stack, Prometheus config & alert rules, Grafana provisioned dashboards, Kubernetes manifests with HPA, CI/CD workflows. |
| **Phase 10**| 15 min | Verification & Final Polish | `scripts/verify_all.sh`, `REQUIREMENTS_TRACE.md`, `KNOWN_LIMITATIONS.md`, end-to-end verification, git commits, final executive report. |
