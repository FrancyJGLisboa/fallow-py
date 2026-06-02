"""vulture adapter: intra-module dead code (functions, classes, methods, vars).

This covers the most common form of AI-generated slop — dead symbols *inside* a
module that the native module-level engine cannot see. Unused *imports* are
deliberately skipped here because the ruff adapter reports them more reliably
(avoids double-reporting). vulture is heuristic in dynamic code, so confidence
is carried in ``detail`` for the consumer to threshold on.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..config import Config
from ..issue import DEAD_CODE, Issue
from .base import AdapterOutcome, module_available, python_module_cmd, run

NAME = "vulture"

# vulture default; findings below this are not reported at all.
_MIN_CONFIDENCE = 60

# Skip symbols dispatched by frameworks via decorators (routes, signals,
# fixtures, CLI commands, event hooks) — the main source of vulture false
# positives. Residual FPs (e.g. Django model classes, settings vars) are why
# dead-code is off by default and only ever a warning, never an error.
_IGNORE_DECORATORS = ",".join(
    [
        "@*.route", "@*.get", "@*.post", "@*.put", "@*.delete", "@*.patch",
        "@*.websocket", "@*.middleware", "@app.*", "@router.*",
        "@receiver", "@*.connect", "@*.fixture", "@pytest.*",
        "@*.command", "@*.task", "@*.on_event", "@*.callback", "@*.validator",
    ]
)

# e.g. "m.py:9: unused function 'dead_function' (60% confidence)"
_LINE = re.compile(r"^(?P<file>.+?):(?P<line>\d+): (?P<msg>.+?) \((?P<conf>\d+)% confidence\)$")
_NAMED = re.compile(r"unused \w+ '([^']+)'")


def run_adapter(root: Path, config: Config, files=None) -> AdapterOutcome:
    if not config.is_enabled(DEAD_CODE):
        return AdapterOutcome(NAME, "skipped", reason="dead-code is off")
    if not module_available("vulture"):
        return AdapterOutcome(NAME, "skipped", reason="vulture not installed")

    # Test files are dispatched by the runner; their test functions are not
    # "dead" — exclude them to avoid the dominant false-positive class.
    paths = [f.rel for f in (files or []) if not f.is_test]
    if not paths:
        return AdapterOutcome(NAME, "skipped", reason="no non-test source files")
    proc = run(
        python_module_cmd(
            "vulture",
            *paths,
            "--min-confidence",
            str(_MIN_CONFIDENCE),
            "--ignore-decorators",
            _IGNORE_DECORATORS,
        ),
        cwd=root,
    )
    sev = config.severity_for(DEAD_CODE)
    issues: list[Issue] = []
    for raw in proc.stdout.splitlines():
        m = _LINE.match(raw)
        if not m:
            continue
        msg = m.group("msg")
        if msg.startswith("unused import"):
            continue  # ruff adapter owns unused imports
        name_match = _NAMED.search(msg)
        rel = m.group("file").lstrip("./")
        issues.append(
            Issue(
                kind=DEAD_CODE,
                path=rel,
                line=int(m.group("line")),
                symbol=name_match.group(1) if name_match else None,
                message=f"{msg} ({m.group('conf')}% confidence)",
                severity=sev,
                detail={"tool": NAME, "confidence": int(m.group("conf"))},
            )
        )
    return AdapterOutcome(NAME, "ran", issues=issues)
