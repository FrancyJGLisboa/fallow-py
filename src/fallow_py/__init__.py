"""fallow-py: unified codebase intelligence for Python.

The wedge is whole-project module reachability — which modules are genuinely
orphaned — plus circular-dependency detection, built natively on the stdlib
``ast`` module. Leaf analyses (dependency hygiene, complexity, boundaries) are
delegated to mature tools via adapters and unified under one issue model.
"""

__version__ = "0.0.1"
