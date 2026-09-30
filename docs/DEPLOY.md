# CleanSlate Deployment & Operations Manual

## 1. Quickstart: Docker Compose Full-Stack Deployment

The fastest way to deploy CleanSlate in enterprise staging or production is using Docker Compose:

```bash
# Clone the repository
git clone https://github.com/enterprise/cleanslate.git
cd cleanslate

# Configure secrets in .env
cp .env.example .env

# Launch all 6 services (Backend, Frontend, PostgreSQL, Redis, Prometheus, Grafana)
docker compose up -d --build
```

### Deployed Services & Ports:

| Service | Port | Description |
|---|---|---|
| **CleanSlate Web UI** | `http://localhost:3000` | React / Tailwind enterprise interface |
| **CleanSlate API & Docs** | `http://localhost:8000/docs` | FastAPI Swagger / OpenAPI documentation |
| **System Health** | `http://localhost:8000/health` | Readiness & Liveness JSON probes |
| **Prometheus Metrics** | `http://localhost:9090` | Time-series metrics and alert rules |
| **Grafana Dashboard** | `http://localhost:3001` | Pre-provisioned operational metrics (admin/admin) |
| **PostgreSQL 16** | `localhost:5432` | Relational audit logs & metadata |
| **Redis 7** | `localhost:6379` | Token-bucket sliding rate limiter cache |

---

## 2. Kubernetes Deployment (Production EKS / GKE / AKS)

### 2.1 Namespace & Secrets Provisioning

```bash
# Create namespace
kubectl create namespace cleanslate

# Apply ConfigMap & Secrets
kubectl apply -f deploy/k8s/configmap.yaml
kubectl apply -f deploy/k8s/secret.yaml
```

### 2.2 Deploy Workloads & Services

```bash
# Deploy backend API with HPA autoscaling
kubectl apply -f deploy/k8s/backend-deployment.yaml
kubectl apply -f deploy/k8s/backend-service.yaml

# Deploy frontend SPA with Ingress TLS
kubectl apply -f deploy/k8s/frontend-and-ingress.yaml
```

### 2.3 Verify Pod Readiness

```bash
kubectl get pods -n cleanslate -l app=cleanslate-backend
kubectl logs -n cleanslate -l app=cleanslate-backend --tail=50
```

---

## 3. Environment Variables Reference

| Variable | Default | Purpose |
|---|---|---|
| `ENVIRONMENT` | `production` | Runtime mode (`development`, `staging`, `production`) |
| `DATABASE_URL` | `sqlite:///./data/cleanslate.db` | PostgreSQL connection string for enterprise clusters |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis caching & sliding rate limiter store |
| `JWT_SECRET` | Required in prod | 256-bit cryptographically secure signing secret |
| `DATA_ENCRYPTION_KEY` | Required in prod | 32-byte URL-safe base64 key for Fernet payload encryption |
| `MAX_UPLOAD_BYTES` | `52428800` (50MB) | Maximum permitted upload file size |
| `SPARSE_THRESHOLD` | `0.90` | Null rate threshold above which columns enter extreme sparsity mode |
| `PROMETHEUS_METRICS` | `true` | Exposes `/metrics` endpoint for Prometheus scraping |

---

## 4. Disaster Recovery & Rollback Runbook

### 4.1 Guaranteed Rollback Procedure

When an automated pipeline must be reversed:
1. Navigate to the dataset execution view: `/apply?run_id=<RUN_ID>`.
2. Click **Rollback All Steps**.
3. CleanSlate traverses the append-only ledger in reverse chronological sequence, applying inverse diffs.
4. CleanSlate recalculates the canonical SHA-256 hash and validates:
   $$\text{SHA256}(\text{DF}_{\text{restored}}) == \text{SHA256}(\text{DF}_{\text{original}})$$
5. The system emits a green **MATCH = TRUE (100.0%)** cryptographic proof.

### 4.2 CLI Disaster Rollback Script

If UI access is disrupted, execute the headless rollback CLI tool:

```bash
python scripts/headless_rollback.py --run-id <RUN_ID> --output ./recovered_dataset.csv
```

---

## 5. Security & Compliance Checklist

- [x] **Non-Root Execution:** Backend runs under UID `10001` (`appuser`).
- [x] **Data Encryption at Rest:** Fernet AES-128-CBC with HMAC-SHA256 authenticated encryption.
- [x] **Injection Defenses:** Formula injections (`=`, `+`, `-`, `@`) neutralized before export.
- [x] **Zip-Bomb Guard:** Rejection when uncompressed ratio exceeds 50:1 or total size exceeds 50MB.
- [x] **Rate Limiting:** Sliding token bucket prevents DoS and brute-force attacks.
- [x] **Immutable Audit Trail:** All operations recorded with operator email, timestamp, and before/after SHA-256 hashes.
