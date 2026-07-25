---
name: walkthrough
description: Build a self-contained HTML walkthrough for presenting a change to a senior reviewer live, step by step through the real code. Use when the user invokes /walkthrough, or says they have to "walk someone through" a PR/feature/codebase, "present this on a call", "demo the code", or wants "a script for the review". Produces one HTML file of clickable file:line stops with scannable KEYWORD and KNOW MORE cues, never prose to read aloud. Part of the "understood" family of low-cognitive-load patterns.
---

# walkthrough

Turns a change you have to defend into a document you can drive a live screen-share from.

The reader is the presenter, mid-call, talking. They glance at the page and look back at the editor. So the page carries **cues, not sentences**. Anything they would have to read aloud has already failed.

## What it produces

Exactly one file: a self-contained HTML page built from `assets/template.html`.

- a pipeline block first: the whole journey in arrow lines, one real record from an actual run riding along, every line stamped with where it lives (`#page`, `#server`, ...)
- stages down the middle ordered by the data's journey, every stop opening with an IN/OUT boundary box, each one a place to put the cursor
- a decisions section, BEFORE/AFTER pairs, only the 2 or 3 that matter
- floating sidebar, every stop listed by `file:line`, current position highlighted on scroll
- every path and every bare line number is a link that opens the editor at that exact line
- two cue types per stop, `KEYWORD` and `KNOW MORE`, both bullet fragments
- ask-from-selection: the reader's questions land as cards floating beside the highlighted text, answered live by the session that built the page
- light and dark, prints, no external requests, no build step
- served on a memorable local hostname so the user gets a URL, not a file path

Default output: `~/Downloads/<slug>-walkthrough.html`, then served on a stable local origin and handed back as `http://walkthrough.localhost:<port>/<slug>/`. Honour an explicit path if the user gives one.

## Before writing a single line

**Read the real code.** Every line number in this document is a promise. A stop that opens the wrong line in front of the reviewer costs more credibility than the whole document earns. Open each file, confirm the symbol is on the line you cite, and confirm the file exists on disk before writing its link.

**Get the change.** The diff, the PR, the branch. What is actually new versus what was already there.

**Find the entry point.** Not the most interesting file. The place the request or the data actually enters the system.

## Write for how the reader reads

The reader is a presenter defending code they did not write. The document must carry the understanding to them; a walkthrough that only works for its author is a diff with decoration. Eight rules, and they outrank stylistic preference:

1. **Flow over structure.** A -> B -> C with data moving through, never components-and-their-responsibilities. A stop that cannot say which stage of the journey it is in does not belong.
2. **Data before implementation.** The unit of understanding is the record moving through the system, not the function. "form JSON in, ~30 answers and a leftover list out" is presenter knowledge; "what settleFromForm does" is author knowledge.
3. **In and out before how.** Every stop opens with its boundary. Mechanism bullets come after, and only when the mechanism is the point.
4. **One real instance rides the whole page.** A name, a number, a filename from the actual run. If a real run happened, harvest its values; schema-speak forces live translation mid-call.
5. **One idea per line, flat lists, bold lead word.** Never group a list under sub-headers. Each line survives alone.
6. **Change is a pair of states.** BEFORE what went wrong, AFTER what happens now. A single-state description leaves the reader asking "compared to what?".
7. **Stamp everything for routing.** Every heading and stop carries where it lives: `#page`, `#server`, `#session`, a repo name, config-or-code. The reader triages before reading.
8. **Compression by default, depth behind a question.** The page stays terse; expansion lives in KNOW MORE blocks the reader opens with their eyes only when a line deserves it.

Pick the format by situation, never by habit:

| explaining | format |
|---|---|
| a process or flow | arrow chain, stage by stage |
| a change | BEFORE/AFTER pair |
| one piece of the system | IN and OUT rows, then cues |
| a set of facts | flat numbered list, bold lead word |
| a decision | BEFORE/AFTER plus the one-line reason |
| something that may need depth | one line now, KNOW MORE beneath it |

## Ordering: chronology, then cursor

Two rules, in this order.

**1. Order stops by the life of the request, not by file, layer, or importance.** If work happens in phases separated by time (a synchronous request, then a queued background job, then a later user action), those are separate acts with their own headings. Making the phase boundary visible is often the single most valuable thing in the document, because it is where "does this block the user" gets answered.

**2. Inside an act, every stop must be reachable from the previous one by go-to-definition.** Open a file, click a symbol, land on the next stop. Never "now open this other file", the presenter loses their place and the audience loses the thread. If two stops are not connected by a call, either they belong to different acts or a stop is missing between them.

Say the hop out loud in the step text: *Cmd-click `Foo`*, *Line 126, cmd-click `bar`*, *Back up to `Baz`, line 141*.

## Anatomy of a stop

```html
<li id="s3">
	<div class="io">
		<div><b>IN</b><span>the 170 byte record over loopback</span></div>
		<div><b>OUT</b><span>1 appended line in questions.jsonl</span></div>
	</div>
	<p><span class="action">Click</span> <a class="path" href="...">serve.py:129</a> <code>do_POST</code></p>
	<div class="say"><ul><li>...</li><li>...</li></ul></div>
	<div class="ask"><b>Question?</b><ul><li>...</li></ul></div>
</li>
```

The `io` box comes first, always: what enters, what leaves, with the real run's numbers. A `<pre>` snippet between the click line and the cues is optional, only when a cue names a variable that must be visible; six lines maximum, elided with `...`. If the snippet needs more to make its point, the stop is really two stops.

The page opens with the pipeline block, the whole journey before any stop:

```html
<div class="pipe">
	<p class="pt">The pipeline, one real question, today's run</p>
	<ol>
		<li>POST /ask, one json record <span class="where">#page</span></li>
		<li>questions.jsonl gains 1 line <span class="where">#server</span></li>
	</ol>
	<code class="rec">{"id":"aba0ecdd...","question":"hey"}</code>
	<p class="foot">this record is real. it rides every stage below.</p>
</div>
```

And decisions render as state pairs, in their own late section, only the 2 or 3 that matter:

```html
<div class="ba">
	<div class="b"><b>BEFORE</b> card html rewritten every poll, the mark died in 2s</div>
	<div class="a"><b>AFTER</b> rendered once, the mark lives as long as the tab</div>
</div>
```

All of these classes (`io`, `pipe`, `rec`, `where`, `tag`, `ba`) ship in the template's stylesheet; write the markup, never inline styles.

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

**No em-dashes, anywhere on the page.** Commas, periods, parentheses instead. This is absolute; sweep the generated HTML for the character before serving.

**Concrete nouns only.** "One item per file" is two vague words. "One queue row per uploaded document, a salary certificate, a bank statement" is checkable. If a word means two different things in the same document (a queue row and a database row), disambiguate every occurrence.

**Numbers earn their place or leave.** A measured latency figure is worth saying. A pile of threshold values the presenter would have to recite is noise. Point at the comment in the code that holds them instead.

## Editor links

Every path and every bare line reference becomes an anchor:

```html
<a class="path" href="cursor://file/ABSOLUTE/PATH/file.go:135">Line 135</a>
```

- Absolute paths only. Percent-encode, keeping `/:.[]()+_-` safe, so route files with brackets and plus signs survive.
- Scheme comes from `assets/editor.py`, Cursor preferred, VS Code fallback. Mention the one-replace switch between them.
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

1. Copy `assets/template.html`, replace `{{TITLE}}`, `{{SUBTITLE}}`, `{{NAV}}`, `{{BODY}}`, `{{SKILLS}}`.
   `{{SKILLS}}` is a JSON array powering the `/` dropdown in the page's ask box: `[{"name": "caveman-english", "hint": "blunt clipped rewording"}, ...]`, hint being the first clause of the skill's description, under 60 chars.
   Curate it from the session's live skill list, never a hardcoded set. Include a skill only if it acts on words: takes the selection (or the question) as text and produces a card answer, rewording, condensing, explaining, translating. Everything code-shaped stays out: skills that generate or edit code, review diffs, run tests or the app, build pages, or touch infrastructure, including `walkthrough` itself. The test is the presenter mid-call: if the skill could not finish as 2 to 4 bullets on the card while they keep talking, it does not belong in the menu. Left unreplaced it degrades to no dropdown, nothing breaks.
2. Write the body: the pipeline block, then the stages, then the decisions, then any closing sections.
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
http://walkthrough.localhost:8477/my-change-walkthrough/
```

Browsers resolve `*.localhost` to loopback on their own, no DNS and no `/etc/hosts` edit, and treat it as a secure context. That last part is the point: editor links (`cursor://`, `vscode://`) trigger the browser's "open this application?" dialog, and only a secure context gets the **Always allow** checkbox. The origin (host and port together) is what the browser remembers the approval for, which is why the host and default port never change and the slug lives in the path. Approve once, never prompted again.

**Why the bundled server and not `python3 -m http.server`.** That serves the whole directory, and these files usually land in Downloads. `serve.py` binds loopback only and answers every path with the one file it was given, so a stray request cannot list or fetch anything else.

Run it in the background, read the URL from its output, hand that to the user. Say the port dies when the process does.

## Watch for questions

The page asks back. Selecting text on it floats an **Ask** chip; the question lands in `<stem>.questions.jsonl` next to the HTML (serve.py prints both file paths on stderr). Serving is not finished until you are listening:

```bash
python3 assets/wait_question.py <stem>.questions.jsonl <stem>.answers.jsonl
```

Run that in the background too. It blocks until a question has no answer, prints the pending question(s) as JSON lines (`id`, `stop`, `selection`, `question`), and exits; that exit is your wake-up. Answer it, then restart the waiter. Append the answer with the same helper, text on stdin:

```bash
python3 assets/wait_question.py <q.jsonl> <a.jsonl> --answer <id> <<'EOF'
- the gate at `formmap.go:50` runs before any mapping is read
- "no" there marks every `properties[]` path NotApplicable, so nothing downstream can invent a value
EOF
```

The page polls and pins the answer under the stop the selection came from, so answer in the page's own voice: 2 to 4 bullets starting `- `, glanceable, `file:line` in backticks, an editor link as `[formmap.go:50](cursor://file/...)` when pointing somewhere is faster than describing it. No paragraphs; the presenter reads this mid-call. The card renders only that mini-markdown (bullets, backtick code, `cursor://`/`vscode://`/http links), nothing else.

A selection inside an existing card threads: the follow-up arrives with a `parent` id and its card nests directly below the card it questions. Answer it the same way, by id; context is the parent card's answer.

A question starting with `/skill-name` is a skill invocation: invoke that skill and apply it to the selection (or to composing the answer), same as if the user typed it in the terminal. The page's `/` dropdown offers the skills you embedded via `{{SKILLS}}`. If someone hand-types a skill you excluded (code-editing, review, anything that cannot finish as a card), do not run it; say on the card what it does and why it needs the terminal instead.

Keep the watch loop running until the user says stop. Questions asked while nobody is listening queue in the file and the card says so; answer them whenever the user brings the walkthrough back up.

## Read the system before you write the file

Three things depend on where this is running. Detect them, do not assume.

**Editor scheme.** Do not assume, and do not ask. Run the bundled probe:

```bash
python3 assets/editor.py     # prints "cursor://file" or "vscode://file"
```

**Cursor wins when both are installed.** A machine with both is almost always someone who moved to Cursor and never uninstalled VS Code, so Cursor is the live editor and VS Code is residue. VS Code is the fallback, not a tie-break.

The probe checks the CLI on `PATH` first, then the platform's install locations: app bundles on macOS (`/Applications` and `~/Applications`), Programs directories on Windows, desktop entries on Linux. If neither is found it exits non-zero and prints nothing on stdout, which is a real answer: write the `file:line` text without anchors rather than emitting links that silently do nothing when clicked.

Getting this wrong is the worst failure this document has, because it only surfaces mid-call, on the first click, in front of the reviewer.

**Path shape.** Absolute paths, in the platform's own form. On Windows that means `vscode://file/C:/Users/...`, forward slashes, drive letter kept.

**Opener.** `open` on macOS, `xdg-open` on Linux, `start` on Windows. `serve.py --open` already picks by platform, so prefer passing the flag over shelling out yourself.

If port `8477` is busy, `serve.py` walks up to the next free port and says so on stderr; a different port is a different origin, so the browser will ask to allow the editor link once more on that origin. Pass that warning on rather than letting it surprise the presenter mid-call. If the browser cannot resolve `walkthrough.localhost` (rare, some non-mainstream browsers), `http://localhost:<port>/<slug>/` reaches the same server.

## Optional closing sections

Only if they carry weight:

- **Spare tabs** — what to have open in case a question goes sideways, usually the tests and the diff
- **If they push** — the two or three points most likely to be challenged, each with its one-line answer

## What this is not

Not documentation. Not a design doc. Not something anyone reads without a call happening. It has one job: keep a person oriented while they talk and click at the same time. Anything that does not serve that comes out.
