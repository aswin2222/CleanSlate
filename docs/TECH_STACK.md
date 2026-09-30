# CleanSlate - Technology Stack & Component Justifications
Document Version: 1.0.0

---

## 1. Backend Core & Libraries
- **Language**: Python 3.11 / 3.12 (Strong static typing, modern asyncio support, rich data ecosystem).
- **Web Framework**: FastAPI (High-performance ASGI, native Pydantic v2 validation, automatic OpenAPI documentation).
- **Data Engineering**:
  - `pandas`, `numpy`, `scipy`: Vectorized string, date, numeric transformation, Shannon entropy, Wasserstein metric, and Jensen-Shannon divergence calculations.
  - `pyarrow`: High-performance Parquet format I/O and serialized delta compression.
  - `openpyxl`: Excel workbook parsing and sheet inspection.
  - `charset-normalizer`: Multi-encoding auto-detection with fallback byte replacement accounting.
  - `rapidfuzz`: C++ accelerated Levenshtein clustering for exact and fuzzy deduplication.
  - `pandera`: DataFrame schema specification and programmatic assertion generation.
- **Data Persistence & Database**:
  - `SQLAlchemy 2.0`: Modern async/sync declarative ORM.
  - `Alembic`: Schema migration management.
  - `SQLite 3` (WAL mode): Lightweight, zero-dependency default persistence for local development and edge deployment.
  - `PostgreSQL 16`: Enterprise production tier database via `DATABASE_URL` switch.
  - `Redis` (with In-Memory LRU Fallback): High-speed cache for dataset fingerprints and LLM responses.
- **Security & Cryptography**:
  - `cryptography` (Fernet / AES-128-CBC): Data-at-rest payload encryption.
  - `PyJWT`: Signed stateless JSON Web Tokens for authentication.
  - `passlib[bcrypt]`: Salted, work-factor controlled credential hashing.
  - `slowapi`: Memory/Redis backed IP and token rate limiting.
- **Testing & Verification**:
  - `pytest`, `pytest-cov`: Deterministic unit, integration, and API test runners with coverage enforcement.
  - `hypothesis`: Property-based testing ensuring transformation reversibility across randomized strings, unicode, and edge cases.
- **Observability**:
  - `prometheus-client`: Core runtime metrics exporter (`/metrics`).
  - Structured JSON logger with request context and correlation IDs.

---

## 2. Frontend Technologies
- **Framework**: React 18 with TypeScript.
- **Build Tool**: Vite (Lightning fast HMR and ESM bundling).
- **Styling**: Tailwind CSS (Consistent design tokens, glassmorphism, responsive utilities).
- **Routing**: React Router v6.
- **State Management & Fetching**: TanStack Query v5 (React Query) for server state caching and optimistic updates.
- **Visualizations**: Recharts (Interactive SVG histograms, distribution charts, loss meters).
- **Icons**: Lucide React.

---

## 3. Infrastructure & DevOps
- **Containerization**: Multi-stage Dockerfiles (non-root unprivileged users, minimal attack surface).
- **Orchestration**:
  - `docker-compose`: Complete microservices stack (API, Frontend, PostgreSQL, Redis, Prometheus, Grafana).
  - `Kubernetes`: Manifests including Deployments, Services, ConfigMaps, Ingress, and HorizontalPodAutoscalers (HPA).
- **Monitoring**:
  - Prometheus: Timeseries metrics collection and alert evaluation.
  - Grafana: Pre-provisioned dashboards covering API throughput, pipeline latency, rollback safety, and survival rates.
- **CI/CD**: GitHub Actions workflows for automated linting, typing, property testing, and container deployment.
