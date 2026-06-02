"""Command-line interface (stdlib ``argparse``)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, report
from .config import load_config
from .engine import ALL_ANALYSES, analyze_project


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="fallow-py",
        description="Unified codebase intelligence for Python: module reachability, "
        "circular dependencies, and import hygiene.",
    )
    p.add_argument("path", nargs="?", default=".", help="project root (default: .)")
    p.add_argument(
        "--format",
        "-f",
        default="human",
        choices=report.FORMATS,
        help="output format (default: human)",
    )
    p.add_argument(
        "--only",
        default="",
        help=f"comma-separated analyses to run (of: {', '.join(ALL_ANALYSES)})",
    )
    p.add_argument("--skip", default="", help="comma-separated analyses to skip")
    p.add_argument("--no-color", action="store_true", help="disable ANSI colour")
    p.add_argument("--version", "-V", action="version", version=f"fallow-py {__version__}")
    return p


def _split(csv: str) -> frozenset[str]:
    return frozenset(s.strip() for s in csv.split(",") if s.strip())


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    root = Path(args.path)
    if not root.is_dir():
        print(f"fallow-py: not a directory: {root}", file=sys.stderr)
        return 2

    try:
        config = load_config(root)
    except ValueError as exc:
        print(f"fallow-py: config error: {exc}", file=sys.stderr)
        return 2

    only, skip = _split(args.only), _split(args.skip)
    unknown = (only | skip) - set(ALL_ANALYSES)
    if unknown:
        print(
            f"fallow-py: unknown analysis name(s): {', '.join(sorted(unknown))}",
            file=sys.stderr,
        )
        return 2

    result = analyze_project(root, config, only=only, skip=skip)

    color = (not args.no_color) and sys.stdout.isatty()
    print(report.render(result, args.format, color=color))

    # Errors fail CI (exit 1); warnings do not (exit 0). Internal errors -> 2.
    return 1 if result.error_count > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
