#!/usr/bin/env python3
"""Wait for unanswered rundown questions, or record an answer.

Wait mode (default) blocks until at least one question in QUESTIONS has no
matching id in ANSWERS, prints the pending question(s) as JSON lines, and
exits 0. Run it in the background; its exit is the signal that someone asked.

    ./wait_question.py foo.questions.jsonl foo.answers.jsonl

Answer mode appends one answer, text read from stdin (heredoc-safe), and then
puts a fresh waiter back in place, because forgetting to rearm is how a reader
ends up talking to nobody:

    ./wait_question.py foo.questions.jsonl foo.answers.jsonl --answer <id> <<'EOF'
    - short bullet
    - another
    EOF

If the answer reworded the text the question was asked on, say what it became.
The mark follows it to the new words and the card shows both, so a rename never
costs a reader the thread back to what they asked about:

    ... --answer <id> --rebind "did the form close this block" <<'EOF'
    - reworded and rebuilt, node C now reads as a question
    EOF

While a waiter is alive it keeps a `watching` file beside the conversation,
touched every few seconds. The page reads it through qa.json and says plainly
when nobody is listening, rather than guessing from how long an answer took.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from serve import read_jsonl
from spec import append_jsonl

HERE = Path(__file__).resolve().parent
STALE_AFTER = 20.0


def watch_file(questions: Path) -> Path:
    return questions.with_name("watching")


def watching(questions: Path) -> bool:
    """True when a waiter touched the file recently enough to still be alive."""
    try:
        return (time.time() - watch_file(questions).stat().st_mtime) < STALE_AFTER
    except OSError:
        return False


def files_signature(*paths: Path) -> tuple:
    sig = []
    for p in paths:
        try:
            st = p.stat()
            sig.append((st.st_mtime_ns, st.st_size))
        except OSError:
            sig.append(None)
    return tuple(sig)


def pending_questions(questions: Path, answers: Path) -> list[dict]:
    answered = {r.get("id") for r in read_jsonl(answers) if r.get("answer") is not None}
    return [q for q in read_jsonl(questions) if q.get("id") not in answered]


def rearm(questions: Path, answers: Path) -> None:
    """Put a waiter back in place, detached, unless one is already alive."""
    if watching(questions):
        return
    try:
        subprocess.Popen(
            [sys.executable, str(HERE / "wait_question.py"), str(questions), str(answers)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as e:
        print(f"could not rearm the waiter: {e}", file=sys.stderr)


def wait(questions: Path, answers: Path, poll: float) -> int:
    # A killed waiter should stop claiming to listen straight away, so take the
    # signal rather than dying where the cleanup below never runs.
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        try:
            signal.signal(sig, lambda *_: sys.exit(0))
        except (OSError, ValueError):
            pass
    mark = watch_file(questions)
    last_sig, last_touch, woke = None, 0.0, False
    try:
        while True:
            now = time.time()
            if now - last_touch > 5:
                last_touch = now
                try:
                    mark.parent.mkdir(parents=True, exist_ok=True)
                    mark.write_text(str(os.getpid()), encoding="utf-8")
                except OSError:
                    pass
            sig = files_signature(questions, answers)
            if sig != last_sig:
                last_sig = sig
                try:
                    pending = pending_questions(questions, answers)
                except OSError:
                    pending = []
                if pending:
                    for question in pending:
                        print(json.dumps(question, ensure_ascii=False), flush=True)
                    woke = True
                    return 0
            time.sleep(poll)
    finally:
        # Waking is not leaving: the session is now the one listening, and
        # answering rearms. The mark only goes stale if that never happens.
        if not woke:
            try:
                mark.unlink()
            except OSError:
                pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("questions", type=Path)
    ap.add_argument("answers", type=Path)
    ap.add_argument("--answer", metavar="ID", help="append an answer for ID, text from stdin")
    ap.add_argument("--rebind", metavar="TEXT", help="the quoted text was reworded to TEXT, move the mark there")
    ap.add_argument("--no-rearm", action="store_true", help="do not put a waiter back after answering")
    ap.add_argument("--pending", action="store_true", help="print what is unanswered and exit, never blocks")
    ap.add_argument("--poll", type=float, default=0.5)
    args = ap.parse_args()

    if args.pending:
        for question in pending_questions(args.questions, args.answers):
            print(json.dumps(question, ensure_ascii=False))
        return 0

    if args.answer:
        text = "" if (args.rebind and sys.stdin.isatty()) else sys.stdin.read().strip()
        if not text and not args.rebind:
            print("empty answer, nothing appended", file=sys.stderr)
            return 1
        # A rebind on its own is how an old mark is relinked: the answer already
        # on the card stays exactly as it was written.
        record = {"id": args.answer}
        if text:
            record["answer"] = text
        if args.rebind:
            record["rebind"] = {"to": args.rebind}
        append_jsonl(args.answers, record)
        if not args.no_rearm:
            rearm(args.questions, args.answers)
        return 0

    return wait(args.questions, args.answers, args.poll)


if __name__ == "__main__":
    raise SystemExit(main())
