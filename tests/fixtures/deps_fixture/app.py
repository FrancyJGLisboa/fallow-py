import os  # stdlib only — the declared 'pathspec' dependency is never used.


def where() -> str:
    return os.getcwd()
