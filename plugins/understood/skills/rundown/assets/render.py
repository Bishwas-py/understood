#!/usr/bin/env python3
"""Compile a rundown spec into one self-contained HTML file.

    python3 render.py rundown.json out.html

The spec holds content; this file owns every tag, id, and class the page uses.
Blocks are emitted with their initial state already drawn, plus a config the
page's runtime reads to wire the interaction, so the page still reads with
javascript off and prints correctly.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import mermaid
import fonts
from icons import icon, sprite
from spec import (BLOCK_TYPES, EM_DASH, chip, esc, expand_root, inline, json_block, load,
                  pretty, ref_href, ref_label)

HERE = Path(__file__).resolve().parent


# --------------------------------------------------------------------------- blocks

def deep_inline(repo: dict, value):
    """Configs are read by the runtime and written with innerHTML, so their text
    is expanded here: {chips} become links, `code` becomes code, once, at build."""
    if isinstance(value, str):
        return inline(repo, value)
    if isinstance(value, list):
        return [deep_inline(repo, v) for v in value]
    if isinstance(value, dict):
        # "chip" is already rendered html, the rest is source text.
        return {k: (v if k in ("type", "tone", "ref", "chip") else deep_inline(repo, v))
                for k, v in value.items()}
    return value


def _cfg(kind: str, repo: dict, cfg: dict, inner: str, stop_id: str) -> str:
    # Script content is raw text, never entity-decoded, so the json must not be
    # html-escaped. Only the tag-closing sequence needs neutralising.
    payload = json.dumps(deep_inline(repo, cfg), ensure_ascii=False).replace("</", "<\\/")
    return (
        f'<div class="blk" data-block="{kind}" data-stop="{stop_id}">'
        f'<script type="application/json" class="blk-cfg">{payload}</script>'
        f"{inner}</div>"
    )


def _ref(repo: dict, c: dict) -> str:
    """A block's own chip, or nothing. Eight blocks used to inline this."""
    return chip(repo, c["ref"]) if c.get("ref") else ""


def _chipped(repo: dict, c: dict, key: str) -> dict:
    """Pre-render the chips a runtime writes with innerHTML, once, at build."""
    items = [dict(i, chip=chip(repo, i["chip"]) if i.get("chip") else "") for i in c.get(key, [])]
    return dict(c, **{key: items})


def b_switch(repo, sid, c):
    on = c.get("on", {})
    lines = "".join(f'<div class="ln">{inline(repo, l)}</div>' for l in on.get("lines", []))
    res = on.get("result", {})
    toggle = '<button class="tgl" type="button" aria-pressed="true"><span class="knob"></span></button>'
    label = f'<code>{esc(c["label"])}</code>' if c.get("label") else ""
    head = (
        f'<div class="blk-head">{toggle}{_ref(repo, c)} {label}'
        f'<span class="state">{esc(on.get("state", "in the build"))}</span></div>'
    )
    body = (
        f'<div class="blk-body">{lines}'
        f'<div class="res">{inline(repo, res.get("text", ""))} '
        f'<span class="tone-{res.get("tone", "good")}">{inline(repo, res.get("note", ""))}</span></div></div>'
    )
    return _cfg("switch", repo, c, head + body, sid)


def b_race(repo, sid, c):
    t = c.get("toggle", {})
    head = (
        '<div class="blk-head"><button class="btn primary run" type="button">run the race</button>'
        '<label class="lock"><input type="checkbox" checked> '
        + (_ref(repo, t))
        + f' <code>{esc(t.get("label", "lock"))}</code></label></div>'
    )
    row = f'<div class="blk-body"><div class="row">{esc(pretty(c.get("row", {})))}</div><div class="log"></div></div>'
    return _cfg("race", repo, c, head + row, sid)


def b_chain(repo, sid, c):
    c = _chipped(repo, c, "hops")
    hops = "".join(
        f'<span class="hop" data-i="{i}">{esc(h.get("label", ""))}</span>'
        + ('<span class="arw">&rArr;</span>' if i < len(c.get("hops", [])) - 1 else "")
        for i, h in enumerate(c.get("hops", []))
    )
    head = (
        '<div class="blk-head"><button class="btn primary run" type="button">'
        f'{esc(c.get("runLabel", "send it through"))}</button>'
        '<span class="hint">click a hop, or run the whole flow</span><span class="ref"></span></div>'
    )
    body = (
        f'<div class="blk-body"><div class="hops">{hops}</div>'
        f'<div class="val"><span class="k">the value now</span> <span class="v">{esc(c.get("seed", ""))}</span></div>'
        '<div class="desc"></div></div>'
    )
    return _cfg("chain", repo, c, head + body, sid)


def b_dial(repo, sid, c):
    val = c.get("value", 0)
    head = (
        '<div class="blk-head">'
        + _ref(repo, c)
        + f' <code>{esc(c.get("name", "value"))} = <b class="dv">{val}</b></code>'
        f'<input class="rng" type="range" min="{c.get("min", 0)}" max="{c.get("max", 100)}" '
        f'step="{c.get("step", 1)}" value="{val}"></div>'
    )
    body = f'<div class="blk-body"><div class="read">{inline(repo, c.get("readout", ""))}</div><div class="verdict"></div></div>'
    return _cfg("dial", repo, c, head + body, sid)


def b_probe(repo, sid, c):
    ins = "".join(
        f'<button class="btn mono in" type="button" data-i="{i}">{esc(i_["label"])}</button>'
        for i, i_ in enumerate(c.get("inputs", []))
    )
    head = f'<div class="blk-head"><span class="hint">feed:</span>{ins}' + _ref(repo, c) + "</div>"
    body = '<div class="blk-body"><div class="route">press an input</div><div class="fields"></div></div>'
    return _cfg("probe", repo, c, head + body, sid)


def b_bind(repo, sid, c):
    pairs = c.get("pairs", [])
    rest, parts = c.get("artifact", ""), []
    for i, pair in enumerate(pairs):
        clause = pair["clause"]
        head, _, rest = rest.partition(clause)
        parts.append(esc(head))
        parts.append(f'<span class="bd" data-k="{i}">{esc(clause)}</span>')
    parts.append(esc(rest))
    art = "".join(parts)
    items = "".join(
        f'<li class="bl" data-k="{i}"><b>{esc(p.get("name", ""))}</b> {inline(repo, p.get("meaning", ""))}</li>'
        for i, p in enumerate(pairs)
    )
    body = f'<div class="blk-body"><pre class="art"><code>{art}</code></pre><ul class="plain">{items}</ul></div>'
    return _cfg("bind", repo, c, body, sid)


def b_ledger(repo, sid, c):
    btns = "".join(
        f'<button class="btn{" primary" if i == 0 else ""} act" type="button" data-i="{i}">{esc(a["label"])}</button>'
        for i, a in enumerate(c.get("actions", []))
    )
    head = f'<div class="blk-head">{btns}' + _ref(repo, c) + "</div>"
    body = (
        f'<div class="blk-body"><div class="row">{esc(c.get("empty", "nothing yet"))}</div>'
        f'<div class="count"><b>{esc(c.get("countLabel", "rows"))}: <span class="n">0</span></b> '
        f'<span class="tone-good">{inline(repo, c.get("invariant", ""))}</span></div>'
        '<div class="log"></div></div>'
    )
    return _cfg("ledger", repo, c, head + body, sid)


def b_stepper(repo, sid, c):
    c = _chipped(repo, c, "moments")
    head = (
        '<div class="blk-head"><button class="btn prev" type="button">&larr;</button>'
        '<button class="btn primary next" type="button">next &rarr;</button>'
        '<span class="dots"></span><span class="ref"></span></div>'
    )
    return _cfg("stepper", repo, c, head + '<div class="blk-body"><div class="moment"></div></div>', sid)


def b_map(repo, sid, c):
    nodes = []
    for i, n in enumerate(c.get("nodes", [])):
        href = ""
        if n.get("ref"):
            h = ref_href(repo, n["ref"])
            href = f' href="{esc(h)}"' if h else ""
        tag = "a" if href else "span"
        nodes.append(
            f'<{tag} class="mapnode"{href} data-i="{i}"><b>{esc(n.get("label", ""))}</b>'
            + (f'<span>{esc(n.get("note", ""))}</span>' if n.get("note") else "")
            + f"</{tag}>"
        )
        if i < len(c.get("nodes", [])) - 1:
            nodes.append('<span class="arw">&rarr;</span>')
    return _cfg("map", repo, c, f'<div class="blk-body mapwrap">{"".join(nodes)}</div>', sid)


def b_space(repo, sid, c):
    pts = "".join(
        f'<circle class="pt" data-i="{i}" cx="{p["x"]}" cy="{p["y"]}" r="5"/>'
        f'<text x="{p["x"] + 8}" y="{p["y"] - 2}">{esc(p["label"])}</text>'
        for i, p in enumerate(c.get("points", []))
    )
    qs = "".join(
        f'<button class="btn q" type="button" data-i="{i}">{esc(q["label"])}</button>'
        for i, q in enumerate(c.get("queries", []))
    )
    head = f'<div class="blk-head"><span class="hint">embed the query:</span>{qs}' + _ref(repo, c) + "</div>"
    body = (
        f'<div class="blk-body"><svg class="space" viewBox="0 0 {c.get("w", 320)} {c.get("h", 190)}">'
        f'{pts}<text class="star" x="-20" y="-20">&#9733;</text></svg>'
        '<div class="read">press a query</div></div>'
    )
    return _cfg("space", repo, c, head + body, sid)


def b_angle(repo, sid, c):
    head = (
        '<div class="blk-head">'
        + _ref(repo, c)
        + f' <code>cos = <b class="cv">1.00</b></code>'
        f'<input class="rng" type="range" min="0" max="180" step="2" value="{c.get("start", 20)}"></div>'
    )
    body = (
        '<div class="blk-body anglewrap"><svg class="ang" viewBox="0 0 240 140">'
        '<path class="arc"/><line class="gate" x1="30" y1="120" x2="0" y2="0"/>'
        '<text class="gatelab">gate</text>'
        '<line class="qv" x1="30" y1="120" x2="130" y2="120"/><text class="qlab" x="112" y="133">query</text>'
        '<line class="pv" x1="30" y1="120" x2="0" y2="0"/><text class="plab"></text>'
        '<text class="deg"></text><circle cx="30" cy="120" r="3"/></svg>'
        '<div class="read"><div class="zone"></div>'
        f'<div class="note">{inline(repo, c.get("note", ""))}</div></div></div>'
    )
    return _cfg("angle", repo, c, head + body, sid)


def b_stack(repo, sid, c):
    parts = "".join(
        f'<label class="pt"><input type="checkbox" data-i="{i}"{" checked" if p.get("on") else ""}> '
        f'{esc(p["label"])}</label>'
        for i, p in enumerate(c.get("parts", []))
    )
    head = f'<div class="blk-head">{parts}' + _ref(repo, c) + "</div>"
    body = (
        '<div class="blk-body"><div class="bar"><div class="fill"></div></div>'
        f'<div class="read"><b class="tok">0</b> / {c.get("budget", 8000)} token budget '
        '<span class="verdict"></span></div></div>'
    )
    return _cfg("stack", repo, c, head + body, sid)


def b_flow(repo, sid, c):
    """A mermaid flowchart, drawn to svg at build time so the page stays one file."""
    hrefs = {}
    for key, ref in (c.get("refs") or {}).items():
        href = ref_href(repo, ref)
        if href:
            hrefs[key] = href
    svg = mermaid.to_svg(c.get("mermaid", ""), hrefs)
    cap = f'<p class="cap">{inline(repo, c["caption"])}</p>' if c.get("caption") else ""
    return f'<div class="blk flow" data-block="flow" data-stop="{sid}"><div class="blk-body">{svg}{cap}</div></div>'


def b_table(repo, sid, c):
    """Rows of evidence. Sortable, filterable from its own head, one verdict each."""
    cols = c.get("columns", [])
    head = "".join(
        '<th data-k="%d"%s>%s%s</th>' % (i, ' class="num"' if col.get("num") else "",
                                         esc(col.get("label", col["key"])), icon("sort"))
        for i, col in enumerate(cols)
    )
    body = []
    for r in c.get("rows", []):
        tone = r.get("tone", "")
        cells = []
        for col in cols:
            v = r.get(col["key"], "")
            if col.get("verdict"):
                cells.append(f'<td><span class="verdict-pill {esc(tone or "good")}">'
                             f'{icon("good" if tone == "good" else "bad")}{esc(v)}</span></td>')
            else:
                cls = " ".join(x for x in ("mono" if col.get("mono") else "", "num" if col.get("num") else "") if x)
                cells.append(f'<td class="{cls}">{inline(repo, str(v))}</td>')
        body.append(f'<tr class="{esc(tone)}" data-v="{esc(r.get("verdict", ""))}">{"".join(cells)}</tr>')
    filters = "".join(
        f'<button class="chipf{" on" if i == 0 else ""}" data-v="{esc(f)}">{esc(f)}</button>'
        for i, f in enumerate(["all", *c.get("filters", [])])
    ) if c.get("filters") else ""
    title = f'<span class="t-title">{esc(c["title"])}</span>' if c.get("title") else ""
    note = f'<span class="hint">{inline(repo, c["note"])}</span>' if c.get("note") else ""
    controls = f'<span class="t-filters">{filters}</span>' if filters else ""
    foot = f'<div class="tbl-foot"><span>{inline(repo, c["foot"])}</span></div>' if c.get("foot") else ""
    return (f'<div class="tbl-wrap"><div class="tbl-head">{icon("table")}{title}{note}{controls}'
            f'{_ref(repo, c)}</div><div class="tbl-scroll"><table class="ev">'
            f'<thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>{foot}</div>')


def b_bar(repo, sid, c):
    """One measure split into its parts, so a ratio is seen instead of worked out."""
    parts = c.get("parts", [])
    total = sum(float(p.get("value", 0)) for p in parts) or 1
    fills = "".join(f'<span class="{esc(p.get("tone", "good"))}" style="flex:{p.get("value", 0)}"></span>'
                    for p in parts)
    keys = "".join(
        f'<span><i class="sw {esc(p.get("tone", "good"))}"></i><b>{esc(p.get("value", 0))}</b> '
        f'{inline(repo, p.get("label", ""))}</span>' for p in parts
    )
    note = f'<span class="bar-note">{inline(repo, c["note"])}</span>' if c.get("note") else ""
    return (f'<div class="bars">{_ref(repo, c)}<div class="bar">{fills}</div>'
            f'<div class="bar-key">{keys}{note}</div></div>')


def b_raw(repo, sid, c):
    return f'<div class="blk" data-block="raw" data-stop="{sid}">{c.get("html", "")}</div>'


BLOCKS = {
    "switch": b_switch, "race": b_race, "chain": b_chain, "dial": b_dial,
    "probe": b_probe, "bind": b_bind, "ledger": b_ledger, "stepper": b_stepper,
    "map": b_map, "flow": b_flow, "space": b_space, "angle": b_angle, "stack": b_stack,
    "table": b_table, "bar": b_bar, "raw": b_raw,
}


assert set(BLOCKS) == BLOCK_TYPES, f"block registries disagree: {set(BLOCKS) ^ BLOCK_TYPES}"


# --------------------------------------------------------------------------- page

def think_html(repo: dict, stop_id: str, think: list) -> str:
    if not think:
        return ""
    items = []
    for i, t in enumerate(think, start=1):
        anchor = f'{stop_id}.think.{i}'
        claim = f'<b>{inline(repo, t.get("claim", ""))}</b>'
        proofs = t.get("proofs") or []
        if len(proofs) == 1:
            items.append(
                f'<li data-anchor="{anchor}">{claim} <span class="arw">&rarr;</span> {inline(repo, proofs[0])}</li>'
            )
        elif proofs:
            subs = "".join(f"<li>{inline(repo, p)}</li>" for p in proofs)
            items.append(f'<li data-anchor="{anchor}">{claim}<ul>{subs}</ul></li>')
        else:
            items.append(f'<li data-anchor="{anchor}">{claim}</li>')
    return f'<ul class="think">{"".join(items)}</ul>'


def receipt_html(repo: dict, r: dict) -> str:
    """What the source says, what the run did, and the difference. The difference
    is a phrase: an explanation belongs in why, not here."""
    rows = [
        ("said", "says", r.get("says"), r.get("saysFrom")),
        ("filed", "the run did", r.get("did"), r.get("didFrom")),
        ("delta", "what differs", r.get("differs"), r.get("differsFrom")),
    ]
    out = []
    for cls, label, value, note in rows:
        if not value:
            continue
        tail = f'<span class="from">{inline(repo, note)}</span>' if note else ""
        out.append(f'<div class="r-row {cls}"><b>{icon(label.split()[0] if cls != "delta" else "differs")}'
                   f'{esc(label)}</b><span class="v">{inline(repo, value)}{tail}</span></div>')
    return f'<div class="receipt">{"".join(out)}</div>' if out else ""


def why_html(repo: dict, text: str) -> str:
    """The mechanism. The loudest thing on the card after the difference itself."""
    return f'<div class="why"><b>{icon("why")}why</b><p>{inline(repo, text)}</p></div>' if text else ""


def knobs_html(repo: dict, rows: list) -> str:
    """What is adjustable, and what each one does today. Never what to change:
    a reader who is handed the fix has nothing left to work out."""
    if not rows:
        return ""
    body = "".join(
        f'<tr><td class="k">{esc(k.get("what", ""))}</td>'
        f'<td class="does">{inline(repo, k.get("does", ""))}</td>'
        f'<td class="where">{chip(repo, k["ref"]) if k.get("ref") else ""}</td></tr>'
        for k in rows
    )
    return ('<div class="knobs"><div class="k-label">what is adjustable here, and what each one does today</div>'
            f"<table>{body}</table></div>")


def carry_html(repo: dict, rule: str) -> str:
    """The rule, not the incident. This is the line a reader takes to the next
    project, so it must survive without any of this page's facts."""
    return f'<div class="carry">{icon("carry")}<p>{inline(repo, rule)}</p></div>' if rule else ""


def stop_html(repo: dict, stop: dict, issue: bool = False) -> str:
    sid = stop["id"]
    ref = stop.get("ref")
    chip_html = ""
    sym = ""
    if ref:
        chip_html = " " + chip(repo, ref)
        if isinstance(ref, dict) and ref.get("symbol") and not issue:
            sym = f' <code>{esc(ref["symbol"])}</code>'
    block = ""
    if stop.get("block"):
        fn = BLOCKS.get(stop["block"].get("type"), b_raw)
        block = fn(repo, sid, stop["block"])
    think = think_html(repo, sid, stop.get("think") or [])

    if not issue:
        head = (
            f'<p class="head"><span class="action" data-anchor="{sid}.head">'
            f'{inline(repo, stop.get("headline", ""))}</span>{chip_html}{sym}</p>'
        )
        return f'<li id="{sid}">{head}{block}{think}</li>'

    # One finding, one card: the evidence, the mechanism, the path and the
    # controls are rows of the same object, never a stack of separate panels.
    sev = stop.get("severity", "s2")
    state = stop.get("state", "open")
    head = (
        f'<span class="sev {esc(sev)}">{icon(sev, "i lg")}</span>'
        f'<p class="head"><span class="claim action" data-anchor="{sid}.head">'
        f'{inline(repo, stop.get("headline", ""))}</span>'
        f'<button class="state {esc(state)}" data-stop="{sid}">{icon(state)}{esc(state)}</button>'
        f'<span class="at">{chip_html}</span></p>'
    )
    case = "".join(p for p in (
        receipt_html(repo, stop.get("receipt") or {}),
        why_html(repo, stop.get("why", "")),
        block,
        knobs_html(repo, stop.get("knobs") or []),
    ) if p)
    case = f'<div class="case">{case}</div>' if case else ""
    return (f'<li class="stop" id="{sid}" data-state="{esc(state)}">'
            f'{head}{case}{think}{carry_html(repo, stop.get("carry", ""))}</li>')


def pipeline_html(repo: dict, pipe: dict) -> str:
    if not pipe:
        return ""
    steps = "".join(
        f'<li>{inline(repo, s.get("text", ""))}'
        + (f'<span class="where">{esc(s["where"])}</span>' if s.get("where") else "")
        + "</li>"
        for s in pipe.get("steps", [])
    )
    rec = json_block(pipe["record"]) if pipe.get("record") else ""
    foot = f'<p class="foot">{inline(repo, pipe["foot"])}</p>' if pipe.get("foot") else ""
    title = esc(pipe.get("title", "the pipeline, one real run"))
    return f'<div class="pipe"><p class="pt">{title}</p><ol>{steps}</ol>{rec}{foot}</div>'


def discussion_html(repo: dict, entries: list) -> str:
    def card(e: dict, reply: bool) -> str:
        cls = "qa reply" if reply else "qa"
        quote = (
            f'<p class="qa-sel">{esc(e["quote"])}</p>' if e.get("quote") and not reply else ""
        )
        answer = f'<div class="qa-a">{answer_html(repo, e.get("answer", ""))}</div>'
        kids = "".join(card(r, True) for r in e.get("replies") or [])
        parent = f' data-parent="{esc(e["parent"])}"' if reply and e.get("parent") else ""
        return (
            f'<div class="{cls}" id="qa-{esc(e["id"])}" data-answered="1" data-via="spot"'
            f'{parent} data-anchor-ref="{esc(e.get("anchor", ""))}">{quote}'
            f'<p class="qa-q">{esc(e.get("question", ""))}</p>{answer}{kids}</div>'
        )

    cards = "".join(card(e, False) for e in entries or [])
    return (
        '<section id="discuss"><h2>Discussion <span class="hint">'
        '<kbd>&#8984;K</kbd> jumps here, with a selection it quotes it</span></h2>'
        f'<div id="chatlog">{cards}</div>'
        '<div id="discuss-box"><input placeholder="ask, or tell me to change the page&hellip;"></div>'
        '</section>'
    )


def answer_html(repo: dict, text: str) -> str:
    out, bullets = [], None
    for raw in (text or "").split("\n"):
        line = raw.strip()
        if line.startswith("- "):
            bullets = bullets if bullets is not None else []
            bullets.append(f"<li>{inline(repo, line[2:])}</li>")
        else:
            if bullets:
                out.append(f'<ul>{"".join(bullets)}</ul>')
                bullets = None
            if line:
                out.append(f"<p>{inline(repo, line)}</p>")
    if bullets:
        out.append(f'<ul>{"".join(bullets)}</ul>')
    return "".join(out)


def viva_html(spec: dict) -> str:
    """The closing section: a reviewer asks, the reader answers, one at a time.

    Nothing is written at build time. The reader presses the button when they
    are done reading, and the questions come from what this page claimed and
    how far they took the conversation.
    """
    return (
        '<section id="viva"><h2>The questions <span class="hint">'
        'a senior reviewer, a dozen of them, then a score you can argue with</span></h2>'
        '<div class="blk bare empty" id="viva-blk"><div class="blk-head">'
        '<button id="viva-start" class="btn primary" type="button">take the questions</button>'
        '<span id="viva-count"></span></div>'
        '<div class="blk-body" id="viva-past"></div>'
        '<div class="viva-deck" id="viva-deck" hidden>'
        '<div class="viva-nav"><button id="viva-prev" class="btn" type="button">&larr;</button>'
        '<span class="dots" id="viva-dots"></span>'
        '<button id="viva-next" class="btn" type="button">&rarr;</button>'
        '<span class="viva-at" id="viva-at"></span></div>'
        '<p class="viva-q" id="viva-q"></p>'
        '<textarea id="viva-input" rows="3" placeholder="your answer, Enter for the next one"></textarea>'
        '<div class="viva-row"><button id="viva-score" class="btn primary" type="button">score me</button>'
        '<span class="hint" id="viva-left"></span></div></div></div></section>'
    )

def nav_html(spec: dict) -> str:
    """On a change the sidebar hunts by file:line. On an issue it hunts by
    finding: the code is the address of the defect, never its subject."""
    issue = spec.get("kind") == "issue"
    title = spec.get("navTitle") or (f'{count_stops(spec)} findings' if issue else "stops")
    out = ['<nav id="toc"><p class="toc-title">', esc(title), "</p><ol>"]
    for stage in spec.get("stages", []):
        out.append(f'<li><a class="sec" href="#{esc(stage["id"])}">{esc(stage.get("title", ""))}</a></li>')
        out.append('<ol class="sub">')
        for stop in stage.get("stops", []):
            ref = stop.get("ref")
            if issue:
                sev = stop.get("severity", "s2")
                short = stop.get("short") or stop.get("headline", "")
                where = f'<span class="where">{esc(ref_label(ref))}</span>' if ref else ""
                out.append(
                    f'<li><a class="item" href="#{esc(stop["id"])}">'
                    f'<span class="sev {esc(sev)}">{icon(sev)}</span>'
                    f'<span class="what">{esc(short)}{where}</span></a></li>'
                )
                continue
            label = ref_label(ref) if ref else stop["id"]
            out.append(f'<li><a href="#{esc(stop["id"])}">{esc(label)}</a></li>')
        out.append("</ol>")
    if issue:
        out.append('<li><a class="sec" href="#cost">what it costs</a></li>')
    out.append('<li><a class="sec" href="#viva">the questions</a></li>')
    out.append('<li><a class="sec" href="#discuss">discussion</a></li>')
    out.append("</ol></nav>")
    return "".join(out)


def count_stops(spec: dict) -> int:
    return sum(len(stage.get("stops") or []) for stage in spec.get("stages") or [])


def bar_html(spec: dict) -> str:
    """The one measure the whole page is about, split into its parts."""
    if spec.get("kind") != "issue":
        return ""
    return ""


def findings_bar(spec: dict) -> str:
    """A record, not an essay: how many findings there are and what state they are in."""
    states = [s.get("state", "open") for stage in spec.get("stages") or [] for s in stage.get("stops") or []]
    total = len(states)
    chips = "".join(
        f'<button class="filter{" on" if k == "all" else ""}" data-f="{k}">{icon(k if k != "all" else "cost")}'
        f'{k}<span class="c">{total if k == "all" else states.count(k)}</span></button>'
        for k in ("all", "open", "agreed", "closed", "holds")
    )
    return (
        f'<div class="docket-bar"><span class="n">{total}</span><span class="of">findings</span>{chips}</div>'
        '<div class="empty-state" id="empty"><span class="big" id="empty-title"></span>'
        '<span id="empty-why"></span></div>'
    )


def cost_html(spec: dict) -> str:
    """What each finding is costing. Arithmetic, never advice: the reader decides
    what to do about it, this only says what it is worth."""
    rows = spec.get("cost") or []
    if not rows:
        return ""
    body = "".join(
        f'<tr><td class="q"><a class="to-finding" href="#{esc(r["stop"])}">{esc(r["what"])}</a></td>'
        f'<td class="num">{esc(r.get("rows", ""))}</td><td>{esc(r.get("costs", ""))}</td>'
        f'<td class="does">{inline(spec["repo"], r.get("note", ""))}</td>'
        f'<td><span class="verdict-pill {"bad" if r.get("state") == "open" else "good"}">'
        f'{esc(r.get("state", "open"))}</span></td></tr>'
        for r in rows
    )
    head = "".join('<th data-k="%d"%s>%s%s</th>' % (i, ' class="num"' if k == "rows" else "", k, icon("sort"))
                   for i, k in enumerate(("finding", "rows", "costs", "note", "state")))
    return (
        f'<section id="cost"><h2>{icon("cost")}What it costs '
        '<span class="hint">every finding, by what it is costing the run</span></h2>'
        f'<div class="tbl-wrap"><div class="tbl-scroll"><table class="ev">'
        f'<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'
        f'<div class="tbl-foot"><span>sorted by what it costs. What to do about it is yours.</span></div>'
        "</div></section>"
    )


def body_html(spec: dict) -> str:
    repo = spec["repo"]
    issue = spec.get("kind") == "issue"
    parts = [pipeline_html(repo, spec.get("pipeline") or {})]
    if issue:
        parts.append(findings_bar(spec))
    for stage in spec.get("stages", []):
        tag = f' <span class="tag">{esc(stage["tag"])}</span>' if stage.get("tag") else ""
        glyph = icon(stage["icon"]) if stage.get("icon") else ""
        parts.append(f'<h2 id="{esc(stage["id"])}">{glyph}{esc(stage.get("title", ""))}{tag}</h2>')
        stops = "".join(stop_html(repo, s, issue) for s in stage.get("stops", []))
        parts.append(f'<ol class="steps{" stops" if issue else ""}">{stops}</ol>')
    if issue:
        parts.append(cost_html(spec))
    parts.append(viva_html(spec))
    parts.append(discussion_html(repo, spec.get("discussion") or []))
    return "\n".join(parts)


def render(spec: dict) -> str:
    tpl = (HERE / "template.html").read_text(encoding="utf-8")
    skills = json.dumps(spec.get("skills", []), ensure_ascii=False)
    sub = spec.get("subtitle", "")
    if spec.get("repo", {}).get("sha"):
        sub = f'{sub} <span class="build">build {spec.get("build", 1)} &middot; {spec["repo"]["sha"]}</span>'
    repo = spec.get("repo") or {}
    # the page carries its own root and scheme, so a chip written in an answer
    # resolves whether or not that file already appears somewhere on the page
    where = json.dumps(
        {"root": str(expand_root(repo["root"])) if repo.get("root") else "", "editor": repo.get("editor", "cursor")},
        ensure_ascii=False,
    )
    html = (
        tpl.replace("{{FONTS}}", f"<style>{fonts.css()}</style>" if fonts.css() else "")
        .replace("{{ICONS}}", sprite())
        .replace("{{REPO}}", where)
        .replace("{{LOOK}}", look_html(spec))
        .replace("{{TITLE}}", esc(spec.get("title", "rundown")))
        .replace("{{SUBTITLE}}", sub)
        .replace("{{NAV}}", nav_html(spec))
        .replace("{{BODY}}", body_html(spec))
        .replace("{{SKILLS}}", skills)
    )
    if EM_DASH in html:
        raise SystemExit("em-dash reached the page, fix the spec")
    return html


def look_html(spec: dict) -> str:
    """The spec's own look rules, last in the cascade so they win.

    A page change is a spec change, so a request to restyle one page lands here
    rather than in the template, which every other rundown is stamped from.
    """
    rules = spec.get("look") or []
    if not rules:
        return ""
    body = "\n".join(f'{r["sel"]} {{ {r["css"]} }}' for r in rules)
    return f'<style id="look">\n{body}\n</style>'


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    spec = load(Path(sys.argv[1]))
    out = Path(sys.argv[2]).expanduser()
    out.write_text(render(spec), encoding="utf-8")
    print(f"rendered {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
