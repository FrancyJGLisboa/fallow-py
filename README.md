# fallow-py

Unified codebase intelligence for Python — the Python counterpart to
[Fallow](https://github.com/fallow-rs/fallow) (TypeScript/JavaScript).

Python already has excellent single-purpose tools (`ruff`, `vulture`, `deptry`,
`import-linter`, `radon`). fallow-py's wedge is the thing none of them do well:
**whole-project module reachability** — which modules are genuinely orphaned —
plus circular-dependency detection, built natively on the stdlib `ast` module,
unified under one issue model, one config, and one output/CI surface. Leaf
analyses are delegated to those mature tools via adapters (Phase 2).

## Status

**Phase 1 — native graph engine:** module reachability, circular dependencies,
unresolved internal imports. Framework-aware (Django, FastAPI, Flask, Celery,
pytest) so framework-dispatched code is not falsely flagged.

**Phase 2 — tool adapters:** dependency hygiene (`deptry`), complexity hotspots
(`radon`), architecture boundaries (`import-linter`), intra-module dead code
(`vulture`), and unused imports (`ruff`) are wrapped and mapped into the same
issue model. Adapters analyze exactly the file set the native engine discovered
(gitignore, venv, and `ignore`-config aware — they never crawl `.venv` or
site-packages). Each is optional — if its tool isn't installed, or its rule is
`off`, it's skipped and the reason is reported under `meta.adapters` (never a
silent gap). Install them with `pip install "fallow-py[adapters]"`.

**Phase 3 — integration surface:** a GitHub Action (SARIF → Code Scanning), an
MCP server (analysis exposed to AI agents over stdio), and an LSP server
(editor diagnostics). See below.

## Usage

```bash
pip install fallow-py
fallow-py                      # analyze the current directory (human output)
fallow-py path/to/project
fallow-py --format json
fallow-py --format sarif        # GitHub Code Scanning
fallow-py --only cycles
fallow-py --skip unresolved-imports
fallow-py --only dependencies          # deptry adapter only
```

Analyses selectable via `--only` / `--skip`: `unused-modules`, `cycles`,
`unresolved-imports` (native), and `dependencies`, `complexity`, `boundaries`,
`dead-code`, `unused-imports` (adapters). Note that selecting an adapter still
respects its rule severity — an adapter whose kinds are all `off` is skipped
regardless of `--only`. `complexity`, `boundaries`, and `dead-code` are `off` by
default (the last is FP-prone in dynamic code); enable them in config.

Exit code: `1` if any `error`-severity issue is found (CI gate), `0` otherwise.

## Configuration

In `pyproject.toml`:

```toml
[tool.fallow_py.rules]
unused-module       = "error"   # error | warn | off
circular-dependency = "error"
unresolved-import   = "warn"

[tool.fallow_py]
ignore = ["generated/**", "vendor/**"]
```

## Inline suppression

```python
# fallow-ignore-file unused-module
# fallow-ignore-next-line circular-dependency
```

## Integrations (Phase 3)

### GitHub Action

```yaml
# .github/workflows/fallow-py.yml — see examples/github-workflow.yml
permissions:
  contents: read
  security-events: write
jobs:
  fallow-py:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: FrancyJGLisboa/fallow-py@v0
        with:
          path: "."
          extras: "adapters"
          fail-on-error: "true"
```

Runs fallow-py, uploads SARIF to Code Scanning, and fails the job on
error-severity findings.

### MCP server (AI agents / Claude Code)

```bash
pip install "fallow-py[mcp]"
fallow-py-mcp           # stdio MCP server
```

Register it with Claude Code (user scope = available in every project):

```bash
claude mcp add fallow-py --scope user -- fallow-py-mcp
# pre-PyPI / from a local checkout, point at the venv binary:
# claude mcp add fallow-py --scope user -- /path/to/fallow-py/.venv/bin/fallow-py-mcp
```

Exposes two tools: `analyze(path, only?, skip?)` (returns the full JSON
envelope) and `list_analyses()`. Restart Claude Code after adding so it loads
the server.

### LSP server (editors)

```bash
pip install "fallow-py[lsp]"
fallow-py-lsp           # stdio LSP server
```

Re-analyzes the workspace on open/save and publishes findings as diagnostics
(`source: fallow-py`, `code:` the issue kind).

## Removing "slop" with Claude Code

fallow-py is built to surface AI-generated cruft and let an agent clean it up.
Coverage:

- **Structural slop** (default-on): orphaned modules, unused dependencies,
  unresolved/renamed imports, circular imports.
- **Intra-module slop** (opt-in): dead functions/classes/methods (`vulture`) and
  unused imports (`ruff`) — the most common AI dead code, invisible to the
  module-level engine.

Enable the dead-code sweep in the target project's `pyproject.toml`:

```toml
[tool.fallow_py.rules]
dead-code = "warn"   # vulture; off by default because it is FP-prone
```

Then point Claude Code at the MCP server (below) or run `fallow-py --format json`
and have it act on the findings. **fallow-py detects; it does not delete** —
removal is the agent's job, and in Python it must be verified, because dynamic
dispatch (decorators, string refs, registries) can make any dead-code tool
false-positive. A sound loop:

1. `dead-code` findings ≥ a confidence threshold (carried in `detail.confidence`).
2. Remove, then **run the test suite** — revert anything that breaks (the safety gate).
3. Re-run fallow-py until clean.

vulture is configured to ignore framework decorators (routes, signals, fixtures,
CLI commands), but residual false positives on framework classes (e.g. Django
models) are expected — always review before deleting.

## Why a module is considered "used"

A module is reachable if some **entry point** transitively imports it. Entry
points are: `[project.scripts]` / `[project.gui-scripts]` targets, `__main__.py`,
test files (pytest dispatches them), and framework roots contributed by plugins
(`manage.py`, `wsgi.py`/`asgi.py`, `main.py`/`app.py`, …). Framework convention
modules (Django `models.py`/`admin.py`/migrations, etc.) are treated as
always-used — favouring zero false positives over catching the rare dead
convention module.
