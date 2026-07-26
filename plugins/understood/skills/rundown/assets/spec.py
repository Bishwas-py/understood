#!/usr/bin/env python3
"""Shared pieces of the rundown spec: refs, chips, ids, escaping.

A spec is one JSON file. Everything the page shows comes from it; the renderer
owns all markup. Two small conventions travel through the text fields:

    {formmap.go:50}     a code chip, resolved against repo.root and linked
    `backtick`          inline code, left as monospace, never linked
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from html import escape
from pathlib import Path

CHIP_RE = re.compile(r"\{([A-Za-z0-9_./\-]+\.[A-Za-z0-9]+:\d+)\}")
CODE_RE = re.compile(r"`([^`]+)`")
EM_DASH = "\u2014"
NAV_VERBS = re.compile(r"^(open|click|cmd-click|scroll|back|line|go to|jump)\b", re.I)
BLOCK_TYPES = {
    "switch", "stepper", "dial", "bind", "race", "ledger",
    "probe", "map", "flow", "space", "angle", "stack", "chain", "raw",
}


def esc(text: str) -> str:
    return escape(str(text))


@lru_cache(maxsize=None)
def expand_root(root: str) -> Path:
    return Path(root).expanduser().resolve()


def ref_parts(ref: str) -> tuple[str, int]:
    """`app/x/formmap.go:50` -> ("app/x/formmap.go", 50). Bare names allowed too."""
    if ":" in ref and ref.rsplit(":", 1)[1].isdigit():
        path, line = ref.rsplit(":", 1)
        return path, int(line)
    return ref, 0


@lru_cache(maxsize=None)
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


def ref_href(repo: dict, ref) -> str | None:
    """Absolute editor URI for a chip, or None when the file cannot be found."""
    path, line = ref_parts(ref_str(ref))
    hit = find_file(expand_root(repo["root"]), path)
    if not hit:
        return None
    scheme = repo.get("editor", "cursor")
    return f"{scheme}://file{hit}:{line}" if line else f"{scheme}://file{hit}"


def ref_str(ref) -> str:
    """A ref is either "path:line" or {path, line, ...}; this is the string form."""
    if isinstance(ref, str):
        return ref
    line = ref.get("line") or 0
    return f'{ref["path"]}:{line}' if line else ref["path"]


def ref_label(ref) -> str:
    """What a chip for this ref says: the basename, with its line when it has one."""
    path, line = ref_parts(ref_str(ref))
    return f"{Path(path).name}:{line}" if line else Path(path).name


def chip(repo: dict, ref) -> str:
    """One code chip. Always an anchor when the file resolves, never bare text."""
    label = ref_label(ref)
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


def walk_refs(spec: dict):
    """Yield (where, container, key) for every ref in a spec, at any depth.

    A ref is a promise, so validation, resync, and rendering must all see the
    same set. They used to disagree: stop refs were checked, and the ones a
    block emits were not.
    """
    pipe = spec.get("pipeline") or {}
    for i, step in enumerate(pipe.get("steps") or []):
        if step.get("ref"):
            yield f"pipeline.steps[{i}].ref", step, "ref"
    for si, stage in enumerate(spec.get("stages") or []):
        for pi, stop in enumerate(stage.get("stops") or []):
            sid = stop.get("id") or f"stages[{si}].stops[{pi}]"
            if stop.get("ref"):
                yield f"{sid}.ref", stop, "ref"
            block = stop.get("block") or {}
            if block.get("ref"):
                yield f"{sid}.block.ref", block, "ref"
            if (block.get("toggle") or {}).get("ref"):
                yield f"{sid}.block.toggle.ref", block["toggle"], "ref"
            for key in ("hops", "moments"):
                for i, item in enumerate(block.get(key) or []):
                    if item.get("chip"):
                        yield f"{sid}.block.{key}[{i}].chip", item, "chip"
            for i, node in enumerate(block.get("nodes") or []):
                if node.get("ref"):
                    yield f"{sid}.block.nodes[{i}].ref", node, "ref"
            refs = block.get("refs") or {}
            for key in refs:
                yield f"{sid}.block.refs.{key}", refs, key


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path: Path, spec: dict) -> None:
    Path(path).write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_jsonl(path: Path, record: dict) -> None:
    """One record, one line. The only way anything is added to a jsonl here."""
    with Path(path).open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


@lru_cache(maxsize=None)
def read_lines(path: Path) -> list[str]:
    return Path(path).read_text(encoding="utf-8", errors="replace").splitlines()


def pattern_lines(lines: list[str], pattern: str) -> list[int]:
    """Line numbers a pattern matches, or a ValueError the caller can report."""
    rx = re.compile(pattern)
    return [i + 1 for i, l in enumerate(lines) if rx.search(l)]
