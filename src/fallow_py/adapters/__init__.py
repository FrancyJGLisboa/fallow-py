"""Tool adapters (Phase 2).

Each adapter wraps a mature single-purpose tool and maps its findings into the
unified issue model. Adapters are optional and self-describing: every run
reports, in ``meta.adapters``, whether each one ran, was skipped (and why), or
errored — so a missing tool or disabled rule is never a silent gap.
"""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..issue import Issue
from . import deptry, import_linter, radon
from .base import AdapterOutcome

# Adapter selection name -> module. Names join the native analyses for
# --only / --skip selection.
_ADAPTERS = {
    "dependencies": deptry,
    "complexity": radon,
    "boundaries": import_linter,
}

ADAPTER_ANALYSES = tuple(_ADAPTERS)


def run_adapters(
    root: Path,
    config: Config,
    selected: set[str],
) -> tuple[list[Issue], list[dict]]:
    """Run each selected adapter. *selected* is the set of adapter names to run."""
    issues: list[Issue] = []
    meta: list[dict] = []
    for name, module in _ADAPTERS.items():
        if name not in selected:
            continue
        try:
            outcome = module.run_adapter(root, config)
        except Exception as exc:  # an adapter crash must not abort the whole run
            outcome = AdapterOutcome(module.NAME, "error", reason=f"{type(exc).__name__}: {exc}")
        issues.extend(outcome.issues)
        meta.append(outcome.meta())
    return issues, meta
