"""Output rendering. Format is a CLI concern only (never config)."""

from __future__ import annotations

from ..engine import AnalysisResult
from . import compact, human, json, markdown, sarif

FORMATS = ("human", "json", "sarif", "compact", "markdown")


def render(result: AnalysisResult, fmt: str, *, color: bool = True) -> str:
    if fmt == "human":
        return human.render(result, color=color)
    if fmt == "json":
        return json.render(result)
    if fmt == "sarif":
        return sarif.render(result)
    if fmt == "compact":
        return compact.render(result)
    if fmt == "markdown":
        return markdown.render(result)
    raise ValueError(f"unknown format: {fmt!r} (expected one of {FORMATS})")
