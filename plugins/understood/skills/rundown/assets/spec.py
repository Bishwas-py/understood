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



R_RENDER = {"path": "assets/render.py", "symbol": "render", "pattern": r"^def render\(", "line": 0}
R_CHECK = {"path": "assets/validate.py", "symbol": "check_ref", "pattern": "^def check_ref", "line": 0}
R_HOME = {"path": "assets/store.py", "symbol": "Home", "pattern": "^class Home", "line": 0}
R_SPLIT = {"path": "assets/serve.py", "symbol": "split_path", "pattern": "^def split_path", "line": 0}
R_WALK = {"path": "assets/spec.py", "symbol": "walk_refs", "pattern": "^def walk_refs", "line": 0}
R_READ = {"path": "assets/template.html", "symbol": "readSelection", "pattern": "function readSelection", "line": 0}
R_SVG = {"path": "assets/mermaid.py", "symbol": "to_svg", "pattern": "^def to_svg", "line": 0}
R_RAIL = {"path": "assets/template.html", "symbol": "layoutRail", "pattern": "function layoutRail", "line": 0}

# What every block takes. One declaration, three readers: `rundown blocks` prints
# it, the validator holds configs to it, and the demo page is built from the
# examples, so a shape cannot drift from the code that renders it.
BLOCK_SHAPE = {
    "switch": {
        "does": "a fix or decision toggled in and out of existence",
        "required": ["on"],
        "optional": ["ref", "label", "off"],
        "example": {
            "type": "switch", "ref": R_CHECK, "label": "pattern",
            "on": {
                "state": "in the build",
                "lines": ["the ref carries a pattern", "the code moves nine lines down"],
                "result": {"text": "the line is repaired,", "note": "and written back to the spec", "tone": "good"},
            },
            "off": {
                "state": "taken out",
                "lines": ["only a line number is stored", "the code moves nine lines down"],
                "result": {"text": "the chip opens the wrong line,", "note": "in front of the reviewer", "tone": "bad"},
            },
        },
    },
    "stepper": {
        "does": "one real value driven through its moments",
        "required": ["moments"],
        "optional": ["ref"],
        "example": {
            "type": "stepper",
            "moments": [
                {"text": "the old spec is copied to `history/`, stamped to the second", "chip": R_HOME},
                {"text": "then the new one is written, one field per line", "chip": R_WALK},
            ],
        },
    },
    "dial": {
        "does": "a tuned constant dragged, with the shipped value marked",
        "required": ["zones"],
        "optional": ["ref", "name", "min", "max", "step", "value", "decimals", "readout"],
        "example": {
            "type": "dial", "ref": R_HOME, "name": "KEEP", "min": 0, "max": 60, "step": 1,
            "value": 20, "decimals": 0, "readout": "{v} snapshots kept per rundown",
            "zones": [
                {"upto": 2, "verdict": "no undo worth having", "tone": "bad"},
                {"upto": 40, "verdict": "a week of edits, cheap on disk", "tone": "good"},
                {"upto": 60, "verdict": "a directory nobody opens", "tone": "bad"},
            ],
        },
    },
    "bind": {
        "does": "an artifact whose clauses glow with their meaning",
        "required": ["artifact", "pairs"],
        "optional": ["ref"],
        "example": {
            "type": "bind", "ref": R_RENDER,
            "artifact": '{\n  "id": "s2",\n  "headline": "a pattern outranks the line number"\n}',
            "pairs": [
                {"clause": '"id": "s2"', "name": "id", "meaning": "what a question, a card, and its thread hang off"},
                {"clause": '"headline"', "name": "headline", "meaning": "the claim this stop proves"},
            ],
        },
    },
    "race": {
        "does": "two runs at one row, with the guard and without it",
        "required": ["toggle", "row", "with"],
        "optional": ["ref", "without"],
        "example": {
            "type": "race",
            "toggle": {"label": "the folder is the identity", "ref": R_HOME},
            "row": {"id": "888c4b73", "question": "does it reach the right folder?"},
            "with": [
                {"text": "page.html overwritten in place"},
                {"text": "questions.jsonl untouched", "tone": "good"},
            ],
            "without": [
                {"text": "rendered to a new filename"},
                {"text": "the whole thread is orphaned", "tone": "bad"},
            ],
        },
    },
    "ledger": {
        "does": "an invariant the reader presses until it refuses",
        "required": ["actions"],
        "optional": ["ref", "empty", "countLabel", "invariant"],
        "example": {
            "type": "ledger", "ref": R_HOME, "empty": "no snapshot yet",
            "countLabel": "snapshots", "invariant": "no write lands without one",
            "actions": [
                {"label": "save the spec", "creates": {"history": "2026-07-26T11-21-09.json"}, "says": "copied first, then written", "tone": "good"},
                {"label": "restore it", "needsRow": True, "refuses": "nothing to restore, save one first",
                 "sets": {"restored": True}, "says": "the snapshot is back in place", "tone": "good"},
            ],
        },
    },
    "probe": {
        "does": "real inputs fed in, one branch lighting per input",
        "required": ["inputs"],
        "optional": ["ref"],
        "example": {
            "type": "probe", "ref": R_CHECK,
            "inputs": [
                {"label": "pattern still matches", "route": "line kept, page ships", "tone": "good",
                 "fields": {"ref says": "43", "pattern finds": "43"}},
                {"label": "the file is gone", "route": "build error, nothing is served", "tone": "bad",
                 "fields": {"path": "assets/serve.py", "found": ""}},
            ],
        },
    },
    "map": {
        "does": "the parts and who owns them, structure rather than sequence",
        "required": ["nodes"],
        "optional": ["ref"],
        "example": {
            "type": "map",
            "nodes": [
                {"label": "spec.json", "note": "the truth", "ref": R_WALK},
                {"label": "render.py", "note": "owns every tag", "ref": R_RENDER},
                {"label": "page.html", "note": "build output", "ref": R_RAIL},
            ],
        },
    },
    "flow": {
        "does": "the whole journey as a real flowchart, every node a code ref",
        "required": ["mermaid"],
        "optional": ["refs", "caption"],
        "example": {
            "type": "flow",
            "mermaid": "flowchart TD\n    A[select, press Ask] --> B{which slug}\n    B -->|first segment| C[(questions.jsonl)]\n    C --> A",
            "refs": {"A": R_READ, "B": R_SPLIT, "C": R_HOME},
            "caption": "asked from one rundown, landed in that rundown's file",
        },
    },
    "space": {
        "does": "a query embedded, the nearest points lighting with scores",
        "required": ["points", "queries"],
        "optional": ["ref", "w", "h"],
        "example": {
            "type": "space", "ref": R_SVG, "w": 320, "h": 190,
            "points": [
                {"label": "spec.json", "x": 60, "y": 60},
                {"label": "render.py", "x": 190, "y": 90},
                {"label": "serve.py", "x": 250, "y": 150},
            ],
            "queries": [
                {"label": "where does a tag come from", "star": [180, 80], "scores": [0.41, 0.88, 0.33], "top": 2},
                {"label": "who answers a request", "star": [245, 140], "scores": [0.29, 0.44, 0.91], "top": 2},
            ],
        },
    },
    "angle": {
        "does": "cosine as an angle the reader drags past the shipped gate",
        "required": ["zones"],
        "optional": ["ref", "gate", "start", "note"],
        "example": {
            "type": "angle", "ref": R_SVG, "gate": 0.35, "start": 20,
            "note": "the gate is the value in the code, not a round number",
            "zones": [
                {"above": 0.7, "text": "the same thing, said twice", "tone": "good"},
                {"above": 0.35, "text": "related, worth returning", "tone": "good"},
                {"above": -1, "text": "below the gate, dropped", "tone": "bad"},
            ],
        },
    },
    "stack": {
        "does": "a context window assembled part by part against a budget",
        "required": ["parts", "budget"],
        "optional": ["ref", "fits", "over"],
        "example": {
            "type": "stack", "ref": R_RENDER, "budget": 8000,
            "fits": "fits, the page stays one file",
            "over": "over budget, the model truncates",
            "parts": [
                {"label": "the spec", "tokens": 2400, "on": True},
                {"label": "the template", "tokens": 5200, "on": True},
                {"label": "every asset", "tokens": 9000},
            ],
        },
    },
    "chain": {
        "does": "a call path or a value's origin, hop by hop, forward or backward",
        "required": ["hops"],
        "optional": ["ref", "runLabel", "seed"],
        "example": {
            "type": "chain", "runLabel": "send it through", "seed": 'one real question, "hey",',
            "hops": [
                {"label": "pointerup", "out": "two characters minimum",
                 "desc": "a chip appears only for a real selection", "chip": R_READ},
                {"label": "POST", "out": "888c4b73",
                 "desc": "the record carries its stop, block, and part", "chip": R_SPLIT},
            ],
        },
    },
    "raw": {
        "does": "markup with no behaviour, for the shape no block covers",
        "required": ["html"],
        "optional": [],
        "example": {"type": "raw", "html": '<div class="ba"><div class="b"><b>BEFORE</b> one port per page</div>'
                                          '<div class="a"><b>AFTER</b> one origin for all of them</div></div>'},
    },
}


BLOCK_SHAPE["table"] = {
    "does": "rows of evidence, sortable, each carrying its own verdict",
    "required": ["columns", "rows"],
    "optional": ["ref", "title", "note", "foot", "filters"],
    "example": {
        "type": "table", "ref": R_CHECK, "title": "six live probes",
        "note": "27.07.2026, top five slots",
        "columns": [
            {"key": "asked", "label": "asked"},
            {"key": "back", "label": "what came back", "mono": True},
            {"key": "truth", "label": "the truth", "mono": True},
            {"key": "verdict", "label": "verdict", "verdict": True},
        ],
        "rows": [
            {"asked": "what was the net salary?", "back": "not found", "truth": "88'554.70",
             "verdict": "lost", "tone": "bad"},
            {"asked": "Kinderbetreuung Kosten", "back": "17'280.00", "truth": "17'280.00",
             "verdict": "exact", "tone": "good"},
        ],
        "filters": ["lost", "exact"],
        "foot": "the three that lost never saw a document at all",
    },
}
BLOCK_SHAPE["bar"] = {
    "does": "one measure split into its parts, so a ratio is seen rather than worked out",
    "required": ["parts"],
    "optional": ["ref", "note"],
    "example": {
        "type": "bar", "ref": R_CHECK, "note": "98% of what it answered, 68% of what was wanted",
        "parts": [
            {"label": "answered and right", "value": 48, "tone": "good"},
            {"label": "answered and wrong", "value": 1, "tone": "bad"},
            {"label": "never asked", "value": 23, "tone": "absent"},
        ],
    },
}

BLOCK_TYPES = set(BLOCK_SHAPE)

# A rundown is one of two kinds. A change is defended; an issue is evidenced.
KINDS = ("change", "issue")
STATES = ("open", "agreed", "closed", "holds")
SEVERITIES = ("s1", "s2", "s3", "ok")

# One glyph per idea, drawn from lucide and inlined at build time. The names on
# the left are what a spec says; the names on the right are what iconify serves.
ICONS = {
    "s1": "triangle-alert", "s2": "circle-alert", "s3": "circle-alert", "ok": "circle-check",
    "open": "circle-dot", "agreed": "handshake", "closed": "badge-check", "holds": "circle-check",
    "says": "file-text", "filed": "terminal", "differs": "git-compare", "why": "circle-question-mark",
    "carry": "target", "knobs": "sliders-horizontal", "cost": "list-ordered", "ask": "circle-question-mark",
    "table": "table-2", "bar": "gauge", "trace": "move-right", "good": "circle-check", "bad": "circle-alert",
    "search": "file-search", "sort": "arrow-right", "page": "file-text", "form": "clipboard-list",
    "model": "sparkles", "row": "table-2", "magnet": "magnet",
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
