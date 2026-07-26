#!/usr/bin/env python3
"""Shared pieces of the walkthrough spec: refs, chips, ids, escaping.

A spec is one JSON file. Everything the page shows comes from it; the renderer
owns all markup. Two small conventions travel through the text fields:

    {formmap.go:50}     a code chip, resolved against repo.root and linked
    `backtick`          inline code, left as monospace, never linked
"""

from __future__ import annotations

import json
import re
from pathlib import Path

CHIP_RE = re.compile(r"\{([A-Za-z0-9_./\-]+\.[A-Za-z0-9]+:\d+)\}")
CODE_RE = re.compile(r"`([^`]+)`")
NAV_VERBS = re.compile(r"^(open|click|cmd-click|scroll|back|line|go to|jump)\b", re.I)
BLOCK_TYPES = {
    "switch", "stepper", "dial", "bind", "race", "ledger",
    "probe", "map", "space", "angle", "stack", "chain", "raw",
}


def esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def expand_root(root: str) -> Path:
    return Path(root).expanduser().resolve()


def ref_parts(ref: str) -> tuple[str, int]:
    """`app/x/formmap.go:50` -> ("app/x/formmap.go", 50). Bare names allowed too."""
    if ":" in ref and ref.rsplit(":", 1)[1].isdigit():
        path, line = ref.rsplit(":", 1)
        return path, int(line)
    return ref, 0


def find_file(root: Path, path: str) -> Path | None:
    """Accept a full relative path, or just a basename we can locate once."""
    direct = root / path
    if direct.is_file():
        return direct
    if "/" not in path:
        hits = [p for p in root.rglob(path) if p.is_file() and ".git" not in p.parts]
        if len(hits) == 1:
            return hits[0]
    return None


def ref_href(repo: dict, ref: str) -> str | None:
    """Absolute editor URI for a chip, or None when the file cannot be found."""
    path, line = ref_parts(ref)
    hit = find_file(expand_root(repo["root"]), path)
    if not hit:
        return None
    scheme = repo.get("editor", "cursor")
    return f"{scheme}://file{hit}:{line}" if line else f"{scheme}://file{hit}"


def chip(repo: dict, ref: str, label: str | None = None) -> str:
    """One code chip. Always an anchor when the file resolves, never bare text."""
    label = label or Path(ref_parts(ref)[0]).name
    if ref_parts(ref)[1]:
        label = f"{Path(ref_parts(ref)[0]).name}:{ref_parts(ref)[1]}"
    href = ref_href(repo, ref)
    if not href:
        return f'<span class="path">{esc(label)}</span>'
    return f'<a class="path" href="{esc(href)}">{esc(label)}</a>'


def inline(repo: dict, text: str) -> str:
    """Escape first, then expand {chips} and `code`. Never returns raw user html."""
    out = esc(text)
    out = CHIP_RE.sub(lambda m: chip(repo, m.group(1)), out)
    out = CODE_RE.sub(lambda m: f"<code>{m.group(1)}</code>", out)
    return out


def pretty(value) -> str:
    """Records and payloads are always indented, one field per line."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return value
    return json.dumps(value, indent=2, ensure_ascii=False)


def tint_json(escaped: str) -> str:
    """Colour the keys of an already-escaped json block."""
    return re.sub(r"(&quot;(?:[^&]|&(?!quot;))*?&quot;)(\s*:)", r'<span class="jk">\1</span>\2', escaped)


def json_block(value) -> str:
    return f'<pre class="rec"><code>{tint_json(esc(pretty(value)))}</code></pre>'


def stop_anchor(stop_id: str, part: str = "") -> str:
    return f"{stop_id}.{part}" if part else stop_id


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path: Path, spec: dict) -> None:
    Path(path).write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
