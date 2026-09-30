"""Comprehensive API Integration Tests using FastAPI TestClient."""
from __future__ import annotations

import io
import pytest
from fastapi.testclient import TestClient

from app.db.models import User
from app.db.session import Base, SessionLocal, engine
from app.main import app


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth_headers(client):
    # Register test user
    email = "test_analyst@cleanslate.local"
    client.post("/auth/register", json={"email": email, "password": "password123!", "role": "analyst"})
    resp = client.post("/auth/login", json={"email": email, "password": "password123!"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestHealthAndObservability:
    def test_liveness(self, client):
        resp = client.get("/health/live")
        assert resp.status_code == 200
        assert resp.json() == {"status": "live"}

    def test_readiness(self, client):
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ready"}

    def test_metrics(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "cleanslate_http_requests_total" in resp.text


class TestAuthFlow:
    def test_auth_me(self, client, auth_headers):
        resp = client.get("/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "test_analyst@cleanslate.local"

    def test_unauthenticated_request_rejected(self, client):
        resp = client.get("/datasets")
        assert resp.status_code == 401


class TestDatasetAndPipelineFlow:
    def test_demo_load_and_full_pipeline(self, client, auth_headers):
        # 1. Load demo dataset
        demo_resp = client.post("/demo/load", headers=auth_headers)
        assert demo_resp.status_code == 201
        dataset_id = demo_resp.json()["dataset_id"]
        original_hash = demo_resp.json()["canonical_hash"]
        assert dataset_id is not None

        # 2. List datasets
        ds_list = client.get("/datasets", headers=auth_headers)
        assert ds_list.status_code == 200
        assert len(ds_list.json()) >= 1

        # 3. Create run
        run_resp = client.post(f"/datasets/{dataset_id}/runs", json={"llm_mode": "heuristic"}, headers=auth_headers)
        assert run_resp.status_code == 201
        run_id = run_resp.json()["id"]

        # 4. Profile dataset
        prof_resp = client.post(f"/runs/{run_id}/profile", headers=auth_headers)
        assert prof_resp.status_code == 200
        assert prof_resp.json()["total_rows"] == 8

        # 5. Infer rules
        infer_resp = client.post(f"/runs/{run_id}/infer", headers=auth_headers)
        assert infer_resp.status_code == 200
        assert infer_resp.json()["rules_count"] >= 1

        # 6. Generate plan
        plan_resp = client.post(f"/runs/{run_id}/plan", headers=auth_headers)
        assert plan_resp.status_code == 200
        steps = plan_resp.json()["steps"]
        assert len(steps) >= 1

        # 7. Apply approved steps
        apply_resp = client.post(f"/runs/{run_id}/apply", json={}, headers=auth_headers)
        assert apply_resp.status_code == 200
        assert apply_resp.json()["status"] == "applied"

        # 8. Test Rollback All -> Assert 100% hash match
        rollback_resp = client.post(f"/runs/{run_id}/rollback", json={"all_steps": True}, headers=auth_headers)
        assert rollback_resp.status_code == 200
        rb_data = rollback_resp.json()
        assert rb_data["matches_original"] is True
        assert rb_data["hash_original"] == original_hash
        assert rb_data["hash_current"] == original_hash

        # 9. Verify Audit log recorded events
        audit_resp = client.get(f"/audit?run_id={run_id}", headers=auth_headers)
        assert audit_resp.status_code == 200
        assert len(audit_resp.json()) >= 1
