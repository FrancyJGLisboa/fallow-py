"""ruff adapter: unused imports (F401).

Scoped to F401 with an explicit ``--select`` so the result is independent of the
target project's own ruff configuration — fallow-py is not a general ruff
wrapper; it surfaces the slop-relevant subset under one issue model.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from ..config import Config
from ..issue import UNUSED_IMPORT, Issue
from .base import AdapterOutcome, module_available, python_module_cmd, run

NAME = "ruff"

# ruff messages like "`os` imported but unused" -> pull the symbol name.
_BACKTICK = re.compile(r"`([^`]+)`")


def run_adapter(root: Path, config: Config, files=None) -> AdapterOutcome:
    if not config.is_enabled(UNUSED_IMPORT):
        return AdapterOutcome(NAME, "skipped", reason="unused-import is off")
    if not module_available("ruff"):
        return AdapterOutcome(NAME, "skipped", reason="ruff not installed")

    paths = [f.rel for f in (files or [])]
    if not paths:
        return AdapterOutcome(NAME, "skipped", reason="no source files")
    proc = run(
        python_module_cmd(
            "ruff", "check", "--output-format", "json", "--select", "F401", "--no-cache", *paths
        ),
        cwd=root,
    )
    try:
        findings = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        return AdapterOutcome(NAME, "error", reason=f"unparseable output: {exc}")

    sev = config.severity_for(UNUSED_IMPORT)
    issues: list[Issue] = []
    for f in findings:
        filename = f.get("filename", "")
        try:
            rel = os.path.relpath(filename, root)
        except ValueError:
            rel = filename
        loc = f.get("location") or {}
        message = f.get("message", "unused import")
        name = _BACKTICK.search(message)
        issues.append(
            Issue(
                kind=UNUSED_IMPORT,
                path=Path(rel).as_posix(),
                line=loc.get("row"),
                column=loc.get("column"),
                symbol=name.group(1) if name else None,
                message=message,
                severity=sev,
                detail={"tool": NAME, "code": f.get("code", "F401")},
            )
        )
    return AdapterOutcome(NAME, "ran", issues=issues)
