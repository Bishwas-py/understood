#!/usr/bin/env python3
"""Two hands, embedded, so the page reads the same on any machine.

A rundown is opened on a call, screen-shared, and sometimes sent as a file. A
webfont link would make the type depend on a network the reader may not have,
and a local font would make it depend on what happens to be installed. So both
faces ride inside the html as base64.

    Shantell Sans   the major face. Every sentence on the page, down to 12px,
                    because it was drawn upright and even for interfaces.
    Caveat          the minor face. Title, headings, claims, the carry rule.
                    A real slant and long extenders, so it never goes small.

    python3 fonts.py            refresh both from google fonts
    python3 fonts.py --check    say what is here and how heavy it is
"""

from __future__ import annotations

import base64
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIR = HERE / "fonts"
AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"

# family -> (file stem, the google css2 spec, the weights the page uses)
FACES = {
    "Caveat": ("Caveat", "Caveat:wght@600", "400 700"),
    "Shantell Sans": ("ShantellSans", "Shantell+Sans:wght@400", "400 700"),
}


def path_of(family: str) -> Path:
    return DIR / f"{FACES[family][0]}.woff2"


def css() -> str:
    """The @font-face rules, or an empty string when nothing is on disk.

    Missing faces are not a build error: the page falls back to the system's
    own hand rather than refusing to build.
    """
    out = []
    for family, (_, _, weights) in FACES.items():
        p = path_of(family)
        if not p.is_file():
            continue
        b64 = base64.b64encode(p.read_bytes()).decode()
        out.append(
            f"@font-face{{font-family:'{family}';font-weight:{weights};font-style:normal;"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2');font-display:block}}"
        )
    return "".join(out)


def fetch(family: str) -> int:
    """Google serves one @font-face per subset and puts latin last. Taking the
    first url gets you cyrillic, and every latin letter falls back to serif."""
    _, spec, _ = FACES[family]
    url = f"https://fonts.googleapis.com/css2?family={spec}&display=block"
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(req, timeout=20) as r:  # noqa: S310
        sheet = r.read().decode("utf-8")
    blocks = re.findall(r"@font-face\s*\{[^}]*\}", sheet)
    latin = [b for b in blocks if "U+0000-00FF" in b]
    pick = latin[-1] if latin else blocks[-1]
    woff = re.search(r"url\((https://[^)]+\.woff2)\)", pick).group(1)
    DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(["curl", "-fsS", "-o", str(path_of(family)), woff], check=True)
    return path_of(family).stat().st_size


def main() -> int:
    if "--check" in sys.argv:
        total = 0
        for family in FACES:
            p = path_of(family)
            size = p.stat().st_size if p.is_file() else 0
            total += size
            print(f"{family:<15} {'missing' if not size else str(size) + ' bytes'}")
        print(f"{'embedded':<15} about {int(total * 4 / 3) // 1024} KB of base64 in every page")
        return 0 if total else 1
    for family in FACES:
        try:
            print(f"{family:<15} {fetch(family)} bytes")
        except (urllib.error.URLError, OSError, AttributeError, subprocess.CalledProcessError) as e:
            print(f"{family}: could not fetch, {e}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
