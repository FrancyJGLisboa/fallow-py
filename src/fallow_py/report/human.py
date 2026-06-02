"""Human-friendly terminal output, grouped by kind."""

from __future__ import annotations

from collections import defaultdict

from ..engine import AnalysisResult
from ..issue import SEVERITY_ERROR, SEVERITY_WARN

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_GREEN = "\033[32m"
_CYAN = "\033[36m"


def _c(text: str, code: str, color: bool) -> str:
    return f"{code}{text}{_RESET}" if color else text


def render(result: AnalysisResult, *, color: bool = True) -> str:
    out: list[str] = []
    files = result.meta.get("files", 0)
    plugins = ", ".join(result.meta.get("plugins", [])) or "none"
    elapsed = result.meta.get("elapsed_ms", 0)
    out.append(
        _c("fallow-py", _BOLD, color)
        + _c(
            f"  ·  {files} files  ·  plugins: {plugins}  ·  {elapsed}ms",
            _DIM,
            color,
        )
    )

    if not result.issues:
        out.append("")
        out.append(_c("✓ No issues found.", _GREEN, color))
        return "\n".join(out)

    by_kind: dict[str, list] = defaultdict(list)
    for i in result.issues:
        by_kind[i.kind].append(i)

    for kind in sorted(by_kind):
        issues = by_kind[kind]
        out.append("")
        out.append(_c(f"{kind}", _BOLD, color) + _c(f"  ({len(issues)})", _DIM, color))
        for i in issues:
            mark = _severity_mark(i.severity, color)
            loc = i.path + (f":{i.line}" if i.line is not None else "")
            out.append(f"  {mark} {_c(loc, _CYAN, color)}")
            out.append(f"      {i.message}")

    errors = sum(1 for i in result.issues if i.severity == SEVERITY_ERROR)
    warnings = sum(1 for i in result.issues if i.severity == SEVERITY_WARN)
    out.append("")
    summary = f"{errors} error(s), {warnings} warning(s)"
    out.append(_c(summary, _RED if errors else _YELLOW, color))
    return "\n".join(out)


def _severity_mark(severity: str, color: bool) -> str:
    if severity == SEVERITY_ERROR:
        return _c("✗", _RED, color)
    if severity == SEVERITY_WARN:
        return _c("!", _YELLOW, color)
    return "·"
