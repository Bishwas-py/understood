---
name: walkthrough
description: Build a self-contained HTML walkthrough for presenting a change to a senior reviewer live, step by step through the real code. Use when the user invokes /walkthrough, or says they have to "walk someone through" a PR/feature/codebase, "present this on a call", "demo the code", or wants "a script for the review". Produces one HTML file of clickable file:line stops with scannable KEYWORD and KNOW MORE cues, never prose to read aloud. Part of the "understood" family of low-cognitive-load patterns.
---

# walkthrough

Turns a change you have to defend into a document you can drive a live screen-share from.

The reader is the presenter, mid-call, talking. They glance at the page and look back at the editor. So the page carries **cues, not sentences**. Anything they would have to read aloud has already failed.

## What it produces

Exactly one file: a self-contained HTML page built from `assets/template.html`.

- floating sidebar, every stop listed by `file:line`, current position highlighted on scroll
- numbered stops down the middle, each one a place to put the cursor
- every path and every bare line number is a link that opens the editor at that exact line
- two cue types per stop, `KEYWORD` and `KNOW MORE`, both bullet fragments
- light and dark, prints, no external requests, no build step
- served on a memorable local hostname so the user gets a URL, not a file path

Default output: `~/Downloads/<slug>-walkthrough.html`, then served on a local port and handed back as `http://<slug>.lvh.me:<port>/`. Honour an explicit path if the user gives one.

## Before writing a single line

**Read the real code.** Every line number in this document is a promise. A stop that opens the wrong line in front of the reviewer costs more credibility than the whole document earns. Open each file, confirm the symbol is on the line you cite, and confirm the file exists on disk before writing its link.

**Get the change.** The diff, the PR, the branch. What is actually new versus what was already there.

**Find the entry point.** Not the most interesting file. The place the request or the data actually enters the system.

## Ordering: chronology, then cursor

Two rules, in this order.

**1. Order stops by the life of the request, not by file, layer, or importance.** If work happens in phases separated by time (a synchronous request, then a queued background job, then a later user action), those are separate acts with their own headings. Making the phase boundary visible is often the single most valuable thing in the document, because it is where "does this block the user" gets answered.

**2. Inside an act, every stop must be reachable from the previous one by go-to-definition.** Open a file, click a symbol, land on the next stop. Never "now open this other file", the presenter loses their place and the audience loses the thread. If two stops are not connected by a call, either they belong to different acts or a stop is missing between them.

Say the hop out loud in the step text: *Cmd-click `Foo`*, *Line 126, cmd-click `bar`*, *Back up to `Baz`, line 141*.

## Anatomy of a stop

```html
<li>
	<p><span class="action">Line 135</span>, cmd-click <code>chunkDocument</code> &rarr; <a class="path" href="...">worker.go:200</a></p>
	<pre><code>...six lines at most...</code></pre>
	<div class="key"><ul><li>...</li><li>...</li></ul></div>
	<div class="more"><b>Question?</b><ul><li>...</li></ul></div>
</li>
```

Snippets are for pointing at, not reading. Six lines maximum, elided with `...` where the middle does not matter. If the snippet needs more than six lines to make its point, the stop is really two stops.

## KEYWORD cues

The default block. What this code is **for**, in fragments.

- **Purpose first, mechanism second, and only if the mechanism is the point.** "Turns one document into its pages, each stored on its own, so search can point at a page instead of a whole file" beats "downloads, splits, uploads".
- **Bullet fragments, never sentences.** One idea per bullet. The presenter builds the sentence, the page does not.
- **A bullet that survives deletion should be deleted.** "Both or neither" says nothing without naming the two things.
- **Point at what is on screen.** If a variable in the snippet is the proof of the claim, name it: "`qtx` means this runs inside the submit's own database write".

## KNOW MORE cues

An anticipated question, bolded, with a fragment answer. These are the ones that save the call.

- **Never include a question the reviewer already decided.** If the pattern was their call, their convention, or their explicit instruction, asking "why did we do it this way" reads as not knowing it was theirs. Convert it into a KEYWORD fragment that credits it instead: "lives here per your ruling, the shared service stays stateless".
- **Only genuinely open questions.** Things decided during the work that the reviewer has not seen.
- **Not on every stop.** Restraint is what makes the real ones land. A stop with an obvious answer gets nothing.
- **Favour failure modes.** What happens on partial failure, on retry, on re-run, on malformed input, on a shrinking dataset, on a concurrent worker. That is where a senior reviewer's attention actually goes.
- **Volunteer the weak spot before they find it.** Anything removed, anything unproven, anything measured on a small sample. Put it in the document. Being told beats being caught.

## Language rules

**Match the reviewer's level.** A senior reviewer, often the person who designed the system. Explaining fundamentals to them is condescending and it costs trust. Use the real term.

| Do not write | Write |
|---|---|
| turns the text into 3072 numbers | embeds the question into a 3072-dim vector |
| compares the numbers | cosine distance between the query vector and each stored vector |
| a special kind of index | the ANN index, and the dimension cap it enforces |

**Ban the phrases that sound like meaning.** These survive drafts because they read smoothly and say nothing:

`worth reading` · `the same form` · `the same space` · `handles it` · `takes care of` · `properly` · `as expected` · `under the hood` · `both or neither`

Each of them hides the fact. Replace with the fact.

**Concrete nouns only.** "One item per file" is two vague words. "One queue row per uploaded document, a salary certificate, a bank statement" is checkable. If a word means two different things in the same document (a queue row and a database row), disambiguate every occurrence.

**Numbers earn their place or leave.** A measured latency figure is worth saying. A pile of threshold values the presenter would have to recite is noise. Point at the comment in the code that holds them instead.

## Editor links

Every path and every bare line reference becomes an anchor:

```html
<a class="path" href="cursor://file/ABSOLUTE/PATH/file.go:135">Line 135</a>
```

- Absolute paths only. Percent-encode, keeping `/:.[]()+_-` safe, so route files with brackets and plus signs survive.
- `cursor://file/...` for Cursor, `vscode://file/...` for VS Code. Pick from what the user runs, and mention the one-replace switch.
- Shorthand in the text resolves to the full path of the file **the surrounding stop is in**. The same line number means different files in different acts.
- **Verify every target exists on disk before writing it.** A dead link during a live call is worse than no link.
- The first click prompts the browser to allow the scheme. Tell the user, so they allow it before the call, not during.

## Sidebar

Built from the document, not hand-maintained.

- One entry per `<h2>`, nested entries per stop
- Stop labels are `file:line`, monospace, because that is what the presenter is hunting for
- Never label a stop "Back to line 141", strip the prose: `worker.go:141`
- Scroll spy highlights the current stop, script is already in the template

## Build order

1. Copy `assets/template.html`, replace `{{TITLE}}`, `{{SUBTITLE}}`, `{{NAV}}`, `{{BODY}}`.
2. Write the body: a summary table of what changed, then the acts, then any closing sections.
3. Give every `<h2>` an `id`, every stop `<li>` an `id`, then build the nav from those.
4. Link the paths, then link the bare line numbers, using the editor scheme detected for this machine.
5. Verify.
6. Serve it, and hand back the URL.

Prefer direct edits over generating the file with a script. A scripted sweep is right for a mechanical pass over dozens of identical blocks; for anything else it is slower, riskier, and one bad substitution silently corrupts every anchor in the file.

## Verify before handing over

Run all of these. Report the counts, do not claim it works.

- every `href="...file..."` target exists on disk
- link count equals id count
- no unclosed tags
- no cue block without a list, a single-item block still gets a bullet, otherwise the question runs into the answer
- no banned phrase survives
- click two or three sidebar links yourself
- fetch the served URL and confirm it returns 200 with the expected byte count

## Serve it

Hand back a URL, not a file path. A `file://` path cannot be pasted into a call, does not survive a screen share, and the editor links behave better from an http origin.

```bash
python3 assets/serve.py <output.html> --open
```

It prints one line, the URL, and holds the port until interrupted:

```
http://my-change-walkthrough.lvh.me:61967/
```

Any subdomain of `lvh.me` resolves to `127.0.0.1` through public DNS, so the page gets a hostname that says what it is, with no `/etc/hosts` edit and no privileged port. The slug comes from the filename.

**Why the bundled server and not `python3 -m http.server`.** That serves the whole directory, and these files usually land in Downloads. `serve.py` binds loopback only and answers every path with the one file it was given, so a stray request cannot list or fetch anything else.

Run it in the background, read the URL from its output, hand that to the user. Say the port dies when the process does.

## Read the system before you write the file

Three things depend on where this is running. Detect them, do not assume.

**Editor scheme.** Look for what the user actually runs before choosing `cursor://file/...` or `vscode://file/...`. On macOS, `ls /Applications | grep -iE 'cursor|visual studio code'`; on Linux, `command -v cursor code`; on Windows, check the Programs folders. If both are present, ask, or pick the one whose process is running. Getting this wrong makes every link on the page inert.

**Path shape.** Absolute paths, in the platform's own form. On Windows that means `vscode://file/C:/Users/...`, forward slashes, drive letter kept.

**Opener.** `open` on macOS, `xdg-open` on Linux, `start` on Windows. `serve.py --open` already picks by platform, so prefer passing the flag over shelling out yourself.

If `lvh.me` does not resolve, the machine is offline or behind a DNS filter. `serve.py` falls back to `localhost` on its own and says so on stderr. Pass that on rather than silently handing over a URL that will not load.

## Optional closing sections

Only if they carry weight:

- **Spare tabs** — what to have open in case a question goes sideways, usually the tests and the diff
- **If they push** — the two or three points most likely to be challenged, each with its one-line answer

## What this is not

Not documentation. Not a design doc. Not something anyone reads without a call happening. It has one job: keep a person oriented while they talk and click at the same time. Anything that does not serve that comes out.
