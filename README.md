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
(`radon`), and architecture boundaries (`import-linter`) are wrapped and mapped
into the same issue model. Each adapter is optional — if its tool isn't
installed, or its rule is `off`, it's skipped and the reason is reported under
`meta.adapters` (never a silent gap). Install them with
`pip install "fallow-py[adapters]"`.

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
`unresolved-imports` (native), and `dependencies`, `complexity`, `boundaries`
(adapters). Note that selecting an adapter still respects its rule severity — an
adapter whose kinds are all `off` is skipped regardless of `--only`.

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

### MCP server (AI agents)

```bash
pip install "fallow-py[mcp]"
fallow-py-mcp           # stdio MCP server
```

Exposes two tools: `analyze(path, only?, skip?)` (returns the full JSON
envelope) and `list_analyses()`. Point Claude Code or any MCP client at the
`fallow-py-mcp` command.

### LSP server (editors)

```bash
pip install "fallow-py[lsp]"
fallow-py-lsp           # stdio LSP server
```

Re-analyzes the workspace on open/save and publishes findings as diagnostics
(`source: fallow-py`, `code:` the issue kind).

## Why a module is considered "used"

A module is reachable if some **entry point** transitively imports it. Entry
points are: `[project.scripts]` / `[project.gui-scripts]` targets, `__main__.py`,
test files (pytest dispatches them), and framework roots contributed by plugins
(`manage.py`, `wsgi.py`/`asgi.py`, `main.py`/`app.py`, …). Framework convention
modules (Django `models.py`/`admin.py`/migrations, etc.) are treated as
always-used — favouring zero false positives over catching the rare dead
convention module.
