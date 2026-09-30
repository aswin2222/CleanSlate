"""Append-only Transformation Ledger for auditability and rollback execution."""
from __future__ import annotations

import json
import gzip
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

from app.config import settings
from app.transforms.base import Delta


@dataclass
class LedgerEntryRecord:
    id: str
    run_id: str
    seq: int
    step_id: str
    transformation: str
    params: Dict[str, Any]
    delta_ref: str
    hash_before: str
    hash_after: str
    predicted_loss: Dict[str, Any]
    actual_loss: Dict[str, Any]
    applied_at: str
    actor: str = "system"
    reverted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TransformationLedger:
    """
    Maintains an in-memory sequence of ledger entries and manages compressed
    delta persistence under storage/deltas/.
    """

    def __init__(self, run_id: str, storage_dir: Optional[Path] = None) -> None:
        self.run_id = run_id
        self.storage_dir = storage_dir or settings.storage_path / "deltas" / run_id
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.entries: List[LedgerEntryRecord] = []
        self._deltas_cache: Dict[str, Delta] = {}

    def append_entry(
        self,
        seq: int,
        step_id: str,
        transformation: str,
        params: Dict[str, Any],
        delta: Delta,
        hash_before: str,
        hash_after: str,
        predicted_loss: Dict[str, Any],
        actual_loss: Dict[str, Any],
        actor: str = "user",
    ) -> LedgerEntryRecord:
        """Appends a new entry to the immutable ledger and persists the compressed delta."""
        delta_id = f"delta_{seq}_{uuid.uuid4().hex[:8]}"
        delta_path = self.storage_dir / f"{delta_id}.json.gz"

        # Serialize delta to compressed JSON
        delta_dict = delta.to_dict()
        with gzip.open(delta_path, "wt", encoding="utf-8") as f:
            json.dump(delta_dict, f)

        # Cache delta in memory for fast rollback
        self._deltas_cache[delta_id] = delta

        entry = LedgerEntryRecord(
            id=f"ledger_{uuid.uuid4().hex[:8]}",
            run_id=self.run_id,
            seq=seq,
            step_id=step_id,
            transformation=transformation,
            params=params,
            delta_ref=delta_id,
            hash_before=hash_before,
            hash_after=hash_after,
            predicted_loss=predicted_loss,
            actual_loss=actual_loss,
            applied_at=datetime.now(timezone.utc).isoformat(),
            actor=actor,
            reverted=False,
        )

        self.entries.append(entry)
        return entry

    def get_delta(self, delta_ref: str) -> Optional[Delta]:
        """Retrieves Delta either from memory cache or decompresses from disk."""
        if delta_ref in self._deltas_cache:
            return self._deltas_cache[delta_ref]

        delta_path = self.storage_dir / f"{delta_ref}.json.gz"
        if not delta_path.exists():
            return None

        try:
            with gzip.open(delta_path, "rt", encoding="utf-8") as f:
                data = json.load(f)
                delta = Delta.from_dict(data)
                self._deltas_cache[delta_ref] = delta
                return delta
        except Exception:
            return None

    def get_latest_entry(self) -> Optional[LedgerEntryRecord]:
        unreverted = [e for e in self.entries if not e.reverted]
        return unreverted[-1] if unreverted else None

    def mark_reverted(self, seq: int) -> bool:
        for entry in self.entries:
            if entry.seq == seq:
                entry.reverted = True
                return True
        return False
