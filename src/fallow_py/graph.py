"""The module graph: edges, reachability, and strongly-connected components.

These three algorithms are the genuinely language-neutral core of Fallow's
design. Reachability uses *augmented* edges (real imports plus synthetic
submodule->package-init edges, since importing a submodule executes its parent
``__init__``). Cycle detection uses *only* real import edges, so the synthetic
edges never manufacture a false cycle.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from .discover import SourceFile
from .entry_points import Roots
from .extract import ModuleInfo
from .resolve import Registry


@dataclass(frozen=True)
class UnresolvedImport:
    rel: str
    line: int
    target: str  # the import text that could not be resolved to a file


@dataclass
class ModuleGraph:
    rels: list[str]
    import_edges: dict[str, set[str]] = field(default_factory=dict)  # real imports
    aug_edges: dict[str, set[str]] = field(default_factory=dict)  # + ancestor inits
    unresolved: list[UnresolvedImport] = field(default_factory=list)

    def reachable_from(self, seeds: set[str]) -> set[str]:
        seen: set[str] = set()
        q: deque[str] = deque(s for s in seeds if s in self.aug_edges)
        seen.update(q)
        while q:
            node = q.popleft()
            for nxt in self.aug_edges.get(node, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    q.append(nxt)
        return seen

    def cycles(self) -> list[list[str]]:
        """Strongly-connected components with a real cycle (Tarjan, iterative)."""
        index: dict[str, int] = {}
        low: dict[str, int] = {}
        on_stack: set[str] = set()
        stack: list[str] = []
        counter = 0
        result: list[list[str]] = []

        for start in self.rels:
            if start in index:
                continue
            # Iterative Tarjan to avoid recursion limits on large graphs.
            work: list[tuple[str, int]] = [(start, 0)]
            while work:
                node, pi = work[-1]
                if pi == 0:
                    index[node] = low[node] = counter
                    counter += 1
                    stack.append(node)
                    on_stack.add(node)
                recursed = False
                succs = sorted(self.import_edges.get(node, ()))
                for j in range(pi, len(succs)):
                    w = succs[j]
                    if w not in index:
                        work[-1] = (node, j + 1)
                        work.append((w, 0))
                        recursed = True
                        break
                    if w in on_stack:
                        low[node] = min(low[node], index[w])
                if recursed:
                    continue
                if low[node] == index[node]:
                    comp: list[str] = []
                    while True:
                        w = stack.pop()
                        on_stack.discard(w)
                        comp.append(w)
                        if w == node:
                            break
                    if len(comp) > 1 or node in self.import_edges.get(node, ()):
                        result.append(sorted(comp))
                work.pop()
                if work:
                    parent = work[-1][0]
                    low[parent] = min(low[parent], low[node])
        return result


def build_graph(
    files: list[SourceFile],
    modinfos: dict[str, ModuleInfo],
    registry: Registry,
    roots: Roots,
) -> ModuleGraph:
    path_of: dict[str, Path] = {f.rel: f.path for f in files}
    rels = sorted(f.rel for f in files)

    g = ModuleGraph(rels=rels)
    for rel in rels:
        g.import_edges.setdefault(rel, set())
        g.aug_edges.setdefault(rel, set())

    for rel in rels:
        info = modinfos.get(rel)
        if info is None or info.parse_error is not None:
            continue
        path = path_of[rel]
        for imp in info.imports:
            targets, is_internal = registry.resolve(rel, path, imp)
            for mod in targets:
                sf = registry.by_module.get(mod)
                if sf is not None and sf.rel != rel:
                    g.import_edges[rel].add(sf.rel)
                    g.aug_edges[rel].add(sf.rel)
            if is_internal and not targets:
                text = _import_text(imp)
                g.unresolved.append(UnresolvedImport(rel=rel, line=imp.line, target=text))

        # Synthetic ancestor-package edges (reachability only).
        module = registry.module_of[rel]
        for anc in registry.ancestor_packages(module):
            sf = registry.by_module.get(anc)
            if sf is not None and sf.rel != rel:
                g.aug_edges[rel].add(sf.rel)

    return g


def _import_text(imp) -> str:  # noqa: ANN001 - small local helper
    dots = "." * imp.level
    base = imp.module or ""
    if imp.names and not imp.is_star:
        return f"from {dots}{base} import {', '.join(imp.names)}"
    if imp.is_star:
        return f"from {dots}{base} import *"
    return f"import {base}" if not imp.level else f"from {dots}{base}"
