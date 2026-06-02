"""Phase 3 integration surface: MCP core, LSP diagnostics mapping, server builds.

The SDK-free helpers (MCP analyze_dict, LSP diagnostic mapping) are always
tested. The server constructors are tested only when their optional extra is
installed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fallow_py.adapters.base import module_available
from fallow_py.engine import ADAPTER_ANALYSES
from fallow_py.issue import (
    SEVERITY_ERROR,
    SEVERITY_WARN,
    UNUSED_MODULE,
    Issue,
)
from fallow_py.lsp.diagnostics import diagnostics_by_path, issue_to_diagnostic
from fallow_py.mcp.core import analyze_dict

FIX = Path(__file__).parent / "fixtures"


# --- MCP core (SDK-free) ---


def test_mcp_analyze_dict_returns_envelope():
    env = analyze_dict(str(FIX / "orphan"), skip=list(ADAPTER_ANALYSES))
    assert env["kind"] == "analysis"
    flagged = {i["path"] for i in env["issues"] if i["kind"] == UNUSED_MODULE}
    assert "orphaned.py" in flagged


def test_mcp_analyze_dict_rejects_unknown_analysis():
    with pytest.raises(ValueError):
        analyze_dict(str(FIX / "orphan"), only=["bogus"])


def test_mcp_analyze_dict_rejects_bad_path(tmp_path: Path):
    with pytest.raises(NotADirectoryError):
        analyze_dict(str(tmp_path / "does-not-exist"))


# --- LSP diagnostic mapping (SDK-free) ---


def test_lsp_error_mapping_is_zero_based():
    issue = Issue(
        kind=UNUSED_MODULE, path="m.py", message="x", severity=SEVERITY_ERROR, line=5, column=2
    )
    d = issue_to_diagnostic(issue)
    assert d["severity"] == 1  # LSP Error
    assert d["range"]["start"] == {"line": 4, "character": 2}  # 1-based -> 0-based
    assert d["source"] == "fallow-py"
    assert d["code"] == UNUSED_MODULE


def test_lsp_module_level_issue_anchors_at_top():
    issue = Issue(kind=UNUSED_MODULE, path="m.py", message="x", severity=SEVERITY_WARN, line=None)
    d = issue_to_diagnostic(issue)
    assert d["severity"] == 2  # LSP Warning
    assert d["range"]["start"]["line"] == 0


def test_lsp_diagnostics_grouped_by_path():
    issues = [
        Issue(UNUSED_MODULE, "a.py", "x"),
        Issue(UNUSED_MODULE, "b.py", "y"),
        Issue(UNUSED_MODULE, "a.py", "z"),
    ]
    grouped = diagnostics_by_path(issues)
    assert set(grouped) == {"a.py", "b.py"}
    assert len(grouped["a.py"]) == 2


# --- Server constructors (need the optional extras) ---


@pytest.mark.skipif(not module_available("mcp"), reason="mcp extra not installed")
def test_mcp_server_builds():
    from fallow_py.mcp.server import build_server

    assert build_server() is not None


@pytest.mark.skipif(not module_available("pygls"), reason="lsp extra not installed")
def test_lsp_server_builds():
    from fallow_py.lsp.server import build_server

    assert build_server() is not None
