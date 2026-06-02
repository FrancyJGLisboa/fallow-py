"""MCP server: exposes fallow-py's analysis to AI agents over stdio.

The analysis logic lives in :mod:`fallow_py.mcp.core` and imports no MCP SDK, so
it is unit-testable without the optional ``mcp`` dependency. :mod:`server`
imports the SDK lazily (only when the server is actually launched).
"""
