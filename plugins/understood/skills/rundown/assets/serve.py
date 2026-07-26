#!/usr/bin/env python3
"""Serve ONE rundown file on a stable local origin: rundown.localhost.

Deliberately not `python3 -m http.server`: that serves the whole directory, and
these files usually live in Downloads. This binds loopback only and answers
every path with the single file it was given, so nothing else is exposed.

    ./serve.py ~/Downloads/my-change-rundown.html
    ./serve.py path/to/file.html --port 8412 --open

Why rundown.localhost and a fixed port: browsers treat *.localhost as a
secure context, so the "Open Cursor?" external-protocol dialog offers an
"Always allow" checkbox, and that decision is remembered per origin (host AND
port). A stable host:port means the presenter approves the editor link once,
ever. The rundown's slug goes in the URL path, not the hostname.
"""

from __future__ import annotations

import argparse
import http.server
import json
import re
import socket
import socketserver
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

HOST = "rundown.localhost"
BASE_PORT = 8477


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "rundown"


def taken(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def free_port(preferred: int | None) -> int:
    """Prefer a stable port so the browser's per-origin approval survives restarts."""
    if preferred:
        # SO_REUSEADDR would let us bind a port someone else is already answering
        # on, and then quietly serve nothing. Say so instead.
        if taken(preferred):
            raise SystemExit(f"port {preferred} is already serving something, stop it or pick another")
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


def in_store(path: Path) -> bool:
    """A page inside a rundown folder shares that folder's conversation."""
    return (path.parent / "spec.json").is_file()


def qa_paths(path: Path) -> tuple[Path, Path]:
    if in_store(path):
        return path.parent / "questions.jsonl", path.parent / "answers.jsonl"
    return (
        path.with_name(path.stem + ".questions.jsonl"),
        path.with_name(path.stem + ".answers.jsonl"),
    )


def read_jsonl(path: Path) -> list[dict]:
    records = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict):
                records.append(record)
    return records


def serve(path: Path, port: int) -> None:
    state = {"body": path.read_bytes(), "mtime": path.stat().st_mtime}
    questions_path, answers_path = qa_paths(path)
    append_lock = threading.Lock()

    def body() -> bytes:
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return state["body"]
        if mtime != state["mtime"]:
            state["mtime"] = mtime
            state["body"] = path.read_bytes()
        return state["body"]

    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def reply(self, status, payload=b"", ctype=None):
            self.send_response(status)
            if ctype:
                self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(payload)))
            if status == 200:
                self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if payload:
                self.wfile.write(payload)

        def do_GET(self):  # noqa: N802
            if self.path in ("/favicon.ico",):
                self.reply(204)
                return
            if self.path.split("?", 1)[0] == "/qa.json":
                payload = json.dumps(
                    {
                        "questions": read_jsonl(questions_path),
                        "answers": read_jsonl(answers_path),
                    },
                    ensure_ascii=False,
                ).encode("utf-8")
                self.reply(200, payload, "application/json; charset=utf-8")
                return
            self.reply(200, body(), "text/html; charset=utf-8")

        def do_POST(self):  # noqa: N802
            if self.path != "/ask":
                self.reply(404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if not 0 < length <= 65536:
                self.reply(413)
                return
            try:
                raw = json.loads(self.rfile.read(length))
                record = {
                    "id": str(raw["id"])[:64],
                    "stop": str(raw.get("stop", ""))[:64],
                    "parent": str(raw.get("parent", ""))[:64],
                    "via": str(raw.get("via", ""))[:16],
                    "block": str(raw.get("block", ""))[:24],
                    "part": str(raw.get("part", ""))[:120],
                    "selection": str(raw.get("selection", ""))[:2000],
                    "question": str(raw["question"])[:2000],
                }
            except (KeyError, TypeError, ValueError):
                self.reply(400)
                return
            with append_lock, questions_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            self.reply(204)

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

    path = args.file.expanduser()
    if not path.is_file():
        import store

        home = store.Home(str(args.file))
        if home.page.is_file():
            path = home.page
        elif home.exists():
            print(f"{home.slug} is not built yet, run store.py build {home.slug}", file=sys.stderr)
            return 1
        else:
            print(f"no such file or rundown: {args.file}", file=sys.stderr)
            return 1
    path = path.resolve()

    port = free_port(args.port)
    slug = slugify(path.parent.name if in_store(path) else path.stem)
    url = f"http://{HOST}:{port}/{slug}/"

    threading.Thread(target=serve, args=(path, port), daemon=True).start()

    # flush: the caller usually backgrounds this and reads the URL from a log
    print(url, flush=True)
    questions_path, answers_path = qa_paths(path)
    print(f"questions: {questions_path}", file=sys.stderr, flush=True)
    print(f"answers:   {answers_path}", file=sys.stderr, flush=True)
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
