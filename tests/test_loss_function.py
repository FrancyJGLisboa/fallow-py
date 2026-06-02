"""The MVP loss function: six binary checks that gate shippability.

Each test maps to one numbered criterion in the plan. The Django/FastAPI
zero-false-positive checks (#1) are the make-or-break gate — they decide whether
the tool is usable or just another noisy linter people disable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fallow_py.adapters.base import module_available
from fallow_py.config import load_config
from fallow_py.engine import ADAPTER_ANALYSES, analyze_project
from fallow_py.issue import (
    BOUNDARY_VIOLATION,
    CIRCULAR_DEPENDENCY,
    COMPLEXITY_HOTSPOT,
    DEAD_CODE,
    UNUSED_DEPENDENCY,
    UNUSED_IMPORT,
    UNUSED_MODULE,
)
from fallow_py.report import json as json_report
from fallow_py.report import sarif as sarif_report

FIX = Path(__file__).parent / "fixtures"


def _analyze(name: str):
    """Analyze a fixture with adapters skipped — these tests exercise the native
    graph engine only, so they stay fast and independent of external tools."""
    root = FIX / name
    return analyze_project(root, load_config(root), skip=frozenset(ADAPTER_ANALYSES))


def _kinds(result, kind):
    return [i for i in result.issues if i.kind == kind]


# --- Loss-fn #1: zero false positives on framework-dispatched code (THE gate) ---


_DJANGO_CONVENTION_MODULES = {
    "blog/models.py",
    "blog/admin.py",
    "blog/apps.py",
    "blog/views.py",
    "blog/signals.py",
    "blog/migrations/0001_initial.py",
    "myproject/settings.py",
    "myproject/urls.py",
    "myproject/wsgi.py",
}


def test_django_convention_modules_not_flagged():
    """Framework-dispatched convention modules must be quiet (the FP gate)."""
    result = _analyze("django_app")
    assert "django" in result.meta["plugins"]
    unused = {i.path for i in _kinds(result, UNUSED_MODULE)}
    leaked = unused & _DJANGO_CONVENTION_MODULES
    assert not leaked, f"convention modules wrongly flagged: {sorted(leaked)}"


def test_django_genuinely_dead_module_flagged():
    """The discriminating check: a non-convention orphan in a live app MUST be
    flagged. Without this, an active plugin would prove only that the globs are
    broad — not that the engine still finds orphans (the product's wedge)."""
    result = _analyze("django_app")
    unused = {i.path for i in _kinds(result, UNUSED_MODULE)}
    assert "blog/dead_helpers.py" in unused, (
        "engine went blind: a dead, non-convention module in a Django app was not "
        f"flagged. Flagged set: {sorted(unused)}"
    )


def test_fastapi_zero_false_positives():
    result = _analyze("fastapi_app")
    unused = _kinds(result, UNUSED_MODULE)
    assert unused == [], f"FastAPI routers must not be flagged; got: {[i.path for i in unused]}"
    assert "fastapi" in result.meta["plugins"]


# --- Loss-fn #2: true-positive orphan ---


def test_orphan_module_flagged():
    result = _analyze("orphan")
    unused = {i.path for i in _kinds(result, UNUSED_MODULE)}
    assert unused == {"orphaned.py"}, f"expected only orphaned.py, got {unused}"


# --- Loss-fn #3: true-positive cycle ---


def test_cycle_detected():
    result = _analyze("cyclic")
    cycles = _kinds(result, CIRCULAR_DEPENDENCY)
    assert len(cycles) == 1, f"expected exactly one cycle, got {len(cycles)}"
    assert cycles[0].detail["members"] == ["a", "b"]
    # The entry point reaches both, so nothing is orphaned.
    assert _kinds(result, UNUSED_MODULE) == []


# --- Loss-fn #4: performance on a ~1k-file tree ---


def test_performance_1k_files(tmp_path: Path):
    pkg = tmp_path / "bigpkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    n = 1000
    # A linear import chain rooted at __main__ so every module is reachable.
    (pkg / "__main__.py").write_text("from bigpkg import mod0\n")
    for i in range(n):
        nxt = f"from bigpkg import mod{i + 1}\n" if i + 1 < n else ""
        (pkg / f"mod{i}.py").write_text(f"{nxt}value = {i}\n")

    result = analyze_project(tmp_path, load_config(tmp_path))
    assert result.meta["files"] >= n
    assert result.meta["elapsed_ms"] < 8000, f"too slow: {result.meta['elapsed_ms']}ms"


# --- Loss-fn #5: output contract (JSON envelope + SARIF shape) ---


def test_json_envelope_contract():
    result = _analyze("orphan")
    env = json_report.build(result)
    for key in ("kind", "schema_version", "version", "summary", "issues", "meta"):
        assert key in env, f"missing top-level key: {key}"
    assert env["kind"] == "analysis"
    assert set(env["summary"]) >= {"total", "errors", "warnings", "by_kind"}
    issue = env["issues"][0]
    for key in ("kind", "path", "message", "severity"):
        assert key in issue


def test_sarif_shape():
    result = _analyze("orphan")
    doc = sarif_report.build(result)
    assert doc["version"] == "2.1.0"
    assert doc["runs"][0]["tool"]["driver"]["name"] == "fallow-py"
    res = doc["runs"][0]["results"]
    assert res and res[0]["ruleId"] == UNUSED_MODULE
    assert res[0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "orphaned.py"


# --- Loss-fn #6: adapters map into the unified model (Phase 2) ---


@pytest.mark.skipif(not module_available("deptry"), reason="deptry not installed")
def test_deptry_adapter_unified():
    """A declared-but-unused dependency surfaces as a unified unused-dependency
    Issue carrying the tool provenance — not as raw deptry output."""
    root = FIX / "deps_fixture"
    result = analyze_project(root, load_config(root), only=frozenset({"dependencies"}))

    deps = [i for i in result.issues if i.kind == UNUSED_DEPENDENCY]
    assert any(i.symbol == "pathspec" for i in deps), (
        f"expected unused-dependency for 'pathspec'; got {[(i.kind, i.symbol) for i in result.issues]}"
    )
    flagged = next(i for i in deps if i.symbol == "pathspec")
    assert flagged.detail.get("tool") == "deptry"
    assert flagged.detail.get("code") == "DEP002"

    # The adapter records its provenance in meta (no silent gaps).
    names = {a["name"]: a for a in result.meta["adapters"]}
    assert names["deptry"]["status"] == "ran"


def test_disabled_adapter_is_skipped_with_reason():
    """An adapter whose kinds are all 'off' must be skipped, and say so."""
    root = FIX / "deps_fixture"
    # complexity-hotspot defaults to "off" -> radon must skip, not run.
    result = analyze_project(root, load_config(root), only=frozenset({"complexity"}))
    radon_meta = next(a for a in result.meta["adapters"] if a["name"] == "radon")
    assert radon_meta["status"] == "skipped"
    assert "off" in radon_meta["reason"]


@pytest.mark.skipif(not module_available("radon"), reason="radon not installed")
def test_radon_adapter_unified():
    root = FIX / "complexity_fixture"
    result = analyze_project(root, load_config(root), only=frozenset({"complexity"}))
    hotspots = [i for i in result.issues if i.kind == COMPLEXITY_HOTSPOT]
    assert any(i.symbol == "tangled" for i in hotspots), (
        f"expected a complexity hotspot for 'tangled'; got {[i.symbol for i in hotspots]}"
    )
    spot = next(i for i in hotspots if i.symbol == "tangled")
    assert spot.detail["tool"] == "radon"
    assert spot.detail["complexity"] >= 11  # rank C or worse


@pytest.mark.skipif(not module_available("vulture"), reason="vulture not installed")
def test_vulture_adapter_finds_intramodule_dead_code():
    """The slop gap-closer: a dead function inside a *reachable* module must be
    flagged (the native engine works at module granularity and cannot see this)."""
    root = FIX / "slop_fixture"
    result = analyze_project(root, load_config(root), only=frozenset({"dead-code"}))
    dead = [i for i in result.issues if i.kind == DEAD_CODE]
    assert any(i.symbol == "dead_function" for i in dead), (
        f"expected dead_function; got {[i.symbol for i in dead]}"
    )
    spot = next(i for i in dead if i.symbol == "dead_function")
    assert spot.detail["tool"] == "vulture"
    assert "confidence" in spot.detail
    # vulture must NOT report unused imports — that is the ruff adapter's job.
    assert not any("import" in i.message for i in dead)


@pytest.mark.skipif(not module_available("ruff"), reason="ruff not installed")
def test_ruff_adapter_finds_unused_imports():
    root = FIX / "slop_fixture"
    result = analyze_project(root, load_config(root), only=frozenset({"unused-imports"}))
    unused = [i for i in result.issues if i.kind == UNUSED_IMPORT]
    assert any(i.symbol == "json" for i in unused), (
        f"expected unused import 'json'; got {[i.symbol for i in unused]}"
    )
    assert unused[0].detail["tool"] == "ruff"


@pytest.mark.skipif(not module_available("importlinter"), reason="import-linter not installed")
def test_import_linter_adapter_unified():
    """The brittle text-parse adapter: a broken forbidden-import contract must
    surface as a unified boundary-violation with from/to provenance."""
    root = FIX / "boundaries_fixture"
    result = analyze_project(root, load_config(root), only=frozenset({"boundaries"}))
    violations = [i for i in result.issues if i.kind == BOUNDARY_VIOLATION]
    assert any(
        i.detail.get("from") == "myproj.a" and i.detail.get("to") == "myproj.b"
        for i in violations
    ), f"expected myproj.a -> myproj.b violation; got {[i.detail for i in violations]}"
    assert violations[0].detail["tool"] == "import-linter"
