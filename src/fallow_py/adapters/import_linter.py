"""import-linter adapter: architecture boundary contracts.

import-linter has no machine-readable output and requires user-defined
*contracts*, so this adapter is the thinnest of the three: it runs only when
contracts are configured, and parses the text report best-effort. Because
``boundary-violation`` defaults to ``off`` and contracts must be authored
explicitly, the brittleness here is low-risk.
"""

from __future__ import annotations

import re
import shutil
import sys
import tomllib
from pathlib import Path

from ..config import Config
from ..issue import BOUNDARY_VIOLATION, Issue
from .base import AdapterOutcome, module_available, run

NAME = "import-linter"

# A concrete violation line, e.g. "-   mypkg.a -> mypkg.b (l.3)". The leading
# bullet/indent varies, so we search rather than anchor.
_VIOLATION = re.compile(r"(\S+)\s*->\s*(\S+)\s*\(l\.(\d+)\)")


def _runner() -> list[str] | None:
    """Locate the ``lint-imports`` console script (no ``python -m`` entry exists).

    Prefer the script alongside the current interpreter (same venv) and run it
    via that interpreter, so it works regardless of whether the venv ``bin`` is
    on ``PATH``; fall back to ``PATH`` lookup.
    """
    local = Path(sys.executable).parent / "lint-imports"
    if local.exists():
        return [sys.executable, str(local)]
    found = shutil.which("lint-imports")
    return [found] if found else None


def _has_contracts(root: Path) -> bool:
    for fname in (".importlinter", "importlinter.ini", "setup.cfg"):
        if (root / fname).is_file():
            return True
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, OSError):
            return False
        return "importlinter" in (data.get("tool") or {})
    return False


def run_adapter(root: Path, config: Config, files=None) -> AdapterOutcome:
    # Contract-based and project-scoped; the discovered file list is not used.
    if not config.is_enabled(BOUNDARY_VIOLATION):
        return AdapterOutcome(NAME, "skipped", reason="boundary-violation is off")
    if not module_available("importlinter"):
        return AdapterOutcome(NAME, "skipped", reason="import-linter not installed")
    if not _has_contracts(root):
        return AdapterOutcome(NAME, "skipped", reason="no import-linter contracts configured")
    runner = _runner()
    if runner is None:
        return AdapterOutcome(NAME, "skipped", reason="lint-imports runner not found")

    proc = run(runner, cwd=root)
    sev = config.severity_for(BOUNDARY_VIOLATION)
    issues: list[Issue] = []
    for raw in proc.stdout.splitlines():
        m = _VIOLATION.search(raw)
        if m:
            src, dst, line = m.group(1), m.group(2), int(m.group(3))
            issues.append(
                Issue(
                    kind=BOUNDARY_VIOLATION,
                    path=src.replace(".", "/") + ".py",
                    line=line,
                    symbol=src,
                    message=f"{src} is not allowed to import {dst}",
                    severity=sev,
                    detail={"tool": NAME, "from": src, "to": dst},
                )
            )
    return AdapterOutcome(NAME, "ran", issues=issues)
