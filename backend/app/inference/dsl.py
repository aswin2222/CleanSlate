"""Fixed Domain-Specific Language (DSL) for CleanSlate Semantic Rules."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RuleKind(str, Enum):
    NOT_NULL = "not_null"
    UNIQUE = "unique"
    RANGE = "range"
    NON_NEGATIVE = "non_negative"
    ALLOWED_VALUES = "allowed_values"
    PATTERN = "pattern"
    TYPE = "type"
    DATE_ORDER = "date_order"
    ARITHMETIC = "arithmetic"
    FUNCTIONAL_DEPENDENCY = "functional_dependency"
    LENGTH = "length"
    NOT_FUTURE = "not_future"
    CROSS_FIELD_CONSISTENCY = "cross_field_consistency"
    REFERENTIAL = "referential"


class RuleStatus(str, Enum):
    ACTIVE = "active"
    NEEDS_REVIEW = "needs_review"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    REJECTED_BY_USER = "rejected_by_user"


class RuleSource(str, Enum):
    DETERMINISTIC = "deterministic"
    LLM = "llm"
    HEURISTIC = "heuristic"


@dataclass
class Rule:
    """
    Representation of a data integrity rule in CleanSlate DSL.
    Enforces strict typing and JSON serializability.
    """
    id: str
    kind: RuleKind
    columns: List[str]
    params: Dict[str, Any]
    support: float
    confidence: float
    evidence: str
    source: RuleSource
    status: RuleStatus
    violation_count: int = 0
    violating_rids: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        d["source"] = self.source.value
        d["status"] = self.status.value
        return d


# Built-in cross-field consistency table: Country code to Phone prefix
COUNTRY_PHONE_PREFIXES: Dict[str, str] = {
    "US": "+1",
    "USA": "+1",
    "CA": "+1",
    "CAN": "+1",
    "GB": "+44",
    "UK": "+44",
    "IN": "+91",
    "IND": "+91",
    "DE": "+49",
    "FR": "+33",
    "AU": "+61",
    "JP": "+81",
}
