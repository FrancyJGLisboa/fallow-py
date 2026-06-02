"""Native graph analyses (Tier 1): unused modules, cycles, unresolved imports."""

from __future__ import annotations

from ..config import Config
from ..discover import SourceFile
from ..entry_points import Roots
from ..extract import ModuleInfo
from ..graph import ModuleGraph
from ..issue import (
    CIRCULAR_DEPENDENCY,
    UNRESOLVED_IMPORT,
    UNUSED_MODULE,
    Issue,
)
from ..resolve import Registry


def detect_unused_modules(
    graph: ModuleGraph,
    files: list[SourceFile],
    modinfos: dict[str, ModuleInfo],
    roots: Roots,
    registry: Registry,
    config: Config,
) -> list[Issue]:
    if not config.is_enabled(UNUSED_MODULE):
        return []
    reachable = graph.reachable_from(set(roots.entry) | set(roots.always_used))
    sev = config.severity_for(UNUSED_MODULE)
    issues: list[Issue] = []
    for rel in graph.rels:
        if rel in reachable:
            continue
        info = modinfos.get(rel)
        if info is not None and info.parse_error is not None:
            continue  # can't trust import data for a file we couldn't parse
        module = registry.module_of.get(rel, rel)
        issues.append(
            Issue(
                kind=UNUSED_MODULE,
                path=rel,
                message=f"Module '{module}' is never imported from any entry point.",
                severity=sev,
                symbol=module,
                detail={"module": module},
            )
        )
    return issues


def detect_cycles(graph: ModuleGraph, registry: Registry, config: Config) -> list[Issue]:
    if not config.is_enabled(CIRCULAR_DEPENDENCY):
        return []
    sev = config.severity_for(CIRCULAR_DEPENDENCY)
    issues: list[Issue] = []
    for comp in graph.cycles():
        modules = [registry.module_of.get(rel, rel) for rel in comp]
        first = comp[0]
        issues.append(
            Issue(
                kind=CIRCULAR_DEPENDENCY,
                path=first,
                message="Circular import among: " + " ↔ ".join(sorted(modules)),
                severity=sev,
                detail={"members": sorted(modules), "paths": comp},
            )
        )
    return issues


def detect_unresolved_imports(graph: ModuleGraph, config: Config) -> list[Issue]:
    if not config.is_enabled(UNRESOLVED_IMPORT):
        return []
    sev = config.severity_for(UNRESOLVED_IMPORT)
    return [
        Issue(
            kind=UNRESOLVED_IMPORT,
            path=u.rel,
            line=u.line,
            message=f"Could not resolve internal import: {u.target}",
            severity=sev,
            detail={"target": u.target},
        )
        for u in graph.unresolved
    ]
