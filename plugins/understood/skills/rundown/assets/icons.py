#!/usr/bin/env python3
"""One glyph per idea, inlined at build time so the page still opens offline.

Iconify serves the drawings; a page that fetched them would stop working the
first time it was opened without a network, which is the one thing a rundown
must never do. So the bodies are fetched once, cached beside this file, and
emitted into the page as a sprite of <symbol>s that every icon then references.

    python3 icons.py            refresh the cache from iconify
    python3 icons.py --check    say what is cached and what is missing
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

from spec import ICONS

HERE = Path(__file__).resolve().parent
CACHE = HERE / "icons.json"
SET = "lucide"
API = "https://api.iconify.design/{set}.json?icons={names}"


def wanted() -> list[str]:
    return sorted(set(ICONS.values()))


def load() -> dict:
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def fetch(names: list[str]) -> dict:
    url = API.format(set=SET, names=",".join(names))
    # the api refuses a request with no agent, and a build should say why rather
    # than come back with an empty sprite
    req = urllib.request.Request(url, headers={"User-Agent": "rundown/1.x (+github.com/Bishwas-py/understood)"})
    with urllib.request.urlopen(req, timeout=20) as r:  # noqa: S310
        data = json.loads(r.read().decode("utf-8"))
    missing = data.get("not_found") or []
    if missing:
        print(f"iconify has no {SET}:{', '.join(missing)}", file=sys.stderr)
    return {k: v["body"] for k, v in (data.get("icons") or {}).items()}


def sprite() -> str:
    """The <symbol> defs, or an empty string when nothing is cached.

    A missing cache is not a build error: the page renders with the glyphs
    absent rather than refusing to build somewhere with no network.
    """
    bodies = load()
    have = [n for n in wanted() if n in bodies]
    if not have:
        return ""
    body = "".join(f'<symbol id="i-{n}" viewBox="0 0 24 24">{bodies[n]}</symbol>' for n in have)
    return f'<svg xmlns="http://www.w3.org/2000/svg" style="display:none" aria-hidden="true">{body}</svg>'


def icon(name: str, cls: str = "i") -> str:
    """`icon("why")` -> the svg that references the sprite, or nothing at all."""
    glyph = ICONS.get(name, name)
    if glyph not in load():
        return ""
    return f'<svg class="{cls}" aria-hidden="true"><use href="#i-{glyph}"/></svg>'


def main() -> int:
    bodies = load()
    if "--check" in sys.argv:
        missing = [n for n in wanted() if n not in bodies]
        print(f"cached {len(bodies)} of {len(wanted())} glyphs in {CACHE.name}")
        if missing:
            print("missing: " + ", ".join(missing))
        return 1 if missing else 0
    try:
        fresh = fetch(wanted())
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"could not reach iconify: {e}", file=sys.stderr)
        return 1
    CACHE.write_text(json.dumps({**bodies, **fresh}, indent=0, sort_keys=True), encoding="utf-8")
    print(f"cached {len(fresh)} glyphs from {SET} into {CACHE.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
