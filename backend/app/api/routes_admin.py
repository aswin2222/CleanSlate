"""Administrative and demo routes: audit trails, demo dataset loading, benchmark & adversarial triggers."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import settings
from app.db.models import AuditEvent, BenchmarkResult, Dataset, User
from app.db.session import get_db
from app.execution.canonical_hash import compute_canonical_hash
from app.ingestion.rowid import assign_stable_row_ids
from app.security.crypto import encryptor

admin_router = APIRouter(tags=["Admin & Demo"])


@admin_router.get("/audit")
def get_audit_trail(
    run_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Retrieves immutable append-only audit trail."""
    query = db.query(AuditEvent)
    if run_id:
        query = query.filter(AuditEvent.run_id == run_id)
    events = query.order_by(AuditEvent.ts.desc()).limit(limit).all()

    return [
        {
            "id": e.id,
            "timestamp": e.ts.isoformat(),
            "actor": e.actor,
            "run_id": e.run_id,
            "event": e.event,
            "details": json.loads(e.details_json),
        }
        for e in events
    ]


@admin_router.post("/demo/load", status_code=status.HTTP_201_CREATED)
def load_demo_dataset(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Creates a seeded dirty enterprise demo dataset for the user:
    Contains mixed date formats, whitespace dirt, currency symbols, missing markers,
    formula injections, and duplicate rows.
    """
    # Deterministic messy enterprise orders dataset
    data = {
        "order_id": ["ORD-1001", "ORD-1002", "ORD-1003", "ORD-1004", "ORD-1005", "ORD-1001", "ORD-1006", "ORD-1007"],
        "customer_email": ["alice@enterprise.com", "  bob@corp.org  ", "charlie@web.io", "diana@test.com", "N/A", "alice@enterprise.com", "=cmd|'calc'!A0", "frank@co.uk"],
        "order_date": ["2024-01-15", "01/16/2024", "17-01-2024", "2024-01-18", "2024-01-19", "2024-01-15", "2024-01-20", "2024-01-21"],
        "ship_date": ["2024-01-20", "2024-01-22", "2024-01-25", "2024-01-22", "2024-01-24", "2024-01-20", "2024-01-23", "2024-01-26"],
        "quantity": ["2", "  3  ", "1", "4", "2", "2", "5", "10"],
        "unit_price": ["$10.50", "20.00", "€15.00", "$50.00", "12.50", "$10.50", "100.00", "5.00"],
        "total_amount": ["21.00", "60.00", "15.00", "200.00", "25.00", "21.00", "500.00", "50.00"],
        "status": ["COMPLETED", "completed", "PENDING", "pending", "CANCELLED", "COMPLETED", "pending", "COMPLETED"],
    }

    df = pd.DataFrame(data, dtype=str)
    csv_text = df.to_csv(index=False)
    raw_bytes = csv_text.encode("utf-8")
    sha256_orig = hashlib.sha256(raw_bytes).hexdigest()

    df_with_rid = assign_stable_row_ids(df)
    canonical_hash_val = compute_canonical_hash(df_with_rid)

    # Encrypt and save
    encrypted_bytes = encryptor.encrypt_bytes(raw_bytes)
    storage_path = settings.storage_path / "datasets"
    storage_path.mkdir(parents=True, exist_ok=True)
    file_path = storage_path / f"demo_orders_{current_user.id[:8]}.csv.enc"
    file_path.write_bytes(encrypted_bytes)

    dataset = Dataset(
        owner_id=current_user.id,
        original_filename_sanitized="demo_enterprise_orders.csv",
        stored_path=str(file_path),
        sha256_original=sha256_orig,
        canonical_hash=canonical_hash_val,
        format="csv",
        rows=len(df),
        cols=len(df.columns),
        size_bytes=len(raw_bytes),
        encrypted=True,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    audit = AuditEvent(
        actor=current_user.email,
        event="LOAD_DEMO_DATASET",
        details_json=f'{{"dataset_id": "{dataset.id}", "rows": {dataset.rows}}}',
    )
    db.add(audit)
    db.commit()

    return {
        "status": "loaded",
        "dataset_id": dataset.id,
        "filename": dataset.original_filename_sanitized,
        "rows": dataset.rows,
        "canonical_hash": dataset.canonical_hash,
    }


@admin_router.get("/benchmarks/latest")
def get_latest_benchmark(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieves latest executed benchmark results."""
    bm_file = Path("benchmarks/results.json")
    if bm_file.exists():
        try:
            return json.loads(bm_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    latest_db = db.query(BenchmarkResult).order_by(BenchmarkResult.ts.desc()).first()
    if latest_db:
        return json.loads(latest_db.results_json)

    return {
        "status": "no_benchmark_run_yet",
        "message": "Run 'make bench' or POST /benchmarks/run to produce real benchmark results.",
    }
