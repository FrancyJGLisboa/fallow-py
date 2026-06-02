"""Inline suppression, mirroring Fallow's syntax.

* ``# fallow-ignore-file [kind]``      — suppress *kind* for the whole file
* ``# fallow-ignore-next-line [kind]`` — suppress *kind* on the following line

Omitting ``[kind]`` suppresses every kind. A module-level finding (line ``None``,
e.g. ``unused-module``) is matched only by a file-level suppression.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .issue import Issue

_PATTERN = re.compile(r"fallow-ignore-(file|next-line)(?:\s+([\w-]+))?")
_WILDCARD = "*"


@dataclass(frozen=True)
class FileSuppressions:
    file_kinds: frozenset[str]  # kinds suppressed file-wide ("*" = all)
    line_kinds: dict[int, frozenset[str]]  # target line -> kinds ("*" = all)


def parse(comments: list[tuple[int, str]]) -> FileSuppressions:
    file_kinds: set[str] = set()
    line_kinds: dict[int, set[str]] = {}
    for lineno, text in comments:
        m = _PATTERN.search(text)
        if not m:
            continue
        scope, kind = m.group(1), (m.group(2) or _WILDCARD)
        if scope == "file":
            file_kinds.add(kind)
        else:  # next-line
            line_kinds.setdefault(lineno + 1, set()).add(kind)
    return FileSuppressions(
        file_kinds=frozenset(file_kinds),
        line_kinds={ln: frozenset(ks) for ln, ks in line_kinds.items()},
    )


def _suppressed(issue: Issue, supp: FileSuppressions) -> bool:
    if _WILDCARD in supp.file_kinds or issue.kind in supp.file_kinds:
        return True
    if issue.line is not None:
        kinds = supp.line_kinds.get(issue.line)
        if kinds and (_WILDCARD in kinds or issue.kind in kinds):
            return True
    return False


def apply(issues: list[Issue], by_file: dict[str, FileSuppressions]) -> list[Issue]:
    out: list[Issue] = []
    for issue in issues:
        supp = by_file.get(issue.path)
        if supp is not None and _suppressed(issue, supp):
            continue
        out.append(issue)
    return out
