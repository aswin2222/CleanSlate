"""Transformation base class and atomic Delta representation."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from app.ingestion.rowid import ROW_ID_COL


@dataclass
class CellEdit:
    rid: int
    column: str
    old_value: str
    new_value: str


@dataclass
class DroppedRow:
    rid: int
    original_position: int
    data: Dict[str, str]


@dataclass
class AddedRow:
    rid: int
    original_position: int
    data: Dict[str, str]


@dataclass
class ColumnOp:
    op_type: str  # "add" | "drop" | "rename"
    column: str
    old_column: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Delta:
    """
    Atomic change set emitted by transformation execution.
    Contains everything necessary to reconstruct the EXACT prior state in reverse.
    """
    transformation: str
    cell_edits: List[CellEdit] = field(default_factory=list)
    dropped_rows: List[DroppedRow] = field(default_factory=list)
    added_rows: List[AddedRow] = field(default_factory=list)
    column_ops: List[ColumnOp] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transformation": self.transformation,
            "cell_edits": [asdict(e) for e in self.cell_edits],
            "dropped_rows": [asdict(r) for r in self.dropped_rows],
            "added_rows": [asdict(r) for r in self.added_rows],
            "column_ops": [asdict(c) for c in self.column_ops],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Delta:
        return cls(
            transformation=data.get("transformation", "unknown"),
            cell_edits=[CellEdit(**e) for e in data.get("cell_edits", [])],
            dropped_rows=[DroppedRow(**r) for r in data.get("dropped_rows", [])],
            added_rows=[AddedRow(**r) for r in data.get("added_rows", [])],
            column_ops=[ColumnOp(**c) for c in data.get("column_ops", [])],
            metadata=data.get("metadata", {}),
        )


@dataclass
class DryRunResult:
    rows_removed: int
    rows_removed_pct: float
    cells_modified: int
    cells_modified_pct: float
    non_null_cells_destroyed: int
    loss_score: float
    loss_label: str  # "LOW" | "MEDIUM" | "HIGH"
    human_summary: str
    column_metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PlanStep:
    id: str
    transformation: str
    params: Dict[str, Any]
    target_columns: List[str]
    rationale: str
    requires_approval: bool
    predicted_loss: DryRunResult
    rule_refs: List[str] = field(default_factory=list)
    seq: int = 0
    approved: bool = True
    status: str = "pending"  # "pending" | "approved" | "applied" | "skipped"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["loss_score"] = self.predicted_loss.loss_score
        d["loss_label"] = self.predicted_loss.loss_label
        return d


class Transformation(ABC):
    """
    Abstract Base Class for all CleanSlate transformations.
    Must implement:
      1. plan(df, params) -> PlanStep info
      2. dry_run(df, params) -> DryRunResult without modifying data
      3. apply(df, params) -> (new_df, Delta)
      4. invert(new_df, Delta) -> df
    """

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def plan(self, df: pd.DataFrame, params: Dict[str, Any]) -> PlanStep:
        pass

    @abstractmethod
    def dry_run(self, df: pd.DataFrame, params: Dict[str, Any]) -> DryRunResult:
        pass

    @abstractmethod
    def apply(self, df: pd.DataFrame, params: Dict[str, Any]) -> Tuple[pd.DataFrame, Delta]:
        pass

    @abstractmethod
    def invert(self, df: pd.DataFrame, delta: Delta) -> pd.DataFrame:
        pass
