#!/usr/bin/env python3
"""Serve ONE walkthrough file on a local host, reachable as <slug>.lvh.me:<port>.

Deliberately not `python3 -m http.server`: that serves the whole directory, and
these files usually live in Downloads. This binds loopback only and answers
every path with the single file it was given, so nothing else is exposed.

    ./serve.py ~/Downloads/my-change-walkthrough.html
    ./serve.py path/to/file.html --port 8412 --open
"""

from __future__ import annotations

import argparse
import http.server
import os
import re
import socket
import socketserver
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

# Any subdomain of lvh.me resolves to 127.0.0.1 via public DNS, which gives the
# page a memorable hostname without touching /etc/hosts. It needs DNS to
# resolve, so an offline machine falls back to localhost.
LVH = "lvh.me"


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "walkthrough"


def free_port(preferred: int | None) -> int:
    if preferred:
        return preferred
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def lvh_resolves() -> bool:
    try:
        socket.getaddrinfo(LVH, None)
        return True
    except OSError:
        return False


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
    host = f"{slug}.{LVH}" if lvh_resolves() else "localhost"
    url = f"http://{host}:{port}/"

    threading.Thread(target=serve, args=(path, port), daemon=True).start()

    # flush: the caller usually backgrounds this and reads the URL from a log
    print(url, flush=True)
    if host == "localhost":
        print(f"({LVH} did not resolve, serving on localhost instead)", file=sys.stderr, flush=True)
    if args.open:
        open_in_browser(url)

    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
