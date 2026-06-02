"""Parse a Python source file and extract the metadata the graph needs.

Uses the stdlib ``ast`` module (zero dependencies, full semantic structure).
Comments are extracted separately via :mod:`tokenize` because ``ast`` discards
them — needed for inline suppressions.

Phase 1 consumes only imports (for the graph) and parse errors. Richer
extraction (``__all__``, decorators, ``INSTALLED_APPS`` string literals for
scoping convention globs to declared apps) is deliberately deferred until the
analysis that consumes it exists, so the model never implies capability it
does not yet have.
"""

from __future__ import annotations

import ast
import io
import tokenize
from dataclasses import dataclass


@dataclass(frozen=True)
class ImportRef:
    """One import statement's resolved intent.

    ``module`` is the dotted target as written (``None`` for ``from . import x``).
    ``level`` is the relative-import depth (0 = absolute). ``names`` are the
    imported member names for ``from`` imports (``["*"]`` for star imports).
    """

    module: str | None
    names: tuple[str, ...]
    level: int
    line: int
    is_star: bool = False


@dataclass(frozen=True)
class ModuleInfo:
    rel: str
    imports: tuple[ImportRef, ...] = ()
    parse_error: str | None = None


class _Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.imports: list[ImportRef] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(
                ImportRef(module=alias.name, names=(), level=0, line=node.lineno)
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        names = tuple(a.name for a in node.names)
        is_star = names == ("*",)
        self.imports.append(
            ImportRef(
                module=node.module,
                names=names,
                level=node.level or 0,
                line=node.lineno,
                is_star=is_star,
            )
        )


def extract(rel: str, source: str) -> ModuleInfo:
    try:
        tree = ast.parse(source, filename=rel)
    except SyntaxError as exc:
        return ModuleInfo(rel=rel, parse_error=f"{exc.msg} (line {exc.lineno})")

    v = _Visitor()
    v.visit(tree)
    return ModuleInfo(rel=rel, imports=tuple(v.imports))


def comment_lines(source: str) -> list[tuple[int, str]]:
    """Return ``(lineno, comment_text)`` for every comment, for suppression parsing."""
    out: list[tuple[int, str]] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.COMMENT:
                out.append((tok.start[0], tok.string))
    except (tokenize.TokenError, IndentationError):
        pass
    return out
