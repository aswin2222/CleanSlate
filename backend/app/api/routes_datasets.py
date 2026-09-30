"""Dataset management routes: upload, inspection, and deletion."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas import DatasetResponse, UploadGuardResponse
from app.config import settings
from app.db.models import AuditEvent, Dataset, QuarantineRow, User
from app.db.session import get_db
from app.execution.canonical_hash import compute_canonical_hash
from app.ingestion.readers import read_dataset_file
from app.security.crypto import encryptor
from app.security.upload_guard import UploadGuard

datasets_router = APIRouter(prefix="/datasets", tags=["Datasets"])
guard = UploadGuard()


@datasets_router.post("", response_model=UploadGuardResponse, status_code=status.HTTP_201_CREATED)
@datasets_router.post("/upload", response_model=UploadGuardResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    format: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UploadGuardResponse:
    """
    Ingests and securely validates an enterprise dataset file.
    Runs upload guard, isolates ragged rows to quarantine, encrypts file at rest.
    """
    content = await file.read()
    filename = file.filename or "unnamed_upload.csv"

    # 1. Run upload guard
    guard_report = guard.inspect_file(content, filename)
    if not guard_report.is_valid:
        # Audit guard rejection
        audit = AuditEvent(
            actor=current_user.email,
            event="UPLOAD_GUARD_REJECTION",
            details_json=f'{{"filename": "{filename}", "error": "{guard_report.error_code}"}}',
        )
        db.add(audit)
        db.commit()
        return UploadGuardResponse(
            is_valid=False,
            error_code=guard_report.error_code.value if guard_report.error_code else "UNKNOWN_ERROR",
            message=guard_report.message,
            quarantined_count=0,
        )

    # 2. Ingest valid rows and extract quarantine
    ingest_res = read_dataset_file(content, filename)
    sha256_orig = hashlib.sha256(content).hexdigest()
    canonical_hash_val = compute_canonical_hash(ingest_res.df)

    # 3. Encrypt and persist file to disk
    encrypted_bytes = encryptor.encrypt_bytes(content)
    storage_filename = f"{guard_report.storage_key}.enc"
    storage_path = settings.storage_path / "datasets"
    storage_path.mkdir(parents=True, exist_ok=True)
    full_path = storage_path / storage_filename
    full_path.write_bytes(encrypted_bytes)

    # 4. Save Dataset record
    dataset = Dataset(
        owner_id=current_user.id,
        original_filename_sanitized=guard_report.sanitized_filename,
        stored_path=str(full_path),
        sha256_original=sha256_orig,
        canonical_hash=canonical_hash_val,
        format=ingest_res.detected_format,
        rows=ingest_res.valid_rows,
        cols=len(ingest_res.original_columns),
        size_bytes=guard_report.file_size_bytes,
        encrypted=True,
    )
    db.add(dataset)
    db.flush()

    # 5. Save quarantine rows
    for q in ingest_res.quarantine:
        q_row = QuarantineRow(
            dataset_id=dataset.id,
            line_no=q.line_no,
            raw_text=q.raw_text,
            reason=q.reason,
        )
        db.add(q_row)

    # Audit event
    audit = AuditEvent(
        actor=current_user.email,
        event="DATASET_INGESTED",
        details_json=f'{{"dataset_id": "{dataset.id}", "rows": {dataset.rows}, "quarantined": {len(ingest_res.quarantine)}}}',
    )
    db.add(audit)
    db.commit()
    db.refresh(dataset)

    ds_resp = DatasetResponse(
        id=dataset.id,
        owner_id=dataset.owner_id,
        filename=dataset.original_filename_sanitized,
        sha256_original=dataset.sha256_original,
        canonical_hash=dataset.canonical_hash,
        format=dataset.format,
        rows=dataset.rows,
        cols=dataset.cols,
        size_bytes=dataset.size_bytes,
        created_at=dataset.created_at.isoformat(),
        quarantined_count=len(ingest_res.quarantine),
    )

    return UploadGuardResponse(
        is_valid=True,
        message="Dataset accepted and ingested securely",
        dataset=ds_resp,
        quarantined_count=len(ingest_res.quarantine),
        null_bytes_stripped=guard_report.null_bytes_stripped,
        formula_injection_cells_detected=ingest_res.formula_injection_count,
    )


@datasets_router.post("/demo", status_code=status.HTTP_201_CREATED)
def load_demo_dataset_for_datasets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Generates and loads the seeded dirty enterprise demo dataset."""
    from app.api.routes_admin import load_demo_dataset
    res = load_demo_dataset(current_user=current_user, db=db)
    dataset = db.query(Dataset).filter(Dataset.id == res["dataset_id"]).first()
    ds_resp = DatasetResponse(
        id=dataset.id,
        owner_id=dataset.owner_id,
        filename=dataset.original_filename_sanitized,
        sha256_original=dataset.sha256_original,
        canonical_hash=dataset.canonical_hash,
        format=dataset.format,
        rows=dataset.rows,
        cols=dataset.cols,
        size_bytes=dataset.size_bytes,
        created_at=dataset.created_at.isoformat(),
        quarantined_count=0,
    )
    return {"dataset": ds_resp, **res}


@datasets_router.get("", response_model=List[DatasetResponse])
def list_datasets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[DatasetResponse]:
    """Lists all datasets owned by current user (strict tenant isolation)."""
    datasets = db.query(Dataset).filter(Dataset.owner_id == current_user.id).order_by(Dataset.created_at.desc()).all()
    resp = []
    for d in datasets:
        resp.append(
            DatasetResponse(
                id=d.id,
                owner_id=d.owner_id,
                filename=d.original_filename_sanitized,
                sha256_original=d.sha256_original,
                canonical_hash=d.canonical_hash,
                format=d.format,
                rows=d.rows,
                cols=d.cols,
                size_bytes=d.size_bytes,
                created_at=d.created_at.isoformat(),
                quarantined_count=len(d.quarantine_rows),
            )
        )
    return resp


@datasets_router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DatasetResponse:
    """Retrieves dataset metadata if owned by current user."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.owner_id == current_user.id).first()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "DATASET_NOT_FOUND", "message": "Dataset not found"},
        )
    return DatasetResponse(
        id=dataset.id,
        owner_id=dataset.owner_id,
        filename=dataset.original_filename_sanitized,
        sha256_original=dataset.sha256_original,
        canonical_hash=dataset.canonical_hash,
        format=dataset.format,
        rows=dataset.rows,
        cols=dataset.cols,
        size_bytes=dataset.size_bytes,
        created_at=dataset.created_at.isoformat(),
        quarantined_count=len(dataset.quarantine_rows),
    )


@datasets_router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Deletes dataset, associated runs, and removes encrypted file on disk."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.owner_id == current_user.id).first()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "DATASET_NOT_FOUND", "message": "Dataset not found"},
        )
    # Remove file on disk
    try:
        p = Path(dataset.stored_path)
        if p.exists():
            p.unlink()
    except Exception:
        pass

    db.delete(dataset)
    db.commit()
