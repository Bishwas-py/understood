# understood

A small family of low-cognitive-load rewrite patterns, packaged as one Claude Code plugin. Every pattern here rewrites text the user already has (pasted, referenced, or otherwise in context) into something faster to read. None of them research or explain proactively on their own; they only act when explicitly invoked.

Install as a plugin (see below), not by symlinking individual skills.

## Patterns

- **caveman-english** — rewords text into blunt, clipped phrasing (drop articles/pronouns/helper verbs, bare verbs, short plain words, no equation-style symbol stacking). A voice, not a compressor: same structure, same ideas, just leaner wording. See `plugins/understood/skills/caveman-english/SKILL.md`. Invoke with `/caveman-english`.
- **forward-arrow** — process/flow explanations become `step → step → step` chains, scoped to what was actually asked (one flow by default, more only if explicitly requested). Uses the caveman-english voice for each step's wording, on top of its own flow-finding and chaining. See `plugins/understood/skills/forward-arrow/SKILL.md`. Invoke with `/forward-arrow`.

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
```

## Install

```bash
cd ~/Projects/understood
claude plugin marketplace add "$(pwd)"
claude plugin install understood@understood
```

Restart Claude Code afterward — skills don't hot-reload mid-session.

## Uninstall

```bash
claude plugin uninstall understood@understood
claude plugin marketplace remove understood
```
