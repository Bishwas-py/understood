# understood

A small family of low-cognitive-load rewrite patterns, packaged as one Claude Code plugin. Every pattern here rewrites text the user already has (pasted, referenced, or otherwise in context) into something faster to read. None of them research or explain proactively on their own; they only act when explicitly invoked.

Install as a plugin (see below), not by symlinking individual skills.

## Patterns

- **caveman-english** — rewords text into blunt, clipped phrasing (drop articles/pronouns/helper verbs, bare verbs, short plain words, no equation-style symbol stacking). A voice, not a compressor: same structure, same ideas, just leaner wording. See `plugins/understood/skills/caveman-english/SKILL.md`. Invoke with `/caveman-english`.
- **forward-arrow** — process/flow explanations become `step → step → step` chains, scoped to what was actually asked (one flow by default, more only if explicitly requested). Uses the caveman-english voice for each step's wording, on top of its own flow-finding and chaining. See `plugins/understood/skills/forward-arrow/SKILL.md`. Invoke with `/forward-arrow`.
- **walkthrough** — compiles one json spec into a self-contained HTML page for presenting a change live: stages ordered by the data's journey, every stop a claim with its `file:line` chip, and operable live blocks (switch, chain, dial, race, probe, flow chart, and more) whose controls are the code references themselves. A validator refuses a wrong line number, a navigation-verb headline, or an em-dash before the page is ever served. The reader can select any text and ask; the question reaches the session that built the page and the answer lands beside the words, threaded to them. Each walkthrough lives in its own folder under `.walkthrough/` in the repo it is about, so the spec, the page, and the whole conversation stay together across rebuilds. See `plugins/understood/skills/walkthrough/SKILL.md`. Invoke with `/walkthrough`.

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
        walkthrough/assets/spec.py            shared conventions: chips, refs, escaping
        walkthrough/assets/validate.py        refuses a lie before it ships
        walkthrough/assets/render.py          spec -> one self-contained page
        walkthrough/assets/mermaid.py         flowcharts drawn to svg at build time
        walkthrough/assets/template.html      the page shell and its runtime
        walkthrough/assets/blocks.html        reference implementations of every block
        walkthrough/assets/example.json       a complete working spec
        walkthrough/assets/store.py           one folder per walkthrough, history, build
        walkthrough/assets/serve.py           stable local origin, live reload, /ask
        walkthrough/assets/wait_question.py   the wake loop
        walkthrough/assets/editor.py          cursor or vscode probe
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
