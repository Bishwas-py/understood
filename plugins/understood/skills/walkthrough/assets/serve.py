#!/usr/bin/env python3
"""Serve ONE walkthrough file on a stable local origin: walkthrough.localhost.

Deliberately not `python3 -m http.server`: that serves the whole directory, and
these files usually live in Downloads. This binds loopback only and answers
every path with the single file it was given, so nothing else is exposed.

    ./serve.py ~/Downloads/my-change-walkthrough.html
    ./serve.py path/to/file.html --port 8412 --open

Why walkthrough.localhost and a fixed port: browsers treat *.localhost as a
secure context, so the "Open Cursor?" external-protocol dialog offers an
"Always allow" checkbox, and that decision is remembered per origin (host AND
port). A stable host:port means the presenter approves the editor link once,
ever. The walkthrough's slug goes in the URL path, not the hostname.
"""

from __future__ import annotations

import argparse
import http.server
import re
import socket
import socketserver
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

HOST = "walkthrough.localhost"
BASE_PORT = 8477


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "walkthrough"


def free_port(preferred: int | None) -> int:
    """Prefer a stable port so the browser's per-origin approval survives restarts."""
    if preferred:
        return preferred
    for port in range(BASE_PORT, BASE_PORT + 20):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def open_in_browser(url: str) -> None:
    """Use the platform's own opener when there is one, else webbrowser."""
    opener = {"darwin": ["open"], "linux": ["xdg-open"]}.get(sys.platform)
    if sys.platform.startswith("win"):
        opener = ["cmd", "/c", "start", ""]
    if opener:
        try:
            subprocess.run([*opener, url], check=False)
            return
        except OSError:
            pass
    webbrowser.open(url)


def serve(path: Path, port: int) -> None:
    body = path.read_bytes()

    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self):  # noqa: N802
            if self.path in ("/favicon.ico",):
                self.send_response(204)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):  # quiet
            pass

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    with Server(("127.0.0.1", port), Handler) as httpd:
        httpd.serve_forever()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("file", type=Path)
    ap.add_argument("--port", type=int, default=None)
    ap.add_argument("--open", action="store_true", help="open the URL after starting")
    args = ap.parse_args()

    path = args.file.expanduser().resolve()
    if not path.is_file():
        print(f"no such file: {path}", file=sys.stderr)
        return 1

    port = free_port(args.port)
    slug = slugify(path.stem)
    url = f"http://{HOST}:{port}/{slug}/"

    threading.Thread(target=serve, args=(path, port), daemon=True).start()

    # flush: the caller usually backgrounds this and reads the URL from a log
    print(url, flush=True)
    if port != BASE_PORT and not args.port:
        print(
            f"(port {BASE_PORT} was busy; on {port} the browser may ask to allow the editor link once more)",
            file=sys.stderr,
            flush=True,
        )
    if args.open:
        open_in_browser(url)

    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
