# understood

Three small patterns for making things faster to read, packaged as one Claude Code plugin.

They run when you ask and never on their own.

## The patterns

### `/caveman-english`

Rewords text into blunt, clipped phrasing. Drop the articles, the pronouns, the helper verbs. Short plain words.

Same structure, same ideas, leaner wording. It's a voice, not a compressor.

### `/forward-arrow`

Turns a process explanation into `step → step → step`. One flow by default. More only if you ask for more.

Each step gets the caveman voice on top.

### `/rundown`

The big one. It builds a single HTML page you can drive a live code review from, and it reads your actual code to do it.

You write nothing. You describe the change, it writes a json spec and compiles that into the page.

What you get:

- stages ordered by where the data goes, not by which file is interesting
- every stop is a claim, with a `file:line` chip that opens your editor at that line
- live blocks you operate instead of paragraphs you read: flip a switch to take a fix out of the build, run a race with and without the lock, drag a dial past the value that shipped
- select any text on the page and ask about it. The question reaches the Claude session that built the page, and the answer lands in the margin, threaded to the words you highlighted
- a round of questions at the end. A senior reviewer asks one at a time, deep ones and code ones, you type your answer, it marks you and asks the next. Last turn is a verdict on what you'd actually survive being asked. Take another round whenever you want; the old ones stay on the page

## Why the rundown doesn't lie to you

Every line number on that page is a promise, and you find out one was wrong by clicking it in front of a reviewer. So most of the work is in refusing to ship one.

**A pattern outranks a line number.** Each reference carries the regex that finds its definition. Code moves, `rundown build --fix` puts the reference back where the pattern says it is now and writes that into the spec. You never chase drift by hand.

**Nothing gets checked halfway.** The chip beside a headline, the reference a block prints in its own header, every hop of a chain, every node of a flow chart: one walk covers all of them. There is no second list to forget about.

**Blocks declare their own shape.** `rundown blocks race` tells you what a race takes and hands you a config to paste. The validator checks against that same declaration, so a typo is a build error instead of a control that renders and then does nothing when you press it.

**Renaming something doesn't lose the question about it.** When an edit rewrites text a reader asked about, the answer says what those words became. The highlight moves there, the thread reconnects, and the card shows the old quote crossed out with the new one under it. Every build also tells you which quotes it just orphaned.

**Rebuilding is cheap.** Each rundown owns a folder, so a rebuild replaces the page and leaves the whole conversation in place. Every write snapshots the spec first and keeps the last twenty, which is your undo.

One process serves all of them. `/` lists what's in the repo, `/<slug>/` is a page. Ports stop wandering, so your browser asks about opening Cursor exactly once.

## Install

One command. Puts `rundown` on your PATH and installs the Claude Code plugin. Run it again later to upgrade both.

```bash
curl -fsSL https://raw.githubusercontent.com/Bishwas-py/understood/main/install.sh | bash
```

One clone on disk, read by both halves, so the command and the plugin can't drift apart. No package manager involved: it's pure python with no dependencies, so a clone and a small shim is the whole install. Set `RUNDOWN_HOME` or `RUNDOWN_BIN` if you want them somewhere else.

Restart Claude Code afterward. Skills don't hot-reload.

### The command

```bash
rundown list                  every rundown in this repo
rundown serve                 all of them on one origin, index at /
rundown serve <slug> --open   the same server, opened at that one
rundown build <slug> --fix    validate, repair drifted refs, render
rundown save <slug> spec.json snapshot the old spec, write the new one, build
rundown verify <slug>         validate only, write nothing
rundown blocks                every block, and what each one needs
rundown blocks <name>         one block's shape, and a config to paste
rundown blocks --demo         a page carrying all fourteen, operable
rundown rm <slug> --force     delete one and its conversation
rundown upgrade               pull the latest source, update the plugin
rundown uninstall             remove the command and the plugin
rundown doctor                versions, store location, what's missing
```

Opening an old rundown never needs a Claude session. `cd` into the repo and `rundown serve`.

### Plugin only

If you want the skill inside Claude Code and nothing on your PATH:

```bash
claude plugin marketplace add Bishwas-py/understood
claude plugin install understood@understood
```

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
        rundown/assets/spec.py            chips, refs, escaping, every block's shape
        rundown/assets/validate.py        refuses a lie before it ships
        rundown/assets/render.py          spec -> one self-contained page
        rundown/assets/mermaid.py         flowcharts drawn to svg at build time
        rundown/assets/template.html      the page shell and its runtime
        rundown/assets/cli.py             the rundown command
        rundown/assets/store.py           one folder per rundown, history, snapshots
        rundown/assets/serve.py           one origin for every rundown, index, /ask
        rundown/assets/wait_question.py   the wake loop, and relinking a renamed mark
        rundown/assets/example.json       a complete working spec
        rundown/assets/editor.py          cursor or vscode probe
```

Anything new goes in its own directory under `plugins/understood/skills/`. One clear job, only runs when asked, and it borrows the caveman voice rather than inventing its own wording rules.

## Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/Bishwas-py/understood/main/uninstall.sh | bash
```

Add `--all` to delete the clone too. Your rundowns are never touched. They live in `.rundown/` inside whichever repo they're about.
