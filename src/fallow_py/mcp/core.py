"""SDK-free analysis entry used by the MCP tools (and unit tests)."""

from __future__ import annotations

from pathlib import Path

from ..config import load_config
from ..engine import ALL_ANALYSES, analyze_project
from ..report import json as json_report


def analyze_dict(
    path: str = ".",
    only: list[str] | None = None,
    skip: list[str] | None = None,
) -> dict:
    """Analyze a project and return the JSON envelope as a plain dict.

    *only* / *skip* are analysis names (see :data:`ALL_ANALYSES`). Unknown names
    are rejected so an agent gets a clear error rather than a silent no-op.
    """
    requested = set(only or []) | set(skip or [])
    unknown = requested - set(ALL_ANALYSES)
    if unknown:
        raise ValueError(
            f"unknown analysis name(s): {sorted(unknown)}; valid: {list(ALL_ANALYSES)}"
        )

    root = Path(path)
    if not root.is_dir():
        raise NotADirectoryError(f"not a directory: {path}")

    result = analyze_project(
        root,
        load_config(root),
        only=frozenset(only or []),
        skip=frozenset(skip or []),
    )
    return json_report.build(result)
