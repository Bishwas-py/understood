#!/usr/bin/env python3
"""Check a rundown spec against the repo and against the skill's rules.

Every line number in a rundown is a promise, so this runs before a page is
ever served. Errors fail the build; warnings are printed and let it through.

    python3 validate.py path/to/rundown.json
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from spec import (BLOCK_SHAPE, CHIP_RE, EM_DASH, KINDS, NAV_VERBS, SEVERITIES, STATES,
                  expand_root, find_file, load, pattern_lines, read_lines, ref_parts, ref_str,
                  save, walk_refs)



class Report:
    def __init__(self):
        self.items: list[tuple[str, str, str]] = []

    def error(self, where: str, msg: str) -> None:
        self.items.append(("error", where, msg))

    def warn(self, where: str, msg: str) -> None:
        self.items.append(("warn", where, msg))

    @property
    def errors(self):
        return [i for i in self.items if i[0] == "error"]

    def print(self) -> None:
        for level, where, msg in self.items:
            mark = "FAIL" if level == "error" else "warn"
            print(f"  {mark}  {where}: {msg}")
        if not self.items:
            print("  ok, no findings")


def check_ref(rep: Report, repo: dict, where: str, ref) -> None:
    """A ref resolves to a real file, and its symbol really sits on that line."""
    if not isinstance(ref, dict):
        path, line = ref_parts(ref_str(ref))
        ref = {"path": path, "line": line}
    root = expand_root(repo["root"])
    hit = find_file(root, ref["path"])
    if not hit:
        rep.error(where, f"file not found under {root}: {ref['path']}")
        return
    line = int(ref.get("line") or 0)
    symbol = ref.get("symbol")
    pattern = ref.get("pattern")
    try:
        lines = read_lines(hit)
    except OSError as e:
        rep.error(where, f"cannot read {hit}: {e}")
        return
    if line and line > len(lines):
        rep.error(where, f"{ref['path']} has {len(lines)} lines, ref points at {line}")
        return
    text = lines[line - 1] if line else ""
    # The pattern is the authority when present: a symbol's first occurrence is
    # often a call site, while the pattern names the definition.
    if pattern:
        try:
            hits = pattern_lines(lines, pattern)
        except re.error as e:
            rep.error(where, f"bad pattern {pattern!r}: {e}")
            return
        if not hits:
            rep.error(where, f"pattern {pattern!r} matches nothing in {ref['path']}")
        elif line and line not in hits:
            rep.error(where, f"ref says line {line}, pattern matches {hits[0]} in {ref['path']}")
        return
    if symbol and line and symbol not in text:
        found = next((i + 1 for i, l in enumerate(lines) if symbol in l), None)
        if found:
            rep.error(where, f"{symbol} is not on line {line} of {ref['path']}, it is on {found}")
        else:
            rep.error(where, f"{symbol} does not appear in {ref['path']}")


def check_block(rep: Report, repo: dict, where: str, block: dict) -> None:
    """A block is held to its declared shape, so a mistyped key is a build error
    rather than a control that renders and then does nothing."""
    btype = block.get("type")
    shape = BLOCK_SHAPE.get(btype)
    if not shape:
        rep.error(where, f"unknown block type {btype!r}, one of: {', '.join(sorted(BLOCK_SHAPE))}")
        return
    for key in shape["required"]:
        if block.get(key) in (None, "", [], {}):
            rep.error(where, f"a {btype} needs {key}, see: rundown blocks {btype}")
    known = {"type", *shape["required"], *shape["optional"]}
    for key in block:
        if key not in known:
            rep.warn(where, f"a {btype} has no {key!r}, so it is ignored, see: rundown blocks {btype}")
    for key in ("label", "title", "caption", "runLabel", "invariant"):
        if isinstance(block.get(key), str):
            check_text(rep, repo, f"{where}.{key}", block[key])
    if btype == "flow":
        check_chart(rep, where, block)


def check_chart(rep: Report, where: str, block: dict) -> None:
    """A chart that parses to nothing renders as an empty panel and says nothing
    about why, so it is refused at build time instead."""
    import mermaid

    _, nodes, edges = mermaid.parse(block.get("mermaid", ""))
    if not nodes:
        rep.error(where, "the mermaid chart has no nodes, check the flowchart line and the shapes")
        return
    if not edges and len(nodes) > 1:
        rep.warn(where, "the chart has nodes but no edges, so nothing points at anything")
    for key in block.get("refs") or {}:
        if key not in nodes:
            rep.warn(where, f"refs.{key} names no node in the chart, so nothing links to it")


SOLVING = re.compile(
    r"\b(the (cheap|obvious|right|quick) fix|we should|you should|just |simply |i (would|d) (add|change|use))\b", re.I
)


def check_kind(rep: Report, spec: dict) -> None:
    """An issue page evidences, a change page defends. They owe different things."""
    kind = spec.get("kind", "change")
    if kind not in KINDS:
        rep.error("spec", f"kind must be one of {', '.join(KINDS)}, not {kind!r}")
        return
    if kind != "issue":
        for stage in spec.get("stages") or []:
            for stop in stage.get("stops") or []:
                for key in ("severity", "state", "receipt", "knobs", "carry"):
                    if stop.get(key):
                        rep.warn(stop.get("id", "stop"), f"{key} only means something on kind: issue")
        return

    for stage in spec.get("stages") or []:
        for stop in stage.get("stops") or []:
            sid = stop.get("id", "stop")
            if stop.get("state") not in STATES:
                rep.error(sid, f"a finding needs a state, one of {', '.join(STATES)}")
            if stop.get("severity") and stop["severity"] not in SEVERITIES:
                rep.error(sid, f"severity must be one of {', '.join(SEVERITIES)}")
            if not stop.get("why") and stop.get("state") != "holds":
                rep.warn(sid, "no why, so the page shows a symptom and never its mechanism")
            if not stop.get("carry") and stop.get("state") != "holds":
                rep.warn(sid, "no carry line, so nothing here survives past this filing")
            for i, k in enumerate(stop.get("knobs") or []):
                if not k.get("what") or not k.get("does"):
                    rep.error(f"{sid}.knobs[{i}]", "a knob needs what it is and what it does today")
                if SOLVING.search(str(k.get("does", ""))):
                    rep.error(f"{sid}.knobs[{i}]",
                              "this reads as a recommendation. Say what the control does today, not what to do with it")
            for key in ("why", "carry"):
                if stop.get(key):
                    check_text(rep, spec.get("repo") or {}, f"{sid}.{key}", stop[key])
            if stop.get("carry") and SOLVING.search(stop["carry"]):
                rep.error(f"{sid}.carry", "a carry line is a rule that outlives this page, never a fix")
    stops = {s.get("id") for stage in spec.get("stages") or [] for s in stage.get("stops") or []}
    for i, row in enumerate(spec.get("cost") or []):
        for key in ("what", "stop"):
            if not row.get(key):
                rep.error(f"cost[{i}]", f"a cost row needs {key}")
        # a cost row is a link into the page, so it has to land somewhere
        if row.get("stop") and row["stop"] not in stops:
            rep.error(f"cost[{i}]", f"stop {row['stop']!r} is not on this page, the link goes nowhere")


def check_text(rep: Report, repo: dict, where: str, text: str) -> None:
    if EM_DASH in text:
        rep.error(where, "em-dash in page text, use a comma, period, or parentheses")
    for m in CHIP_RE.finditer(text):
        check_ref(rep, repo, f"{where} chip", m.group(1))


def check_claim(rep: Report, repo: dict, where: str, claim: str) -> None:
    check_text(rep, repo, where, claim)
    if NAV_VERBS.match(claim.strip()):
        rep.error(where, f"starts with a navigation verb, state a finding instead: {claim!r}")
    stripped = CHIP_RE.sub("", claim).strip(" ,.:")
    if not stripped:
        rep.error(where, "is only a code reference, a claim needs a finding")
    elif CHIP_RE.search(claim):
        rep.warn(where, "holds a code reference; locations usually belong in the proofs")


def validate(spec: dict) -> Report:
    rep = Report()
    repo = spec.get("repo") or {}
    if not repo.get("root"):
        rep.error("repo", "missing repo.root")
        return rep
    if not expand_root(repo["root"]).is_dir():
        rep.error("repo", f"root is not a directory: {repo['root']}")
        return rep
    if not repo.get("sha"):
        rep.warn("repo", "no commit sha pinned, drift cannot be dated")

    for key in ("id", "title", "stages"):
        if not spec.get(key):
            rep.error("spec", f"missing {key}")

    pipe = spec.get("pipeline") or {}
    for i, step in enumerate(pipe.get("steps") or []):
        check_text(rep, repo, f"pipeline.steps[{i}]", step.get("text", ""))

    seen_ids: set[str] = set()
    for si, stage in enumerate(spec.get("stages") or []):
        swhere = f"stages[{si}]"
        check_text(rep, repo, f"{swhere}.title", stage.get("title", ""))
        for pi, stop in enumerate(stage.get("stops") or []):
            sid = stop.get("id") or f"{swhere}.stops[{pi}]"
            if sid in seen_ids:
                rep.error(sid, "duplicate stop id")
            seen_ids.add(sid)
            head = stop.get("headline", "")
            if not head:
                rep.error(sid, "stop has no headline")
            else:
                check_claim(rep, repo, f"{sid}.headline", head)
            block = stop.get("block")
            if block:
                check_block(rep, repo, f"{sid}.block", block)
            for ti, think in enumerate(stop.get("think") or []):
                twhere = f"{sid}.think[{ti}]"
                claim = think.get("claim", "")
                if not claim:
                    rep.error(twhere, "think entry has no claim")
                else:
                    check_claim(rep, repo, f"{twhere}.claim", claim)
                for pi2, proof in enumerate(think.get("proofs") or []):
                    check_text(rep, repo, f"{twhere}.proofs[{pi2}]", proof)

    kinds = {
        (stop.get("block") or {}).get("type")
        for stage in spec.get("stages") or []
        for stop in stage.get("stops") or []
    }
    if "flow" not in kinds:
        rep.warn("spec", "no flow chart, so the reader never sees the journey in one picture")

    check_kind(rep, spec)

    seen_look: set[str] = set()
    for i, rule in enumerate(spec.get("look") or []):
        where = f"look[{i}]"
        for key in ("id", "sel", "css"):
            if not isinstance(rule.get(key), str) or not rule[key].strip():
                rep.error(where, f"look rule needs a {key}")
        if rule.get("id") in seen_look:
            rep.error(where, f"duplicate look id {rule['id']!r}")
        seen_look.add(rule.get("id"))
        # css never needs a <, and one would end the style tag early
        if "<" in rule.get("sel", "") or "<" in rule.get("css", ""):
            rep.error(where, "look rule holds a <, which cannot survive a style tag")
        if "}" in rule.get("css", ""):
            rep.error(where, "look rule css closes its own block, write declarations only")

    for where, container, key in walk_refs(spec):
        check_ref(rep, repo, where, container[key])

    for qi, q in enumerate(spec.get("discussion") or []):
        for entry in [q] + list(q.get("replies") or []):
            if entry.get("answer"):
                check_text(rep, repo, f"discussion[{qi}].answer", entry["answer"])
    return rep


def resync(spec: dict) -> list[str]:
    """Move every ref that carries a pattern back onto the line the pattern finds.
    Code moves; a rundown should follow it rather than lie about it."""
    root = expand_root(spec["repo"]["root"])
    moved = []
    for where, container, key in walk_refs(spec):
        ref = container[key]
        if not isinstance(ref, dict) or not ref.get("pattern"):
            continue
        hit = find_file(root, ref["path"])
        if not hit:
            continue
        try:
            hits = pattern_lines(read_lines(hit), ref["pattern"])
        except (re.error, OSError):
            continue
        if hits and hits[0] != ref.get("line"):
            moved.append(f"{where}: {ref['path']} {ref.get('line')} -> {hits[0]}")
            ref["line"] = hits[0]
    return moved


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    fix = "--fix" in sys.argv
    if not args:
        print(__doc__)
        return 2
    path = Path(args[0])
    spec = load(path)
    if fix:
        moved = resync(spec)
        for line in moved:
            print(f"  moved {line}")
        if moved:
            save(path, spec)
    rep = validate(spec)
    print(f"validating {path.name}")
    rep.print()
    return 1 if rep.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
