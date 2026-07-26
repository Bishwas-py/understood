#!/usr/bin/env python3
"""One folder per rundown, so a rebuild cannot orphan the conversation.

    .rundown/ask-loop/
        spec.json          the truth, the only file anyone edits
        page.html          build output, overwritten by every build
        questions.jsonl    what the reader asked
        answers.jsonl      what the session answered
        history/*.json     a copy of spec.json taken before each write

The folder name is the identity. Nothing is keyed on a filename, so re-rendering
never separates a page from its thread. The store sits in the repo the
rundown is about, and is added to .git/info/exclude rather than .gitignore,
since .gitignore is a tracked file in someone else's project.

The command surface lives in cli.py; this is the library it stands on.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from spec import load, save as write_json

STORE = ".rundown"
KEEP = 20


def repo_root(start: Path | None = None) -> Path:
    """The git top level, or the directory itself when there is no repo."""
    start = (start or Path.cwd()).resolve()
    try:
        out = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return Path(out.stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        return start


def ensure_ignored(root: Path) -> None:
    """Keep the store out of git without touching the project's own .gitignore."""
    exclude = root / ".git" / "info" / "exclude"
    if not exclude.parent.is_dir():
        return
    lines = exclude.read_text(encoding="utf-8").splitlines() if exclude.is_file() else []
    if any(l.strip().rstrip("/") == STORE for l in lines):
        return
    lines.append(STORE + "/")
    exclude.write_text("\n".join(lines) + "\n", encoding="utf-8")


def store_dir(start: Path | None = None) -> Path:
    root = repo_root(start)
    ensure_ignored(root)
    return root / STORE


class Home:
    """Every path a rundown owns, derived from its slug and nothing else."""

    def __init__(self, slug: str, start: Path | None = None, root: Path | None = None):
        self.slug = slug
        self.root = root or store_dir(start)
        self.dir = self.root / slug
        self.spec = self.dir / "spec.json"
        self.page = self.dir / "page.html"
        self.questions = self.dir / "questions.jsonl"
        self.answers = self.dir / "answers.jsonl"
        self.history = self.dir / "history"

    def create(self) -> Home:
        self.history.mkdir(parents=True, exist_ok=True)
        return self

    def exists(self) -> bool:
        return self.spec.is_file()


def snapshot(home: Home) -> Path | None:
    """A copy of the spec before it is overwritten. The undo there is no git for."""
    if not home.spec.is_file():
        return None
    home.history.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    shot = home.history / f"{stamp}.json"
    shutil.copy2(home.spec, shot)
    old = sorted(home.history.glob("*.json"))[:-KEEP]
    for path in old:
        path.unlink()
    return shot


def save_spec(home: Home, spec: dict) -> Path | None:
    home.create()
    shot = snapshot(home)
    write_json(home.spec, spec)
    return shot


def build(home: Home, fix: bool = False) -> int:
    """Validate, then render into the folder. A failing validate is a build error."""
    import render
    import validate

    if not home.exists():
        print(f"no rundown named {home.slug} in {home.dir.parent}", file=sys.stderr)
        return 1
    spec = load(home.spec)
    if fix:
        moved = validate.resync(spec)
        for line in moved:
            print(f"  moved {line}")
        if moved:
            save_spec(home, spec)
    rep = validate.validate(spec)
    rep.print()
    if rep.errors:
        return 1
    home.page.write_text(render.render(spec), encoding="utf-8")
    print(f"built {home.page} ({home.page.stat().st_size} bytes)")
    return 0


def each(start: Path | None = None, root: Path | None = None):
    root = root or store_dir(start)
    for child in sorted(root.glob("*/spec.json")):
        yield Home(child.parent.name, root=root)


def count_lines(path: Path) -> int:
    if not path.is_file():
        return 0
    return sum(1 for l in path.read_text(encoding="utf-8").splitlines() if l.strip())
