"""Markdown summary for PR/MR comments."""

from __future__ import annotations

from ..engine import AnalysisResult
from ..issue import SEVERITY_ERROR, SEVERITY_WARN


def render(result: AnalysisResult) -> str:
    errors = sum(1 for i in result.issues if i.severity == SEVERITY_ERROR)
    warnings = sum(1 for i in result.issues if i.severity == SEVERITY_WARN)

    out = ["## fallow-py"]
    if not result.issues:
        out.append("")
        out.append("No issues found. ✅")
        return "\n".join(out)

    out.append("")
    out.append(f"**{errors} error(s), {warnings} warning(s)** across {result.meta.get('files', 0)} files.")
    out.append("")
    out.append("| Severity | Kind | Location | Message |")
    out.append("| --- | --- | --- | --- |")
    for i in result.issues:
        loc = i.path + (f":{i.line}" if i.line is not None else "")
        msg = i.message.replace("|", "\\|")
        out.append(f"| {i.severity} | `{i.kind}` | `{loc}` | {msg} |")
    return "\n".join(out)
