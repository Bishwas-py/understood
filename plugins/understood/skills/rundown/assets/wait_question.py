#!/usr/bin/env python3
"""Wait for unanswered rundown questions, or record an answer.

Wait mode (default) blocks until at least one question in QUESTIONS has no
matching id in ANSWERS, prints the pending question(s) as JSON lines, and
exits 0. Run it in the background; its exit is the signal that someone asked.

    ./wait_question.py foo.questions.jsonl foo.answers.jsonl

Answer mode appends one answer, text read from stdin (heredoc-safe):

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
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from serve import read_jsonl
from spec import append_jsonl


def files_signature(*paths: Path) -> tuple:
    sig = []
    for p in paths:
        try:
            st = p.stat()
            sig.append((st.st_mtime_ns, st.st_size))
        except OSError:
            sig.append(None)
    return tuple(sig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("questions", type=Path)
    ap.add_argument("answers", type=Path)
    ap.add_argument("--answer", metavar="ID", help="append an answer for ID, text from stdin")
    ap.add_argument("--rebind", metavar="TEXT", help="the quoted text was reworded to TEXT, move the mark there")
    ap.add_argument("--poll", type=float, default=0.5)
    args = ap.parse_args()

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
        return 0

    last_sig = None
    while True:
        sig = files_signature(args.questions, args.answers)
        if sig != last_sig:
            last_sig = sig
            answered = {r.get("id") for r in read_jsonl(args.answers)}
            pending = [q for q in read_jsonl(args.questions) if q.get("id") not in answered]
            if pending:
                for question in pending:
                    print(json.dumps(question, ensure_ascii=False), flush=True)
                return 0
        time.sleep(args.poll)


if __name__ == "__main__":
    raise SystemExit(main())
