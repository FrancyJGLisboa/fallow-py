"""Machine-readable JSON envelope, shaped to match Fallow's contract."""

from __future__ import annotations

import json as _json

from .. import __version__
from ..engine import AnalysisResult
from ..issue import SEVERITY_ERROR, SEVERITY_WARN

SCHEMA_VERSION = 1


def build(result: AnalysisResult) -> dict:
    issues = [i.to_dict() for i in result.issues]
    summary = {
        "total": len(issues),
        "errors": sum(1 for i in result.issues if i.severity == SEVERITY_ERROR),
        "warnings": sum(1 for i in result.issues if i.severity == SEVERITY_WARN),
        "by_kind": _counts(result),
    }
    return {
        "kind": "analysis",
        "schema_version": SCHEMA_VERSION,
        "version": __version__,
        "summary": summary,
        "issues": issues,
        "meta": result.meta,
    }


def _counts(result: AnalysisResult) -> dict[str, int]:
    out: dict[str, int] = {}
    for i in result.issues:
        out[i.kind] = out.get(i.kind, 0) + 1
    return out


def render(result: AnalysisResult) -> str:
    return _json.dumps(build(result), indent=2, sort_keys=False)
