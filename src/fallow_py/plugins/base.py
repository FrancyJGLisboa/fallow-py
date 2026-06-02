"""Plugin protocol and the built-in framework plugins."""

from __future__ import annotations

from dataclasses import dataclass

from ..discover import SourceFile


@dataclass(frozen=True)
class Plugin:
    name: str
    # Package names that activate the plugin (matched against project deps).
    enablers: tuple[str, ...] = ()
    # gitignore-style globs. Entry files are roots; always-used files are reachable.
    entry_globs: tuple[str, ...] = ()
    always_used_globs: tuple[str, ...] = ()
    # When True the plugin is always active regardless of deps.
    always_on: bool = False

    def is_enabled(self, deps: set[str]) -> bool:
        if self.always_on:
            return True
        return any(e in deps for e in self.enablers)


# Generic: applies to every Python project.
_GENERIC = Plugin(
    name="generic",
    always_on=True,
    entry_globs=("**/__main__.py", "**/manage.py"),
    always_used_globs=("**/conftest.py",),
)

# Django dispatches an entire vocabulary of convention modules via app loading,
# the URL resolver, the admin/signal/migration registries, and management
# command discovery — none of it visible as a static import.
#
# LIMITATION (conscious MVP tradeoff): these globs are unscoped — they match
# e.g. ``models.py`` in ANY package, not only packages listed in
# ``INSTALLED_APPS``. So convention files of a *dead app* (left on disk after
# removal from INSTALLED_APPS) are not flagged. We favour zero false positives
# on live apps over catching that rarer case. Scoping convention files to
# declared apps (parsing INSTALLED_APPS) is deferred to Phase 2. Non-convention
# orphans inside a live app ARE still flagged (see the discriminating test).
_DJANGO = Plugin(
    name="django",
    enablers=("django", "Django"),
    entry_globs=("**/manage.py", "**/wsgi.py", "**/asgi.py"),
    always_used_globs=(
        "**/settings.py",
        "**/settings/*.py",
        "**/urls.py",
        "**/models.py",
        "**/models/*.py",
        "**/admin.py",
        "**/admin/*.py",
        "**/apps.py",
        "**/views.py",
        "**/views/*.py",
        "**/forms.py",
        "**/serializers.py",
        "**/signals.py",
        "**/receivers.py",
        "**/tasks.py",
        "**/middleware.py",
        "**/migrations/*.py",
        "**/management/commands/*.py",
        "**/templatetags/*.py",
        "**/consumers.py",
        "**/routing.py",
    ),
)

_FASTAPI = Plugin(
    name="fastapi",
    enablers=("fastapi",),
    entry_globs=("**/main.py", "**/app.py", "**/asgi.py"),
    always_used_globs=("**/routers/*.py", "**/routes/*.py", "**/api/*.py"),
)

_FLASK = Plugin(
    name="flask",
    enablers=("flask", "Flask"),
    entry_globs=("**/app.py", "**/wsgi.py", "**/main.py"),
    always_used_globs=("**/views.py", "**/views/*.py", "**/blueprints/*.py"),
)

_CELERY = Plugin(
    name="celery",
    enablers=("celery",),
    always_used_globs=("**/tasks.py", "**/tasks/*.py", "**/celery.py"),
)

_ALL: tuple[Plugin, ...] = (_GENERIC, _DJANGO, _FASTAPI, _FLASK, _CELERY)


def active_plugins(deps: set[str], files: list[SourceFile]) -> list[Plugin]:
    return [p for p in _ALL if p.is_enabled(deps)]
