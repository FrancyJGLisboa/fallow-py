"""File discovery: walk the project for ``.py`` files, honouring ``.gitignore``.

Classifies each file as test vs source so downstream analyses can treat test
files as reachability roots (pytest dispatches them at runtime).
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path

import pathspec

# Directories never traversed regardless of .gitignore.
_HARD_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".tox",
    "build",
    "dist",
    ".eggs",
    "site-packages",
}

_TEST_NAME_GLOBS = ("test_*.py", "*_test.py", "conftest.py")
_TEST_DIR_NAMES = {"tests", "test"}


@dataclass(frozen=True)
class SourceFile:
    path: Path  # absolute, resolved
    rel: str  # repo-relative POSIX path
    is_test: bool


def _is_test(rel: str) -> bool:
    # Classify from the ROOT-RELATIVE path only. Using the absolute path would
    # misclassify every file under an ancestor dir named "tests" (e.g. a project
    # checked out below some .../tests/ directory).
    rel_path = Path(rel)
    if any(fnmatch.fnmatch(rel_path.name, g) for g in _TEST_NAME_GLOBS):
        return True
    return any(part in _TEST_DIR_NAMES for part in rel_path.parts)


def _load_gitignore(root: Path) -> pathspec.PathSpec | None:
    gi = root / ".gitignore"
    if not gi.is_file():
        return None
    return pathspec.PathSpec.from_lines("gitignore", gi.read_text(encoding="utf-8").splitlines())


def discover(root: Path, extra_ignore: tuple[str, ...] = ()) -> list[SourceFile]:
    """Return all analysable ``.py`` files under *root*, sorted by path.

    Sorting gives stable, reproducible file identity across runs (Fallow ADR-004).
    """
    root = root.resolve()
    spec = _load_gitignore(root)
    extra = (
        pathspec.PathSpec.from_lines("gitignore", extra_ignore) if extra_ignore else None
    )

    found: list[SourceFile] = []
    stack = [root]
    while stack:
        d = stack.pop()
        try:
            entries = list(d.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_symlink():
                continue
            if entry.is_dir():
                if entry.name in _HARD_SKIP_DIRS:
                    continue
                rel_dir = entry.relative_to(root).as_posix() + "/"
                if spec and spec.match_file(rel_dir):
                    continue
                if extra and extra.match_file(rel_dir):
                    continue
                stack.append(entry)
                continue
            if entry.suffix != ".py":
                continue
            rel = entry.relative_to(root).as_posix()
            if spec and spec.match_file(rel):
                continue
            if extra and extra.match_file(rel):
                continue
            found.append(SourceFile(path=entry.resolve(), rel=rel, is_test=_is_test(rel)))

    found.sort(key=lambda f: f.rel)
    return found
