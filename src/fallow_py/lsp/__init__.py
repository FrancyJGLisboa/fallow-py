"""LSP server: publishes fallow-py findings as editor diagnostics.

The :class:`~fallow_py.issue.Issue`-to-LSP-Diagnostic mapping lives in
:mod:`fallow_py.lsp.diagnostics` as plain dicts (LSP wire shape) with no SDK
dependency, so it is unit-testable. :mod:`server` imports ``pygls`` lazily.
"""
