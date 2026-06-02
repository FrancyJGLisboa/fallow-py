"""Module-name computation and import resolution.

Python's import system, unlike Node's, is path + ``sys.path`` driven. We compute
each first-party file's dotted module name by walking up the ``__init__.py``
chain (so ``src/`` layout, flat layout, and namespace packages all work without
configuration), then resolve each :class:`ImportRef` to the first-party module
file(s) it targets. Stdlib and third-party imports are intentionally *not* part
of the internal graph (dependency hygiene is the deptry adapter's job).
"""

from __future__ import annotations

import sys
from pathlib import Path

from .extract import ImportRef
from .discover import SourceFile

_STDLIB = set(getattr(sys, "stdlib_module_names", frozenset()))


def module_name_for(path: Path) -> str:
    """Dotted module name, by walking up the ``__init__.py`` chain.

    ``pkg/sub/mod.py`` -> ``pkg.sub.mod``; ``pkg/sub/__init__.py`` -> ``pkg.sub``;
    a top-level ``run.py`` with no package -> ``run``.
    """
    parts: list[str] = []
    stem = path.stem
    if stem != "__init__":
        parts.append(stem)
    d = path.parent
    while (d / "__init__.py").exists():
        parts.append(d.name)
        d = d.parent
    parts.reverse()
    return ".".join(parts) if parts else stem


def is_package_init(path: Path) -> bool:
    return path.name == "__init__.py"


class Registry:
    """Maps dotted module names to first-party files and resolves imports."""

    def __init__(self, files: list[SourceFile]) -> None:
        self.files = files
        self.by_module: dict[str, SourceFile] = {}
        self.module_of: dict[str, str] = {}  # rel -> module name
        for f in files:
            mod = module_name_for(f.path)
            self.module_of[f.rel] = mod
            # First file wins on collision (path-sorted -> deterministic).
            self.by_module.setdefault(mod, f)

    def package_context(self, rel: str, path: Path) -> str:
        """The package a relative import is resolved against.

        For ``__init__.py`` it is the package itself; for a regular module it is
        the parent package.
        """
        mod = self.module_of[rel]
        if is_package_init(path):
            return mod
        return mod.rpartition(".")[0]

    def _resolve_relative(self, package_context: str, level: int, module: str | None) -> str:
        base_parts = package_context.split(".") if package_context else []
        # level 1 = current package, level 2 = parent, ...
        drop = level - 1
        if drop > 0:
            base_parts = base_parts[: len(base_parts) - drop] if drop <= len(base_parts) else []
        base = ".".join(base_parts)
        if module:
            return f"{base}.{module}" if base else module
        return base

    def resolve(
        self, rel: str, path: Path, imp: ImportRef
    ) -> tuple[list[str], bool]:
        """Resolve one import.

        Returns ``(target_module_names, is_internal)`` where target names are
        first-party modules that exist in the registry. ``is_internal`` is True
        when the import targets the project (even if a specific submodule could
        not be pinned down); used to distinguish unresolved-internal from
        third-party/stdlib.
        """
        if imp.level and imp.level > 0:
            ctx = self.package_context(rel, path)
            base = self._resolve_relative(ctx, imp.level, imp.module)
            return self._targets_for(base, imp), True

        assert imp.module is not None
        top = imp.module.split(".")[0]
        if top in _STDLIB:
            return [], False
        if top not in {m.split(".")[0] for m in self.by_module}:
            # Not a first-party top-level package -> third-party.
            return [], False
        return self._targets_for(imp.module, imp), True

    def _targets_for(self, base: str, imp: ImportRef) -> list[str]:
        """Given a resolved base module, pin the concrete first-party targets.

        ``from a.b import c`` may import submodule ``a.b.c`` or a name within
        ``a.b``; we edge to whichever module(s) actually exist.
        """
        targets: list[str] = []
        # The base itself, if it is a module.
        if base in self.by_module:
            targets.append(base)
        # Each from-imported name may itself be a submodule of base.
        if imp.names and not imp.is_star:
            for name in imp.names:
                candidate = f"{base}.{name}" if base else name
                if candidate in self.by_module:
                    targets.append(candidate)
        # Star import or plain ``import a.b.c``: also pull submodules under base
        # so a package import keeps its package __init__ reachable.
        if imp.is_star or not imp.names:
            if base in self.by_module:
                pass  # already added
        return targets

    def ancestor_packages(self, module: str) -> list[str]:
        """All existing ancestor ``__init__`` package modules of *module*.

        Importing a submodule executes every parent package ``__init__``, so a
        reachable module keeps its package inits reachable too.
        """
        out: list[str] = []
        parts = module.split(".")
        for i in range(1, len(parts)):
            anc = ".".join(parts[:i])
            if anc in self.by_module:
                out.append(anc)
        return out
