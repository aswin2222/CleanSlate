"""Transformation Registry mapping rule violations and profile findings to transformations."""
from __future__ import annotations

from typing import Dict, List, Optional, Type
from app.transforms.base import Transformation
from app.transforms.missing import NormalizeMissingMarkers
from app.transforms.text import TrimWhitespace, NormalizeCase, NormalizePhone, RemoveJsonBrackets
from app.transforms.dates import StandardizeDates
from app.transforms.numeric import ParseNumeric
from app.transforms.dedupe import DedupeExact, DedupeFuzzy
from app.transforms.arithmetic import FixArithmetic
from app.transforms.outliers import CapOutliers
from app.transforms.impute import ImputeMedian, ImputeMode
from app.transforms.categories import MergeCategories
from app.transforms.drop_rows import DropRowsViolating, FlagOnly


class TransformationRegistry:
    """
    Central registry holding all allowlisted transformations.
    Guarantees Principle P1 & P2: No transformation may be applied unless
    registered with verified dry_run, apply, and invert.
    """

    def __init__(self) -> None:
        self._registry: Dict[str, Transformation] = {}
        self._register_defaults()

    def register(self, transform: Transformation) -> None:
        self._registry[transform.name] = transform

    def get(self, name: str) -> Optional[Transformation]:
        return self._registry.get(name)

    def list_all(self) -> List[Transformation]:
        return list(self._registry.values())

    def list_names(self) -> List[str]:
        return list(self._registry.keys())

    def _register_defaults(self) -> None:
        # All allowlisted transformations
        self.register(NormalizeMissingMarkers())
        self.register(TrimWhitespace())
        self.register(RemoveJsonBrackets())
        self.register(NormalizeCase())
        self.register(StandardizeDates())
        self.register(ParseNumeric())
        self.register(NormalizePhone())
        self.register(DedupeExact())
        self.register(DedupeFuzzy())
        self.register(FixArithmetic())
        self.register(CapOutliers())
        self.register(ImputeMedian())
        self.register(ImputeMode())
        self.register(MergeCategories())
        self.register(DropRowsViolating())
        self.register(FlagOnly())


# Global registry singleton
registry = TransformationRegistry()
