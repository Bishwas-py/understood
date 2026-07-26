#!/usr/bin/env python3
"""Refuse to end a turn while a reader is still waiting on an answer.

A background waiter can be killed, forgotten, or never started, and then a
question sits in a file nobody reads. This runs on Stop, which fires every time
Claude finishes responding, so the check happens whether or not anything else
is alive.

Exit 2 blocks the stop and puts the stderr in front of Claude. Exit 0 lets the
turn end. Nothing here writes to the conversation.

Each question is raised once. If a turn ends with the same one still unanswered,
it is let through, because a hook that argues with a stuck model just burns the
block cap for nothing.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

STORE = ".rundown"
SEEN = "nudged"


def rundowns(root: Path):
    store = root / STORE
    if not store.is_dir():
        return
    for questions in sorted(store.glob("*/questions.jsonl")):
        yield questions.parent


def records(path: Path) -> list[dict]:
    out = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def pending(home: Path) -> list[dict]:
    answers = records(home / "answers.jsonl")
    answered = {r.get("id") for r in answers if r.get("answer") is not None}
    return [q for q in records(home / "questions.jsonl") if q.get("id") not in answered]


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        event = {}
    root = Path(event.get("cwd") or os.getcwd())

    fresh, homes = [], []
    for home in rundowns(root):
        waiting = pending(home)
        if not waiting:
            continue
        seen_file = home / SEEN
        try:
            seen = set(seen_file.read_text(encoding="utf-8").split())
        except OSError:
            seen = set()
        new = [q for q in waiting if q.get("id") not in seen]
        if new:
            homes.append(home)
            fresh.extend((home, q) for q in new)
            seen_file.write_text(" ".join(sorted(seen | {q["id"] for q in waiting})), encoding="utf-8")

    if not fresh:
        return 0

    lines = [f"{len(fresh)} question(s) on a served rundown have no answer yet. Answer them before finishing:"]
    for home, q in fresh[:6]:
        where = f' on "{q["selection"][:60]}"' if q.get("selection") else ""
        lines.append(f'  {home.name} {q["id"][:8]}{where}: {q.get("question", "")[:120]}')
    lines.append("")
    lines.append("Answer with the same helper, then the waiter rearms itself:")
    lines.append(
        f'  python3 "$CLAUDE_PLUGIN_ROOT/skills/rundown/assets/wait_question.py" '
        f'{homes[0]}/questions.jsonl {homes[0]}/answers.jsonl --answer <id> <<\'EOF\' ... EOF'
    )
    print("\n".join(lines), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
