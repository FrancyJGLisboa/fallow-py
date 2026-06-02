from a import run  # noqa: F401 — deliberate import cycle a <-> b


def helper() -> str:
    return "helped"
