__all__ = [
    "run",
]


def run():
    from .app import run as _run

    return _run()
