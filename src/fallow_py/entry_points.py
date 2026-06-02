"""Entry-point and always-used discovery.

Entry points are reachability roots; always-used files are forced reachable.
Sources: ``pyproject.toml`` (project deps drive plugin activation; ``scripts`` /
``gui-scripts`` / ``entry-points`` name concrete root modules), test files
(pytest dispatches them), and active framework plugins.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

import pathspec

from .discover import SourceFile
from .plugins import active_plugins
from .resolve import Registry

_DEP_NAME = re.compile(r"^[A-Za-z0-9._-]+")


@dataclass(frozen=True)
class Roots:
    entry: frozenset[str]  # rel paths that are reachability roots
    always_used: frozenset[str]  # rel paths forced reachable
    deps: frozenset[str]  # declared project dependency names (for adapters)
    plugin_names: tuple[str, ...]


def _dep_name(spec: str) -> str | None:
    m = _DEP_NAME.match(spec.strip())
    return m.group(0).lower() if m else None


def _read_project(root: Path) -> dict:
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return {}
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return data.get("project") or {}


def _collect_deps(project: dict) -> set[str]:
    deps: set[str] = set()
    for spec in project.get("dependencies") or []:
        name = _dep_name(spec)
        if name:
            deps.add(name)
    for group in (project.get("optional-dependencies") or {}).values():
        for spec in group:
            name = _dep_name(spec)
            if name:
                deps.add(name)
    return deps


def _script_target_modules(project: dict) -> set[str]:
    """Module dotted-paths referenced by console/gui scripts and entry points."""
    mods: set[str] = set()
    for table_key in ("scripts", "gui-scripts"):
        for target in (project.get(table_key) or {}).values():
            # "pkg.module:func" -> "pkg.module"
            mods.add(target.split(":", 1)[0].strip())
    for group in (project.get("entry-points") or {}).values():
        for target in group.values():
            mods.add(target.split(":", 1)[0].strip())
    return mods


def _match(globs: tuple[str, ...], files: list[SourceFile]) -> set[str]:
    if not globs:
        return set()
    spec = pathspec.PathSpec.from_lines("gitignore", globs)
    return {f.rel for f in files if spec.match_file(f.rel)}


def discover_roots(root: Path, files: list[SourceFile], registry: Registry) -> Roots:
    project = _read_project(root)
    deps = _collect_deps(project)
    plugins = active_plugins(deps, files)

    entry: set[str] = set()
    always: set[str] = set()

    # 1. Test files are dispatched by the test runner.
    entry.update(f.rel for f in files if f.is_test)

    # 2. Script / entry-point target modules.
    script_mods = _script_target_modules(project)
    for mod in script_mods:
        sf = registry.by_module.get(mod)
        if sf is not None:
            entry.add(sf.rel)

    # 3. Plugin contributions.
    for p in plugins:
        entry.update(_match(p.entry_globs, files))
        always.update(_match(p.always_used_globs, files))

    # Always-used files should not also be reported as entries (entries are a
    # superset for reachability); keep them distinct only for clarity.
    return Roots(
        entry=frozenset(entry),
        always_used=frozenset(always),
        deps=frozenset(deps),
        plugin_names=tuple(p.name for p in plugins),
    )
