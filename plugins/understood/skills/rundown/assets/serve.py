#!/usr/bin/env python3
"""Serve the rundowns in this repo on one stable local origin: rundown.localhost.

One process, one origin, every rundown in the store:

    /                an index of the rundowns in this repo
    /<slug>/         that rundown's page
    /<slug>/qa.json  its conversation, polled by the page
    /<slug>/ask      POST, one question appended

Deliberately not `python3 -m http.server`: this binds loopback only and answers
nothing but the pages and conversations it knows about, so a stray request
cannot list or fetch anything else.

Why rundown.localhost and a fixed port: browsers treat *.localhost as a secure
context, so the "Open Cursor?" external-protocol dialog offers an "Always allow"
checkbox, and that decision is remembered per origin (host AND port). One origin
for every rundown means the presenter approves the editor link once, ever.

    ./serve.py                       every rundown in this repo, index at /
    ./serve.py ask-loop --open       the same server, opened at that one
    ./serve.py path/to/page.html     one loose file, for the hand-authored path
"""

from __future__ import annotations

import argparse
import html
import http.server
import json
import re
import socket
import socketserver
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
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
        if not taken(port):
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


def read_jsonl(path: Path | None) -> list[dict]:
    records = []
    if path and path.exists():
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


class Reader:
    """One file's bytes, re-read whenever it changes on disk."""

    def __init__(self, path: Path):
        self.path = path
        self.mtime = -1.0
        self.body = b""

    def bytes(self) -> bytes:
        try:
            mtime = self.path.stat().st_mtime
        except OSError:
            return self.body
        if mtime != self.mtime:
            self.mtime, self.body = mtime, self.path.read_bytes()
        return self.body


class FileSite:
    """One loose html file, answering under any slug. The hand-authored path."""

    def __init__(self, path: Path):
        self.path = path
        self.reader = Reader(path)
        if (path.parent / "spec.json").is_file():
            self.slug = slugify(path.parent.name)
            self.questions = path.parent / "questions.jsonl"
            self.answers = path.parent / "answers.jsonl"
        else:
            self.slug = slugify(path.stem)
            self.questions = path.with_name(path.stem + ".questions.jsonl")
            self.answers = path.with_name(path.stem + ".answers.jsonl")

    def page(self, slug: str) -> bytes | None:
        return self.reader.bytes()

    def qa_files(self, slug: str):
        return self.questions, self.answers

    def index(self) -> bytes | None:
        return None


class StoreSite:
    """Every rundown in one repo, under one origin."""

    def __init__(self, root: Path):
        self.root = root
        self.readers: dict[str, Reader] = {}

    def homes(self):
        import store

        return list(store.each(root=self.root))

    def home(self, slug: str):
        import store

        home = store.Home(slug, root=self.root)
        return home if home.exists() else None

    def page(self, slug: str) -> bytes | None:
        home = self.home(slug)
        if not home or not home.page.is_file():
            return None
        reader = self.readers.get(slug)
        if not reader:
            reader = self.readers[slug] = Reader(home.page)
        return reader.bytes()

    def qa_files(self, slug: str):
        home = self.home(slug)
        return (home.questions, home.answers) if home else (None, None)

    def index(self) -> bytes:
        return index_html(self.homes(), self.root).encode("utf-8")


def index_html(homes: list, root: Path) -> str:
    """The front page: what is in this repo, and how much of it has been asked about."""
    rows = []
    for home in homes:
        try:
            title = json.loads(home.spec.read_text(encoding="utf-8")).get("title", home.slug)
        except (OSError, ValueError):
            title = home.slug
        asked = len(read_jsonl(home.questions))
        built = (
            "built " + datetime.fromtimestamp(home.page.stat().st_mtime).strftime("%d %b, %H:%M")
            if home.page.is_file()
            else "not built"
        )
        rows.append(
            f'<li><a href="/{html.escape(home.slug)}/"><b>{html.escape(title)}</b>'
            f'<span class="slug">{html.escape(home.slug)}</span></a>'
            f'<span class="meta">{asked} asked &middot; {built}</span></li>'
        )
    body = "\n".join(rows) or '<li class="none">no rundowns here yet</li>'
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>rundowns</title>
<style>
  :root {{ --bg: #fbfaf8; --fg: #1a1a1a; --dim: #6b6b6b; --line: #e2ded8; --card: #fff; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg: #14161a; --fg: #e8e6e3; --dim: #9a9894; --line: #262a30; --card: #191c21; }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--bg); color: var(--fg); padding: 64px 24px;
         font: 15px/1.6 ui-sans-serif, -apple-system, system-ui, sans-serif; }}
  main {{ max-width: 620px; margin: 0 auto; }}
  h1 {{ font-size: 21px; margin: 0 0 4px; letter-spacing: -.01em; }}
  .where {{ color: var(--dim); font-size: 12.5px; margin: 0 0 28px;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
  ul {{ list-style: none; margin: 0; padding: 0; }}
  li {{ border: 1px solid var(--line); border-radius: 12px; margin-bottom: 10px; background: var(--card); }}
  li.none {{ padding: 18px; color: var(--dim); text-align: center; }}
  a {{ display: flex; align-items: baseline; gap: 10px; padding: 15px 18px 5px;
       color: inherit; text-decoration: none; }}
  a:hover b {{ text-decoration: underline; }}
  .slug {{ color: var(--dim); font-size: 12.5px;
           font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
  .meta {{ display: block; padding: 0 18px 15px; color: var(--dim); font-size: 12.5px; }}
</style></head>
<body><main>
<h1>rundowns</h1>
<p class="where">{html.escape(str(root))}</p>
<ul>
{body}
</ul>
</main></body></html>
"""


def split_path(path: str) -> tuple[str, str]:
    """`/ask-loop/qa.json` -> ("ask-loop", "qa.json"). A bare segment is a slug."""
    parts = [p for p in path.split("?", 1)[0].split("/") if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return ("", parts[0]) if "." in parts[0] else (parts[0], "")
    return parts[0], parts[-1]


def serve(site, port: int) -> None:
    append_lock = threading.Lock()

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
            if self.path.startswith("/favicon"):
                self.reply(204)
                return
            slug, leaf = split_path(self.path)
            if leaf == "qa.json":
                questions, answers = site.qa_files(slug)
                if not questions:
                    self.reply(404)
                    return
                payload = json.dumps(
                    {"questions": read_jsonl(questions), "answers": read_jsonl(answers)},
                    ensure_ascii=False,
                ).encode("utf-8")
                self.reply(200, payload, "application/json; charset=utf-8")
                return
            if not slug:
                index = site.index()
                body = site.page("") if index is None else index
                self.reply(200, body, "text/html; charset=utf-8")
                return
            body = site.page(slug)
            if body is None:
                self.reply(404, b"no such rundown", "text/plain; charset=utf-8")
                return
            self.reply(200, body, "text/html; charset=utf-8")

        def do_POST(self):  # noqa: N802
            slug, leaf = split_path(self.path)
            if leaf != "ask":
                self.reply(404)
                return
            questions, _ = site.qa_files(slug)
            if not questions:
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
            with append_lock, questions.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            self.reply(204)

        def log_message(self, *args):  # quiet
            pass

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    with Server(("127.0.0.1", port), Handler) as httpd:
        httpd.serve_forever()


def build_site(target: str | None):
    """A path means that one file; a slug or nothing means this repo's store."""
    import store

    if target:
        path = Path(target).expanduser()
        if path.is_file():
            site = FileSite(path.resolve())
            return site, site.slug
    root = store.store_dir()
    site = StoreSite(root)
    if target and not site.home(target):
        raise SystemExit(f"no rundown named {target} in {root}")
    return site, (target or "")


def run(target: str | None = None, port: int | None = None, open_after: bool = False, block: bool = True) -> int:
    site, slug = build_site(target)
    port = free_port(port)
    url = f"http://{HOST}:{port}/" + (f"{slug}/" if slug else "")

    threading.Thread(target=serve, args=(site, port), daemon=True).start()

    # flush: the caller usually backgrounds this and reads the URL from a log
    print(url, flush=True)
    if slug:
        questions, answers = site.qa_files(slug)
        print(f"questions: {questions}", file=sys.stderr, flush=True)
        print(f"answers:   {answers}", file=sys.stderr, flush=True)
    if port != BASE_PORT:
        print(
            f"(port {BASE_PORT} was busy; on {port} the browser may ask to allow the editor link once more)",
            file=sys.stderr,
            flush=True,
        )
    if open_after:
        open_in_browser(url)
    if not block:
        return 0
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        return 0
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?", help="a slug, a path to one html file, or nothing for all of them")
    ap.add_argument("--port", type=int, default=None)
    ap.add_argument("--open", action="store_true", help="open the URL after starting")
    args = ap.parse_args()
    return run(args.target, args.port, args.open)


if __name__ == "__main__":
    raise SystemExit(main())
