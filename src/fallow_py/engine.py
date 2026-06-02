"""Pipeline orchestration: discover -> parse/extract -> resolve -> graph -> detect.

This is the top-level entry the CLI, and later the MCP/LSP servers, call into.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from . import analyze, suppress
from .adapters import ADAPTER_ANALYSES, run_adapters
from .config import Config
from .discover import discover
from .entry_points import discover_roots
from .extract import ModuleInfo, comment_lines, extract
from .graph import build_graph
from .issue import Issue
from .resolve import Registry

# Analyses selectable via --only / --skip.
NATIVE_ANALYSES = ("unused-modules", "cycles", "unresolved-imports")
ALL_ANALYSES = NATIVE_ANALYSES + ADAPTER_ANALYSES


@dataclass
class AnalysisResult:
    issues: list[Issue]
    meta: dict = field(default_factory=dict)

    @property
    def error_count(self) -> int:
        from .issue import SEVERITY_ERROR

        return sum(1 for i in self.issues if i.severity == SEVERITY_ERROR)


def _selected(name: str, only: frozenset[str], skip: frozenset[str]) -> bool:
    if only:
        return name in only
    return name not in skip


def analyze_project(
    root: Path,
    config: Config,
    only: frozenset[str] = frozenset(),
    skip: frozenset[str] = frozenset(),
) -> AnalysisResult:
    started = time.perf_counter()
    root = root.resolve()

    files = discover(root, config.ignore)
    registry = Registry(files)

    modinfos: dict[str, ModuleInfo] = {}
    suppressions: dict[str, suppress.FileSuppressions] = {}
    parse_errors: list[dict] = []
    for f in files:
        try:
            source = f.path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            parse_errors.append({"path": f.rel, "error": str(exc)})
            modinfos[f.rel] = ModuleInfo(rel=f.rel, parse_error=str(exc))
            continue
        info = extract(f.rel, source)
        modinfos[f.rel] = info
        if info.parse_error:
            parse_errors.append({"path": f.rel, "error": info.parse_error})
        suppressions[f.rel] = suppress.parse(comment_lines(source))

    roots = discover_roots(root, files, registry)
    graph = build_graph(files, modinfos, registry, roots)

    issues: list[Issue] = []
    if _selected("unused-modules", only, skip):
        issues += analyze.detect_unused_modules(
            graph, files, modinfos, roots, registry, config
        )
    if _selected("cycles", only, skip):
        issues += analyze.detect_cycles(graph, registry, config)
    if _selected("unresolved-imports", only, skip):
        issues += analyze.detect_unresolved_imports(graph, config)

    # Tool adapters (Phase 2): only the selected ones run; each reports its own
    # ran/skipped/error status into meta so omissions are never silent.
    selected_adapters = {a for a in ADAPTER_ANALYSES if _selected(a, only, skip)}
    adapter_issues, adapter_meta = run_adapters(root, config, selected_adapters, files)
    issues += adapter_issues

    issues = suppress.apply(issues, suppressions)
    issues.sort(key=lambda i: (i.path, i.line or 0, i.kind))

    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    meta = {
        "root": str(root),
        "files": len(files),
        "modules": len(registry.by_module),
        "entry_points": len(roots.entry),
        "always_used": len(roots.always_used),
        "plugins": list(roots.plugin_names),
        "dependencies": sorted(roots.deps),
        "adapters": adapter_meta,
        "parse_errors": parse_errors,
        "elapsed_ms": elapsed_ms,
    }
    return AnalysisResult(issues=issues, meta=meta)
