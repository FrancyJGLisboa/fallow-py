"""Configuration loading.

Mirrors Fallow's config semantics: a ``rules`` map of kind -> severity
(``error`` | ``warn`` | ``off``), where severity drives the CI exit code, plus
ignore globs. No ``detect`` section, no ``output`` (format is CLI-only).

Sources, in precedence order:
  1. ``[tool.fallow_py]`` in ``pyproject.toml``
  2. ``.fallowrc.toml`` at the project root
Defaults fill anything unset.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path

from .issue import (
    ALL_KINDS,
    BOUNDARY_VIOLATION,
    CIRCULAR_DEPENDENCY,
    COMPLEXITY_HOTSPOT,
    SEVERITY_ERROR,
    SEVERITY_OFF,
    SEVERITY_WARN,
    UNLISTED_DEPENDENCY,
    UNRESOLVED_IMPORT,
    UNUSED_DEPENDENCY,
    UNUSED_MODULE,
)

# Default severity per kind. Native graph analyses default to error; adapter and
# convention-heavy analyses default to warn/off so the tool is quiet out of the box.
DEFAULT_RULES: dict[str, str] = {
    UNUSED_MODULE: SEVERITY_ERROR,
    CIRCULAR_DEPENDENCY: SEVERITY_ERROR,
    UNRESOLVED_IMPORT: SEVERITY_WARN,
    UNUSED_DEPENDENCY: SEVERITY_WARN,
    UNLISTED_DEPENDENCY: SEVERITY_WARN,
    COMPLEXITY_HOTSPOT: SEVERITY_OFF,
    BOUNDARY_VIOLATION: SEVERITY_OFF,
}

_VALID_SEVERITIES = {SEVERITY_ERROR, SEVERITY_WARN, SEVERITY_OFF}


@dataclass(frozen=True)
class Config:
    rules: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_RULES))
    # Extra ignore globs (on top of .gitignore), repo-relative.
    ignore: tuple[str, ...] = ()

    def severity_for(self, kind: str) -> str:
        return self.rules.get(kind, DEFAULT_RULES.get(kind, SEVERITY_ERROR))

    def is_enabled(self, kind: str) -> bool:
        return self.severity_for(kind) != SEVERITY_OFF


def _merge(base: Config, raw: dict) -> Config:
    rules = dict(base.rules)
    for kind, sev in (raw.get("rules") or {}).items():
        if kind not in ALL_KINDS:
            raise ValueError(f"unknown rule kind in config: {kind!r}")
        if sev not in _VALID_SEVERITIES:
            raise ValueError(
                f"invalid severity {sev!r} for {kind!r}; expected one of {sorted(_VALID_SEVERITIES)}"
            )
        rules[kind] = sev
    ignore = tuple(raw.get("ignore") or base.ignore)
    return replace(base, rules=rules, ignore=ignore)


def load_config(root: Path) -> Config:
    """Load config for the project rooted at *root*. Missing config -> defaults."""
    cfg = Config()

    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        tool = (data.get("tool") or {}).get("fallow_py")
        if isinstance(tool, dict):
            cfg = _merge(cfg, tool)

    rc = root / ".fallowrc.toml"
    if rc.is_file():
        cfg = _merge(cfg, tomllib.loads(rc.read_text(encoding="utf-8")))

    return cfg
