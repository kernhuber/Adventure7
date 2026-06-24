"""Web backend package for the text adventure.

Hosts the WebSocket/HTTP server that bridges the browser GUI to the game engine.
``web_backend_server.py`` at the project root remains the launch entry point and
delegates to :func:`run_working_adventure` exported here.

The server class pulls in the full game/LLM stack, so it is imported lazily (PEP
562): ``from webserver import run_working_adventure`` still works, but importing a
leaf module such as ``webserver.http_server`` does not drag in that heavy chain,
keeping the leaf modules independently testable.
"""

__all__ = ["WebAdventureServer", "run_working_adventure"]


def __getattr__(name):
    if name in __all__:
        from webserver import server
        return getattr(server, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
