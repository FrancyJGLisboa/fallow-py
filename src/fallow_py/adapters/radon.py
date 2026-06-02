"""radon adapter: cyclomatic-complexity hotspots."""

from __future__ import annotations

import json
from pathlib import Path

from ..config import Config
from ..issue import COMPLEXITY_HOTSPOT, Issue
from .base import AdapterOutcome, module_available, python_module_cmd, run

NAME = "radon"

# radon ranks: A (1-5) B (6-10) C (11-20) D (21-30) E (31-40) F (41+). We ask
# radon to emit only C and worse via ``-n C``, so every returned block is a
# genuine hotspot.
_MIN_RANK = "C"


def _blocks(entries: list) -> list[dict]:
    """Flatten radon's per-file entries, descending into class methods."""
    out: list[dict] = []
    for b in entries:
        if not isinstance(b, dict):
            continue
        out.append(b)
        out.extend(m for m in b.get("methods", []) if isinstance(m, dict))
    return out


def run_adapter(root: Path, config: Config, files=None) -> AdapterOutcome:
    if not config.is_enabled(COMPLEXITY_HOTSPOT):
        return AdapterOutcome(NAME, "skipped", reason="complexity-hotspot is off")
    if not module_available("radon"):
        return AdapterOutcome(NAME, "skipped", reason="radon not installed")

    paths = [f.rel for f in (files or [])]
    if not paths:
        return AdapterOutcome(NAME, "skipped", reason="no source files")
    # Pass the discovered files explicitly so radon does not crawl .venv etc.
    proc = run(python_module_cmd("radon", "cc", "--json", "-n", _MIN_RANK, *paths), cwd=root)
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        return AdapterOutcome(NAME, "error", reason=f"unparseable output: {exc}")

    sev = config.severity_for(COMPLEXITY_HOTSPOT)
    issues: list[Issue] = []
    for file, entries in data.items():
        if not isinstance(entries, list):
            continue  # radon emits an error object for unparseable files
        for b in _blocks(entries):
            name = b.get("name", "?")
            complexity = b.get("complexity")
            rank = b.get("rank")
            issues.append(
                Issue(
                    kind=COMPLEXITY_HOTSPOT,
                    path=file,
                    line=b.get("lineno"),
                    column=b.get("col_offset"),
                    symbol=name,
                    message=f"{b.get('type', 'block')} '{name}' has cyclomatic "
                    f"complexity {complexity} (rank {rank})",
                    severity=sev,
                    detail={"tool": NAME, "complexity": complexity, "rank": rank},
                )
            )
    return AdapterOutcome(NAME, "ran", issues=issues)
