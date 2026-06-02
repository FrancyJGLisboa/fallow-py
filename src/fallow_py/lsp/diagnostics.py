"""Pure Issue -> LSP Diagnostic mapping (LSP wire shape, no SDK types)."""

from __future__ import annotations

from collections import defaultdict

from ..issue import SEVERITY_ERROR, SEVERITY_WARN, Issue

# LSP DiagnosticSeverity: 1=Error 2=Warning 3=Information 4=Hint.
_LSP_SEVERITY = {SEVERITY_ERROR: 1, SEVERITY_WARN: 2}


def issue_to_diagnostic(issue: Issue) -> dict:
    """Map one Issue to an LSP Diagnostic dict.

    LSP positions are 0-based; our line numbers are 1-based and may be ``None``
    for module-level findings (which anchor at the top of the file).
    """
    line = (issue.line - 1) if issue.line else 0
    char = issue.column or 0
    return {
        "range": {
            "start": {"line": line, "character": char},
            "end": {"line": line, "character": char},
        },
        "severity": _LSP_SEVERITY.get(issue.severity, 3),
        "code": issue.kind,
        "source": "fallow-py",
        "message": issue.message,
    }


def diagnostics_by_path(issues: list[Issue]) -> dict[str, list[dict]]:
    """Group diagnostics by repo-relative path, for per-file publishing."""
    out: dict[str, list[dict]] = defaultdict(list)
    for issue in issues:
        out[issue.path].append(issue_to_diagnostic(issue))
    return dict(out)
