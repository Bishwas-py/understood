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


def b_raw(repo, sid, c):
    return f'<div class="blk" data-block="raw" data-stop="{sid}">{c.get("html", "")}</div>'


BLOCKS = {
    "switch": b_switch, "race": b_race, "chain": b_chain, "dial": b_dial,
    "probe": b_probe, "bind": b_bind, "ledger": b_ledger, "stepper": b_stepper,
    "map": b_map, "flow": b_flow, "space": b_space, "angle": b_angle, "stack": b_stack, "raw": b_raw,
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


def stop_html(repo: dict, stop: dict) -> str:
    sid = stop["id"]
    ref = stop.get("ref")
    chip_html = ""
    sym = ""
    if ref:
        chip_html = " " + chip(repo, ref)
        if isinstance(ref, dict) and ref.get("symbol"):
            sym = f' <code>{esc(ref["symbol"])}</code>'
    head = (
        f'<p class="head"><span class="action" data-anchor="{sid}.head">'
        f'{inline(repo, stop.get("headline", ""))}</span>{chip_html}{sym}</p>'
    )
    block = ""
    if stop.get("block"):
        fn = BLOCKS.get(stop["block"].get("type"), b_raw)
        block = fn(repo, sid, stop["block"])
    return f'<li id="{sid}">{head}{block}{think_html(repo, sid, stop.get("think") or [])}</li>'


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
    out = ['<nav id="toc"><p class="toc-title">', esc(spec.get("navTitle", "stops")), "</p><ol>"]
    for stage in spec.get("stages", []):
        out.append(f'<li><a class="sec" href="#{esc(stage["id"])}">{esc(stage.get("title", ""))}</a></li>')
        out.append('<ol class="sub">')
        for stop in stage.get("stops", []):
            ref = stop.get("ref")
            label = ref_label(ref) if ref else stop["id"]
            out.append(f'<li><a href="#{esc(stop["id"])}">{esc(label)}</a></li>')
        out.append("</ol>")
    out.append('<li><a class="sec" href="#viva">the questions</a></li>')
    out.append('<li><a class="sec" href="#discuss">discussion</a></li>')
    out.append("</ol></nav>")
    return "".join(out)


def body_html(spec: dict) -> str:
    repo = spec["repo"]
    parts = [pipeline_html(repo, spec.get("pipeline") or {})]
    for stage in spec.get("stages", []):
        tag = f' <span class="tag">{esc(stage["tag"])}</span>' if stage.get("tag") else ""
        parts.append(f'<h2 id="{esc(stage["id"])}">{esc(stage.get("title", ""))}{tag}</h2>')
        stops = "".join(stop_html(repo, s) for s in stage.get("stops", []))
        parts.append(f'<ol class="steps">{stops}</ol>')
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
        tpl.replace("{{REPO}}", where)
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
