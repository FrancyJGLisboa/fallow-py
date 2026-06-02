"""One issue per line, grep-friendly: ``path:line:col: [kind] (severity) message``."""

from __future__ import annotations

from ..engine import AnalysisResult


def render(result: AnalysisResult) -> str:
    lines = []
    for i in result.issues:
        line = i.line if i.line is not None else 0
        col = i.column if i.column is not None else 0
        lines.append(f"{i.path}:{line}:{col}: [{i.kind}] ({i.severity}) {i.message}")
    return "\n".join(lines)
