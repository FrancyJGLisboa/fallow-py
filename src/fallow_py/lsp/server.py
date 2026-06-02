"""LSP server wiring. ``pygls`` / ``lsprotocol`` are imported lazily inside
``build_server`` so this module imports cleanly without the optional extra.

On document open and save, the whole workspace is (re)analyzed and diagnostics
are published per file. Re-analyzing the project on each save is acceptable for
typical projects (analysis is sub-second) and keeps cross-module findings —
unused modules, cycles — correct; incremental analysis is a later optimization.
"""

from __future__ import annotations

from pathlib import Path

from .. import __version__
from ..config import load_config
from ..engine import analyze_project
from .diagnostics import diagnostics_by_path


def build_server():
    try:
        from lsprotocol import types
        from pygls.lsp.server import LanguageServer  # pygls 2.x location
    except ImportError as exc:  # pragma: no cover - exercised only without extra
        raise RuntimeError(
            "the LSP server requires the 'lsp' extra: pip install 'fallow-py[lsp]'"
        ) from exc

    server = LanguageServer("fallow-py-lsp", __version__)

    def _to_diagnostic(d: dict):
        rng = d["range"]
        return types.Diagnostic(
            range=types.Range(
                start=types.Position(rng["start"]["line"], rng["start"]["character"]),
                end=types.Position(rng["end"]["line"], rng["end"]["character"]),
            ),
            message=d["message"],
            severity=types.DiagnosticSeverity(d["severity"]),
            code=d["code"],
            source=d["source"],
        )

    def _analyze_and_publish(ls) -> None:
        root_path = ls.workspace.root_path
        if not root_path:
            return
        root = Path(root_path)
        result = analyze_project(root, load_config(root))
        grouped = diagnostics_by_path(result.issues)
        # Clearing stale diagnostics for files that no longer have findings would
        # require tracking previously-published URIs; for the MVP we publish for
        # files with findings and rely on the client clearing on each full run.
        for rel, diags in grouped.items():
            uri = (root / rel).as_uri()
            ls.text_document_publish_diagnostics(
                types.PublishDiagnosticsParams(
                    uri=uri, diagnostics=[_to_diagnostic(d) for d in diags]
                )
            )

    @server.feature(types.TEXT_DOCUMENT_DID_OPEN)
    def did_open(ls, params):  # noqa: ARG001 - LSP callback signature
        _analyze_and_publish(ls)

    @server.feature(types.TEXT_DOCUMENT_DID_SAVE)
    def did_save(ls, params):  # noqa: ARG001 - LSP callback signature
        _analyze_and_publish(ls)

    return server


def main() -> None:
    build_server().start_io()


if __name__ == "__main__":
    main()
