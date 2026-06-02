"""The unified issue model.

Field-for-field aligned with Fallow's (Rust) JSON issue model so the two
products share tooling, schemas, and CI integration. Every analysis — native
or adapter-sourced — emits this shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Issue kinds. Kebab-case, mirroring Fallow's vocabulary where the concept maps.
# Python's unit of reachability is the module, so we use ``unused-module`` rather
# than Fallow's ``unused-file``.
UNUSED_MODULE = "unused-module"
CIRCULAR_DEPENDENCY = "circular-dependency"
UNRESOLVED_IMPORT = "unresolved-import"
UNUSED_DEPENDENCY = "unused-dependency"
UNLISTED_DEPENDENCY = "unlisted-dependency"
COMPLEXITY_HOTSPOT = "complexity-hotspot"
BOUNDARY_VIOLATION = "boundary-violation"
STALE_SUPPRESSION = "stale-suppression"
# Intra-module slop (Phase 2b adapters): dead symbols inside a live module
# (vulture) and unused imports (ruff). The native engine works at module
# granularity, so these cover the most common AI-generated dead code.
DEAD_CODE = "dead-code"
UNUSED_IMPORT = "unused-import"

ALL_KINDS = (
    UNUSED_MODULE,
    CIRCULAR_DEPENDENCY,
    UNRESOLVED_IMPORT,
    UNUSED_DEPENDENCY,
    UNLISTED_DEPENDENCY,
    COMPLEXITY_HOTSPOT,
    BOUNDARY_VIOLATION,
    DEAD_CODE,
    UNUSED_IMPORT,
    STALE_SUPPRESSION,
)

# Severity resolved from config. "off" issues are never emitted.
SEVERITY_ERROR = "error"
SEVERITY_WARN = "warn"
SEVERITY_OFF = "off"


@dataclass(frozen=True)
class Issue:
    """A single finding. Immutable — analyses return new Issues, never mutate."""

    kind: str
    path: str  # repo-relative POSIX path
    message: str
    severity: str = SEVERITY_ERROR
    line: int | None = None
    column: int | None = None
    symbol: str | None = None
    # Extra structured payload (e.g. cycle member list, complexity score).
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "kind": self.kind,
            "path": self.path,
            "message": self.message,
            "severity": self.severity,
        }
        if self.line is not None:
            out["line"] = self.line
        if self.column is not None:
            out["column"] = self.column
        if self.symbol is not None:
            out["symbol"] = self.symbol
        if self.detail:
            out["detail"] = self.detail
        return out
