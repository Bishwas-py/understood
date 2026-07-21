# understood

A small family of low-cognitive-load rewrite patterns, packaged as one Claude Code plugin. Every pattern here rewrites text the user already has (pasted, referenced, or otherwise in context) into something faster to read. None of them research or explain proactively on their own; they only act when explicitly invoked.

Install as a plugin (see below), not by symlinking individual skills.

## Patterns

- **caveman-english** — rewords text into blunt, clipped phrasing (drop articles/pronouns/helper verbs, bare verbs, short plain words, no equation-style symbol stacking). A voice, not a compressor: same structure, same ideas, just leaner wording. See `plugins/understood/skills/caveman-english/SKILL.md`. Invoke with `/caveman-english`.
- **forward-arrow** — process/flow explanations become `step → step → step` chains, scoped to what was actually asked (one flow by default, more only if explicitly requested). Uses the caveman-english voice for each step's wording, on top of its own flow-finding and chaining. See `plugins/understood/skills/forward-arrow/SKILL.md`. Invoke with `/forward-arrow`.
- **walkthrough** — builds one self-contained HTML page for presenting a change live to a senior reviewer: numbered stops through the real code in request order, every `file:line` clickable straight into the editor, and two kinds of scannable cue (`KEYWORD` for what a stop is for, `KNOW MORE` for the question it invites). The presenter glances and talks; the page never contains a sentence to read aloud. It detects the editor it is running next to (Cursor first, VS Code as fallback) and the platform it is on, and serves the finished page at `http://walkthrough.localhost:<port>/<slug>/`, a stable secure-context origin, so you hand over a URL rather than a file path and the browser's "open Cursor?" dialog can be allowed once and never asked again. See `plugins/understood/skills/walkthrough/SKILL.md`. Invoke with `/walkthrough`.

The first two rewrite text the user already has. `walkthrough` is the one pattern that reads a codebase, because a walkthrough is only worth anything if every line number in it is real.

Future patterns get their own subdirectory under `plugins/understood/skills/`, following the same shape: one clear job, scoped by request, no output beyond what was asked for, and reuse the caveman-english voice rather than redefining wording rules.

## Layout

```
understood/
  .claude-plugin/
    marketplace.json          local marketplace manifest
  plugins/
    understood/
      .claude-plugin/
        plugin.json            plugin manifest
      skills/
        caveman-english/SKILL.md
        forward-arrow/SKILL.md
        walkthrough/SKILL.md
        walkthrough/assets/template.html
        walkthrough/assets/serve.py
        walkthrough/assets/editor.py
```

## Install

```bash
claude plugin marketplace add Bishwas-py/understood
claude plugin install understood@understood
```

Restart Claude Code afterward — skills don't hot-reload mid-session.

### Local development install

If you're working on a local clone instead of the published repo:

```bash
cd /path/to/understood
claude plugin marketplace add "$(pwd)"
claude plugin install understood@understood
```

## Uninstall

```bash
claude plugin uninstall understood@understood
claude plugin marketplace remove understood
```
