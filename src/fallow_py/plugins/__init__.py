"""Framework plugins.

A plugin's job is to teach the reachability pass about code that frameworks
dispatch at runtime — invisible to static import analysis. It does so by
contributing:

* **entry globs** — files that are reachability roots (e.g. ``manage.py``);
* **always-used globs** — files the framework loads by convention and that must
  never be flagged unused (e.g. Django ``models.py`` / ``admin.py``).

The policy is deliberately conservative: when a framework is present we favour
marking convention files used (zero false positives) over catching the rare
genuinely-dead convention module. That tradeoff is the make-or-break metric.
"""

from __future__ import annotations

from .base import Plugin, active_plugins

__all__ = ["Plugin", "active_plugins"]
