"""SARIF v2.1.0 output for GitHub Code Scanning and other SARIF consumers.

Hand-built dict — no heavy dependency, per the stdlib-first preference.
"""

from __future__ import annotations

import json as _json

from .. import __version__
from ..engine import AnalysisResult
from ..issue import ALL_KINDS, SEVERITY_ERROR, SEVERITY_WARN

_LEVEL = {SEVERITY_ERROR: "error", SEVERITY_WARN: "warning"}

_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
_INFO_URI = "https://github.com/FrancyJGLisboa/fallow-py"


def build(result: AnalysisResult) -> dict:
    rules = [{"id": kind, "name": kind} for kind in ALL_KINDS]
    results = []
    for issue in result.issues:
        region = {}
        if issue.line is not None:
            region["startLine"] = issue.line
        if issue.column is not None:
            region["startColumn"] = issue.column
        location = {
            "physicalLocation": {
                "artifactLocation": {"uri": issue.path},
                **({"region": region} if region else {}),
            }
        }
        results.append(
            {
                "ruleId": issue.kind,
                "level": _LEVEL.get(issue.severity, "note"),
                "message": {"text": issue.message},
                "locations": [location],
            }
        )
    return {
        "$schema": _SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "fallow-py",
                        "version": __version__,
                        "informationUri": _INFO_URI,
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }


def render(result: AnalysisResult) -> str:
    return _json.dumps(build(result), indent=2)
