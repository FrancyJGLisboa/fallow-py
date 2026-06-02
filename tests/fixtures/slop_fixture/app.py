import json  # genuinely unused -> ruff F401


def used():
    return 1


def dead_function():
    # The module is reachable, but this function is never called anywhere
    # -> vulture dead-code (intra-module slop the native engine cannot see).
    return "slop"


class DeadClass:
    pass


print(used())
