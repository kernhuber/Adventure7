"""Entry point for the web adventure server.

The implementation lives in the ``webserver`` package (see ``webserver/server.py``).
This module stays at the project root because ``start.sh`` / ``start.bat`` launch the
game with ``python3 ./web_backend_server.py``; it just delegates to the package.
"""
from webserver import run_working_adventure

if __name__ == "__main__":
    run_working_adventure()
