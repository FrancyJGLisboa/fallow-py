"""deptry adapter: dependency hygiene (unused / missing / transitive)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from ..config import Config
from ..issue import (
    UNLISTED_DEPENDENCY,
    UNUSED_DEPENDENCY,
    Issue,
)
from .base import AdapterOutcome, module_available, python_module_cmd, run

NAME = "deptry"

# deptry error codes -> our unified kinds.
#   DEP001 missing/undeclared, DEP003 transitive  -> should be declared (unlisted)
#   DEP002 unused/obsolete                          -> unused
#   DEP004 misplaced dev dependency                 -> treated as unused (mislisted)
_CODE_TO_KIND = {
    "DEP001": UNLISTED_DEPENDENCY,
    "DEP002": UNUSED_DEPENDENCY,
    "DEP003": UNLISTED_DEPENDENCY,
    "DEP004": UNUSED_DEPENDENCY,
}


def run_adapter(root: Path, config: Config) -> AdapterOutcome:
    relevant_kinds = {UNUSED_DEPENDENCY, UNLISTED_DEPENDENCY}
    if not any(config.is_enabled(k) for k in relevant_kinds):
        return AdapterOutcome(NAME, "skipped", reason="all dependency kinds are off")
    if not module_available("deptry"):
        return AdapterOutcome(NAME, "skipped", reason="deptry not installed")

    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "deptry.json"
        proc = run(
            python_module_cmd("deptry", ".", "--json-output", str(out_path)),
            cwd=root,
        )
        if not out_path.is_file():
            return AdapterOutcome(
                NAME, "error", reason=f"no output (exit {proc.returncode}): {proc.stderr.strip()[:200]}"
            )
        try:
            findings = json.loads(out_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            return AdapterOutcome(NAME, "error", reason=f"unparseable output: {exc}")

    issues: list[Issue] = []
    for f in findings:
        code = (f.get("error") or {}).get("code", "")
        kind = _CODE_TO_KIND.get(code)
        if kind is None or not config.is_enabled(kind):
            continue
        loc = f.get("location") or {}
        message = (f.get("error") or {}).get("message") or f"{code}: {f.get('module')}"
        issues.append(
            Issue(
                kind=kind,
                path=loc.get("file") or "pyproject.toml",
                line=loc.get("line"),
                column=loc.get("column"),
                symbol=f.get("module"),
                message=message,
                severity=config.severity_for(kind),
                detail={"tool": NAME, "code": code},
            )
        )
    return AdapterOutcome(NAME, "ran", issues=issues)
