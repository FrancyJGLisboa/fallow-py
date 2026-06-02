"""Shared helpers for tool adapters.

Adapters subprocess a mature external tool, parse its machine-readable output,
and map findings into the unified :class:`Issue` model. Every adapter is
optional: if its tool is not importable, or its issue kinds are all ``off``, it
is skipped — and the skip reason is surfaced in ``meta`` so the omission is never
silent.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from dataclasses import dataclass, field

from ..issue import Issue


@dataclass
class AdapterOutcome:
    name: str
    status: str  # "ran" | "skipped" | "error"
    issues: list[Issue] = field(default_factory=list)
    reason: str | None = None

    def meta(self) -> dict:
        m = {"name": self.name, "status": self.status, "findings": len(self.issues)}
        if self.reason:
            m["reason"] = self.reason
        return m


def module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def run(args: list[str], cwd, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    """Run a subprocess, capturing text output. Never raises on non-zero exit."""
    return subprocess.run(
        args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def python_module_cmd(module: str, *args: str) -> list[str]:
    """``python -m <module> ...`` using the current interpreter (same venv)."""
    return [sys.executable, "-m", module, *args]
