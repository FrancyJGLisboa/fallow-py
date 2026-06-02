"""MCP server wiring. The ``mcp`` SDK is imported lazily inside ``build_server``
so this module imports cleanly even when the optional dependency is absent."""

from __future__ import annotations

from ..engine import ALL_ANALYSES
from .core import analyze_dict


def build_server():
    """Construct the FastMCP server with tools registered (does not run it)."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - exercised only without extra
        raise RuntimeError(
            "the MCP server requires the 'mcp' extra: pip install 'fallow-py[mcp]'"
        ) from exc

    server = FastMCP("fallow-py")

    @server.tool()
    def analyze(
        path: str = ".",
        only: list[str] | None = None,
        skip: list[str] | None = None,
    ) -> dict:
        """Analyze a Python project for unused modules, circular dependencies,
        unresolved imports, and (when enabled) dependency/complexity/boundary
        issues. Returns the full JSON envelope: summary counts, the issue list,
        and run metadata (files, active plugins, adapter statuses).

        Args:
            path: Project root to analyze (default: current directory).
            only: Restrict to these analyses (subset of list_analyses()).
            skip: Exclude these analyses.
        """
        return analyze_dict(path, only, skip)

    @server.tool()
    def list_analyses() -> list[str]:
        """List the analysis names accepted by analyze()'s only/skip arguments."""
        return list(ALL_ANALYSES)

    return server


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
