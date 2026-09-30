"""Rollback engine for exact inverse execution and canonical hash verification."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple
import pandas as pd

from app.execution.canonical_hash import compute_canonical_hash
from app.execution.ledger import TransformationLedger, LedgerEntryRecord
from app.logging import logger
from app.planning.registry import registry


@dataclass
class RollbackResult:
    success: bool
    restored_df: pd.DataFrame
    hash_original: str
    hash_current: str
    matches_original: bool
    reverted_steps_count: int
    message: str


class RollbackEngine:
    """
    Inverts transformations in reverse chronological sequence using ledger deltas.
    Validates canonical hash equality against original dataset state.
    """

    def __init__(self, ledger: TransformationLedger, original_hash: str) -> None:
        self.ledger = ledger
        self.original_hash = original_hash

    def rollback_latest_step(self, current_df: pd.DataFrame) -> Tuple[pd.DataFrame, Optional[LedgerEntryRecord]]:
        """Rolls back the latest unreverted step."""
        latest = self.ledger.get_latest_entry()
        if not latest:
            return current_df, None

        transform = registry.get(latest.transformation)
        if not transform:
            raise ValueError(f"Transformation '{latest.transformation}' not found for rollback")

        delta = self.ledger.get_delta(latest.delta_ref)
        if not delta:
            raise ValueError(f"Delta '{latest.delta_ref}' could not be loaded for rollback")

        # Invert step
        restored_df = transform.invert(current_df, delta)
        self.ledger.mark_reverted(latest.seq)

        return restored_df, latest

    def rollback_to(self, current_df: pd.DataFrame, target_seq: int) -> RollbackResult:
        """
        Rolls back all steps from the latest down to target_seq (inclusive).
        Inverts in strict reverse sequence.
        """
        df_work = current_df.copy()
        reverted_count = 0

        while True:
            latest = self.ledger.get_latest_entry()
            if not latest or latest.seq < target_seq:
                break

            df_work, entry = self.rollback_latest_step(df_work)
            reverted_count += 1

        curr_hash = compute_canonical_hash(df_work)
        matches = (curr_hash == self.original_hash)

        return RollbackResult(
            success=True,
            restored_df=df_work,
            hash_original=self.original_hash,
            hash_current=curr_hash,
            matches_original=matches,
            reverted_steps_count=reverted_count,
            message=f"Reverted {reverted_count} step(s). Current hash matches original: {matches}.",
        )

    def rollback_all(self, current_df: pd.DataFrame) -> RollbackResult:
        """
        Rolls back all applied transformations to the origin.
        Strict verification: canonical hash MUST equal original dataset hash.
        """
        res = self.rollback_to(current_df, target_seq=1)
        if not res.matches_original:
            logger.error(
                f"CRITICAL ROLLBACK MISMATCH: Original={self.original_hash} Restored={res.hash_current}"
            )
            res.message = "ALERT: Restored state does not match original canonical hash! Run marked corrupted."
        else:
            res.message = "100% CANONICAL MATCH: Restored state perfectly matches original upload."
        return res
