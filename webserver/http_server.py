"""Static-file HTTP server for the web GUI assets (the ``web/`` directory).

Extracted from web_backend_server.py (Step 1.2 refactor). Serves the browser
front-end with directory listing disabled and caching turned off for development.
"""
import threading
import time
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler

from utils import dprint, dl


class NoListingHandler(SimpleHTTPRequestHandler):
    """Serve files from ``web/`` without directory listings and with no-cache headers."""

    def list_directory(self, path):
        self.send_error(403, "Verzeichnisauflistung nicht erlaubt")
        return None

    def end_headers(self):
        # Prevent browser caching of HTML/JS files during development
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()


def start_http_server(host, http_port, max_retries=20):
    """Start the static-file HTTP server on a daemon thread.

    If the port is already in use, increments and retries within the same thread
    (the previous implementation recursed and spawned a fresh thread on every
    collision). Returns the port that was actually bound, so the caller can point
    the browser at it.
    """
    bound_port = [http_port]  # mutable cell so the worker thread can report the real port

    def run_http_server():
        port = http_port
        for _ in range(max_retries):
            try:
                handler = partial(NoListingHandler, directory="web")
                bound_port[0] = port
                httpd = HTTPServer((host, port), handler)
                dprint(dl.WEBGUI, f"📄 HTTP Server bereit auf http://{host}:{port}")
                httpd.serve_forever()
                return
            except OSError as e:
                if e.errno == 48:  # Address already in use
                    dprint(dl.WEBGUI, f"⚠️  Port {port} ist bereits belegt. Verwende anderen Port.")
                    port += 1
                    continue
                dprint(dl.WEBGUI, f"❌ HTTP Server Fehler: {e}")
                return
            except Exception as e:
                dprint(dl.WEBGUI, f"❌ Unerwarteter HTTP Server Fehler: {e}")
                return
        dprint(dl.WEBGUI, f"❌ Kein freier HTTP-Port nach {max_retries} Versuchen gefunden.")

    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    time.sleep(0.5)
    return bound_port[0]
