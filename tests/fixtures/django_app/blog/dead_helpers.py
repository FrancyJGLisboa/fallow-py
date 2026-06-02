# A genuinely-dead module inside a live Django app: matches no framework
# convention glob and is imported by nobody. The engine MUST still flag this —
# otherwise activating a plugin would make it blind to orphans (the wedge).
def unused_helper() -> str:
    return "nobody imports this"
