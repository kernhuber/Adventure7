"""Web backend package for the text adventure.

Hosts the WebSocket/HTTP server that bridges the browser GUI to the game engine.
``web_backend_server.py`` at the project root remains the launch entry point and
simply delegates to :func:`run_working_adventure` exported here.
"""
from webserver.server import WebAdventureServer, run_working_adventure

__all__ = ["WebAdventureServer", "run_working_adventure"]
