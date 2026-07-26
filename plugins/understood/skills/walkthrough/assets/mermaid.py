#!/usr/bin/env python3
"""Render a mermaid flowchart subset to inline SVG, at build time.

Mermaid proper is megabytes and wants a browser; a walkthrough is one small
file that must still work offline in a year. So this understands the part of
the language a code walkthrough actually uses and draws it directly:

    flowchart TD
        A[selection] --> B[POST /ask]
        B --> C[(questions.jsonl)]
        C -->|waiter exits| D{answer written}
        D --> A

Shapes: [box] (round) [(store)] {decision} ([stadium]). Edges: -->, ---,
-.->, ==>, each with an optional |label|. Direction TD, TB, or LR.
"""

from __future__ import annotations

import re
from html import escape

OPEN = r"(\[\(|\(\[|\(\(|\[|\(|\{)"
CLOSE = r"(\)\]|\]\)|\)\)|\]|\)|\})"
NODE_RE = re.compile(r"^([A-Za-z0-9_]+)" + OPEN + r"?(.*?)" + CLOSE + r"?$")
EDGE_RE = re.compile(
    r"^([A-Za-z0-9_]+)(?:" + OPEN + r"(.*?)" + CLOSE + r")?\s*"
    r"(-{2,3}>|-{3}|-\.->|={2,}>)\s*(?:\|([^|]*)\|\s*)?"
    r"([A-Za-z0-9_]+)(?:" + OPEN + r"(.*?)" + CLOSE + r")?\s*$"
)
SHAPES = {"[": "box", "(": "round", "([": "stadium", "[(": "store", "{": "diamond", "((": "circle"}

CHAR_W = 7.8
PAD_X, PAD_Y = 20, 12
GAP_RANK, GAP_SIB = 66, 30


class Node:
    def __init__(self, key: str, label: str, shape: str):
        self.key, self.label, self.shape = key, label or key, shape
        self.rank = 0
        self.x = self.y = 0.0
        self.size()

    def size(self) -> None:
        """A diamond only reaches full width at its middle, so text inside it needs
        roughly twice the room a box does. Give every shape air where there is space."""
        text_w = len(self.label) * CHAR_W + PAD_X * 2
        if self.shape == "diamond":
            self.w, self.h = max(150.0, text_w * 1.32), 78.0
        elif self.shape == "store":
            self.w, self.h = max(96.0, text_w), 52.0
        else:
            self.w, self.h = max(96.0, text_w), 42.0


def parse(src: str):
    """Return (direction, nodes, edges). Unknown lines are skipped, not fatal."""
    direction = "TD"
    nodes: dict[str, Node] = {}
    edges: list[tuple[str, str, str]] = []

    def touch(key, open_, label, close):
        shape = SHAPES.get(open_ or "[", "box")
        if key not in nodes:
            nodes[key] = Node(key, (label or "").strip('"'), shape)
        elif label:
            nodes[key].label = label.strip('"')
            nodes[key].shape = shape
            nodes[key].size()
        return key

    for raw in src.splitlines():
        line = raw.strip()
        if not line or line.startswith("%%"):
            continue
        head = re.match(r"^(?:flowchart|graph)\s+(TD|TB|LR|RL|BT)\s*$", line, re.I)
        if head:
            direction = head.group(1).upper()
            continue
        m = EDGE_RE.match(line)
        if m:
            a = touch(m.group(1), m.group(2), m.group(3), m.group(4))
            b = touch(m.group(7), m.group(8), m.group(9), m.group(10))
            edges.append((a, b, (m.group(6) or "").strip()))
            continue
        m = NODE_RE.match(line)
        if m and m.group(2):
            touch(m.group(1), m.group(2), m.group(3), m.group(4))
    return direction, nodes, edges


def rank(nodes: dict, edges: list) -> None:
    """Longest-path layering: a node sits one rank below its deepest parent."""
    incoming = {k: [] for k in nodes}
    for a, b, _ in edges:
        if a != b:
            incoming[b].append(a)
    for _ in range(len(nodes)):
        moved = False
        for key, parents in incoming.items():
            want = max([nodes[p].rank + 1 for p in parents], default=0)
            if want > nodes[key].rank:
                nodes[key].rank = want
                moved = True
        if not moved:
            break


def layout(direction: str, nodes: dict, edges: list) -> tuple[float, float]:
    rank(nodes, edges)
    order: dict[int, list[Node]] = {}
    for n in nodes.values():
        order.setdefault(n.rank, []).append(n)
    vertical = direction in ("TD", "TB", "BT")
    cursor = 20.0
    width_needed = 0.0
    for r in sorted(order):
        row = order[r]
        if vertical:
            span = sum(n.w for n in row) + GAP_SIB * (len(row) - 1)
            x = 20.0
            for n in row:
                n.x, n.y = x, cursor
                x += n.w + GAP_SIB
            width_needed = max(width_needed, span + 40)
            cursor += max(n.h for n in row) + GAP_RANK
        else:
            span = sum(n.h for n in row) + GAP_SIB * (len(row) - 1)
            y = 20.0
            widest = max(n.w for n in row)
            for n in row:
                n.x, n.y = cursor, y
                y += n.h + GAP_SIB
            width_needed = max(width_needed, cursor + widest + 20)
            cursor += widest + GAP_RANK + 40
    if vertical:
        # centre each rank against the widest one
        for r in sorted(order):
            row = order[r]
            span = sum(n.w for n in row) + GAP_SIB * (len(row) - 1)
            shift = (width_needed - 40 - span) / 2
            for n in row:
                n.x += shift
        return width_needed, cursor - GAP_RANK + 20
    heights = [sum(n.h for n in row) + GAP_SIB * (len(row) - 1) for row in order.values()]
    return width_needed, max(heights) + 40


def rounded(points: list, r: float) -> str:
    """A closed polygon with its corners eased, so a diamond does not stab."""
    def toward(a, b, dist):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = (dx * dx + dy * dy) ** 0.5 or 1
        k = min(dist, length / 2) / length
        return (a[0] + dx * k, a[1] + dy * k)

    parts = []
    n = len(points)
    for i, v in enumerate(points):
        prev, nxt = points[(i - 1) % n], points[(i + 1) % n]
        p1, p2 = toward(v, prev, r), toward(v, nxt, r)
        parts.append(f"{'M' if i == 0 else 'L'} {p1[0]:.1f} {p1[1]:.1f} Q {v[0]:.1f} {v[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}")
    return " ".join(parts) + " Z"


def shape_svg(n: Node, href: str = "") -> str:
    x, y, w, h = n.x, n.y, n.w, n.h
    label = escape(n.label)
    text = f'<text x="{x + w / 2:.1f}" y="{y + h / 2 + 4:.1f}" text-anchor="middle">{label}</text>'
    if n.shape == "diamond":
        return f'<path class="nd" d="{rounded([(x + w / 2, y), (x + w, y + h / 2), (x + w / 2, y + h), (x, y + h / 2)], 12)}"/>{text}'
    if n.shape == "store":
        # a real cylinder: straight sides, arc across the bottom, full ellipse on top
        ry, cx = 7.0, x + w / 2
        sides = (
            f"M {x:.1f} {y + ry:.1f} V {y + h - ry:.1f} "
            f"A {w / 2:.1f} {ry:.1f} 0 0 0 {x + w:.1f} {y + h - ry:.1f} V {y + ry:.1f}"
        )
        text = f'<text x="{cx:.1f}" y="{y + h / 2 + 6:.1f}" text-anchor="middle">{label}</text>'
        return (
            f'<path class="nd store" d="{sides}"/>'
            f'<ellipse class="nd store" cx="{cx:.1f}" cy="{y + ry:.1f}" rx="{w / 2:.1f}" ry="{ry:.1f}"/>'
            f"{text}"
        )
    rx = h / 2 if n.shape in ("round", "stadium", "circle") else 8
    return f'<rect class="nd" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx:.1f}"/>{text}'


def wrap(svg: str, href: str, key: str = "") -> str:
    if not href:
        return f'<g class="nd-g" data-key="{escape(key, quote=True)}">{svg}</g>' if key else svg
    return f'<a class="nd-a" data-key="{escape(key, quote=True)}" href="{escape(href, quote=True)}">{svg}</a>' 


def edge_svg(a: Node, b: Node, label: str, vertical: bool, right_edge: float = 0.0) -> str:
    if vertical:
        x1, y1 = a.x + a.w / 2, a.y + a.h
        x2, y2 = b.x + b.w / 2, b.y
        if b.rank <= a.rank:  # a loop back up the page, routed around the side
            side = max(right_edge, a.x + a.w, b.x + b.w) + 26
            path = f"M {a.x + a.w:.1f} {a.y + a.h / 2:.1f} H {side:.1f} V {b.y + b.h / 2:.1f} H {b.x + b.w:.1f}"
            mid = (side + 6, (a.y + b.y) / 2)
        else:
            path = f"M {x1:.1f} {y1:.1f} C {x1:.1f} {y1 + 24:.1f} {x2:.1f} {y2 - 24:.1f} {x2:.1f} {y2:.1f}"
            mid = ((x1 + x2) / 2, (y1 + y2) / 2 + 4)
    else:
        x1, y1 = a.x + a.w, a.y + a.h / 2
        x2, y2 = b.x, b.y + b.h / 2
        path = f"M {x1:.1f} {y1:.1f} C {x1 + 24:.1f} {y1:.1f} {x2 - 24:.1f} {y2:.1f} {x2:.1f} {y2:.1f}"
        mid = ((x1 + x2) / 2, (y1 + y2) / 2 - 6)
    out = f'<path class="eg" d="{path}" marker-end="url(#mmar)"/>'
    if label:
        lw = len(label) * 6.0 + 14
        out += (
            f'<rect class="elbg" x="{mid[0] - lw / 2:.1f}" y="{mid[1] - 11:.1f}" '
            f'width="{lw:.1f}" height="16" rx="8"/>'
            f'<text class="el" x="{mid[0]:.1f}" y="{mid[1]:.1f}" text-anchor="middle">{escape(label)}</text>'
        )
    return out


def to_svg(src: str, hrefs: dict | None = None) -> str:
    hrefs = hrefs or {}
    direction, nodes, edges = parse(src)
    if not nodes:
        return ""
    w, h = layout(direction, nodes, edges)
    if any(nodes[b].rank <= nodes[a].rank for a, b, _ in edges):
        w += 44
    vertical = direction in ("TD", "TB", "BT")
    body = [
        '<defs><marker id="mmar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
        'orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z"/></marker></defs>'
    ]
    right_edge = max((n.x + n.w for n in nodes.values()), default=0.0)
    for a, b, label in edges:
        body.append(edge_svg(nodes[a], nodes[b], label, vertical, right_edge))
    for n in nodes.values():
        body.append(wrap(shape_svg(n), hrefs.get(n.key, ""), n.key))
    return (
        f'<svg class="mmd" viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" '
        f'preserveAspectRatio="xMidYMid meet">{"".join(body)}</svg>'
    )


if __name__ == "__main__":
    import sys

    print(to_svg(sys.stdin.read()))
