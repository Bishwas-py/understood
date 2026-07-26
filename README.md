# understood

A small family of low-cognitive-load rewrite patterns, packaged as one Claude Code plugin. Every pattern here rewrites text the user already has (pasted, referenced, or otherwise in context) into something faster to read. None of them research or explain proactively on their own; they only act when explicitly invoked.

Install as a plugin (see below), not by symlinking individual skills.

## Patterns

- **caveman-english** — rewords text into blunt, clipped phrasing (drop articles/pronouns/helper verbs, bare verbs, short plain words, no equation-style symbol stacking). A voice, not a compressor: same structure, same ideas, just leaner wording. See `plugins/understood/skills/caveman-english/SKILL.md`. Invoke with `/caveman-english`.
- **forward-arrow** — process/flow explanations become `step → step → step` chains, scoped to what was actually asked (one flow by default, more only if explicitly requested). Uses the caveman-english voice for each step's wording, on top of its own flow-finding and chaining. See `plugins/understood/skills/forward-arrow/SKILL.md`. Invoke with `/forward-arrow`.
- **rundown** — compiles one json spec into a self-contained HTML page for presenting a change live: stages ordered by the data's journey, every stop a claim with its `file:line` chip, and operable live blocks (switch, chain, dial, race, probe, flow chart, and more) whose controls are the code references themselves. A validator refuses a wrong line number, a navigation-verb headline, or an em-dash before the page is ever served. The reader can select any text and ask; the question reaches the session that built the page and the answer lands beside the words, threaded to them. Each rundown lives in its own folder under `.rundown/` in the repo it is about, so the spec, the page, and the whole conversation stay together across rebuilds. See `plugins/understood/skills/rundown/SKILL.md`. Invoke with `/rundown`.

The first two rewrite text the user already has. `rundown` is the one pattern that reads a codebase, because a rundown is only worth anything if every line number in it is real.

Future patterns get their own subdirectory under `plugins/understood/skills/`, following the same shape: one clear job, scoped by request, no output beyond what was asked for, and reuse the caveman-english voice rather than redefining wording rules.

## Layout

```
understood/
  .claude-plugin/
    marketplace.json          local marketplace manifest
  install.sh                  the command and the plugin, in one step
  uninstall.sh                undo it, rundowns untouched
  plugins/
    understood/
      .claude-plugin/
        plugin.json            plugin manifest
      skills/
        caveman-english/SKILL.md
        forward-arrow/SKILL.md
        rundown/SKILL.md
        rundown/assets/spec.py            shared conventions: chips, refs, escaping
        rundown/assets/validate.py        refuses a lie before it ships
        rundown/assets/render.py          spec -> one self-contained page
        rundown/assets/mermaid.py         flowcharts drawn to svg at build time
        rundown/assets/template.html      the page shell and its runtime
        rundown/assets/example.json       a complete working spec
        rundown/assets/cli.py             the rundown command, and every block's shape
        rundown/assets/store.py           one folder per rundown, history, snapshots
        rundown/assets/serve.py           one origin for every rundown, index, /ask
        rundown/assets/wait_question.py   the wake loop
        rundown/assets/editor.py          cursor or vscode probe
```

## Install

One command. It puts `rundown` on your PATH and installs the Claude Code plugin, and re-running it upgrades both:

```bash
curl -fsSL https://raw.githubusercontent.com/Bishwas-py/understood/main/install.sh | bash
```

There is one clone on disk and both halves read it, so the command and the plugin can never drift out of version with each other. No package manager: the code is pure python with no dependencies, so a clone and a small shim is the whole install. `RUNDOWN_HOME` and `RUNDOWN_BIN` override where those land.

Restart Claude Code afterward, skills don't hot-reload.

### The command

```bash
rundown list                  every rundown in this repo
rundown serve                 all of them on one origin, index at /
rundown serve <slug> --open   the same server, opened at that one
rundown build <slug> --fix    validate, resync drifted refs, render
rundown verify <slug>         validate only, write nothing
rundown rm <slug> --force     delete one and its conversation
rundown upgrade               pull the latest source, update the plugin
rundown doctor                versions, store location, what is missing
```

Reading an old rundown never needs a session: `cd` into the repo and `rundown serve`.

### Plugin only

If you only want the skill inside Claude Code and no command on your PATH:

```bash
claude plugin marketplace add Bishwas-py/understood
claude plugin install understood@understood
```

## Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/Bishwas-py/understood/main/uninstall.sh | bash
```

Pass `--all` to delete the clone too. Your rundowns are never touched: they live in `.rundown/` inside each repo they are about.
