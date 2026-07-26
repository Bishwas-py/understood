---
name: rundown
description: Build a self-contained HTML rundown for presenting a change to a senior reviewer live, step by step through the real code. Use when the user invokes /rundown, asks for a walkthrough of a change, or says they have to "walk someone through" a PR/feature/codebase, "present this on a call", "demo the code", or wants "a script for the review". Produces one HTML file of clickable file:line stops carrying operable live blocks (switch, dial, chain, race...) whose controls are the code references themselves, never prose to read aloud. Part of the "understood" family of low-cognitive-load patterns.
---

# rundown

Turns a change you have to defend into a document you can drive a live screen-share from.

The reader is the presenter, mid-call, talking. They glance at the page and look back at the editor. So the page carries **cues, not sentences**. Anything they would have to read aloud has already failed.

## What it produces

Exactly one file: a self-contained HTML page built from `assets/template.html`.

- a pipeline block first: the whole journey in arrow lines, one real record from an actual run riding along, every line stamped with where it lives (`#page`, `#server`, ...)
- stages down the middle ordered by the data's journey, each stop a place to put the cursor
- a claim-checks section at the end, generated on demand, each row tickable with a running count
- floating sidebar, every stop listed by `file:line`, current position highlighted on scroll
- every path and every bare line number is a link that opens the editor at that exact line
- live blocks inside the stops: operable components (a switch, a dial, a chain) whose control surface is a code reference; understanding is operated, not read
- ask-from-selection: the reader's questions land as cards floating beside the highlighted text, answered live by the session that built the page; a discussion section at the end of the page takes questions not tied to any selection and can ask the session to reshape the page itself (Cmd+K jumps to it, and with a selection active Cmd+K quotes it there)
- light and dark, prints, no external requests, no build step
- served on a memorable local hostname so the user gets a URL, not a file path

Default output: `.rundown/<slug>/page.html` inside the repo it is about, then served on a stable local origin and handed back as `http://rundown.localhost:<port>/<slug>/`. Honour an explicit path if the user gives one.

## Before writing a single line

**Read the real code.** Every line number in this document is a promise. A stop that opens the wrong line in front of the reviewer costs more credibility than the whole document earns. Open each file, confirm the symbol is on the line you cite, and confirm the file exists on disk before writing its link.

**Get the change.** The diff, the PR, the branch. What is actually new versus what was already there.

**Find the entry point.** Not the most interesting file. The place the request or the data actually enters the system.

## Write for how the reader reads

The reader is a presenter defending code they did not write. The document must carry the understanding to them; a rundown that only works for its author is a diff with decoration. Eight rules, and they outrank stylistic preference:

1. **Flow over structure.** A -> B -> C with data moving through, never components-and-their-responsibilities. A stop that cannot say which stage of the journey it is in does not belong.
2. **Data before implementation.** The unit of understanding is the record moving through the system, not the function. "form JSON in, ~30 answers and a leftover list out" is presenter knowledge; "what settleFromForm does" is author knowledge.
3. **In and out before how.** Name what enters and what leaves before any mechanism; in a live block that boundary is what the reader operates, not a labeled box.
4. **One real instance rides the whole page.** A name, a number, a filename from the actual run. If a real run happened, harvest its values; schema-speak forces live translation mid-call.
5. **One idea per line, flat lists, bold lead word.** Never group a list under sub-headers. Each line survives alone.
6. **Change is a pair of states.** BEFORE what went wrong, AFTER what happens now. A single-state description leaves the reader asking "compared to what?".
7. **Stamp everything for routing.** Every heading and stop carries where it lives: `#page`, `#server`, `#session`, a repo name, config-or-code. The reader triages before reading.
8. **Compression by default, depth behind a question.** The page stays terse; depth lives behind the ask loop, pulled by the reader when a line deserves it.

Pick the format by situation, never by habit:

| explaining | format |
|---|---|
| a process or flow | arrow chain, stage by stage |
| a change | switch block; a BEFORE/AFTER pair when minor |
| one piece of the system | the live block its type calls for (see the block table) |
| a set of facts | flat numbered list, bold lead word |
| a decision | switch or dial block; BEFORE/AFTER pair for minor ones |
| something that may need depth | one line now; depth lives in the ask loop, the reader pulls it |

## Craft: the page has to be worth looking at

Beauty is not decoration here. A page the reader wants to look at is a page they keep looking at, and a rundown only works while someone is still reading it. Every rule below came from a real defect on a real page.

**Use the space you have.** If there is room, take it: wider nodes, more padding, longer line length. Crowded output reads as unfinished. A diamond only reaches full width at its middle, so text inside one needs roughly twice the room a box does; a cylinder needs height for its rim. Measure the shape, not the string.

**Draw the line, do not rule it.** A connector is always a curve: a soft wave when the two ends sit level, and one smooth sweep with its control points out in the margin when they are far apart, so it leaves and arrives horizontally and never turns a corner. Straight lines and elbows read as plumbing; a drawn line reads as a hand pointing. Keep the curve out of the text column, and route a chart's return edge outside the widest node rather than through whichever one is in the way.

**Nothing crosses anything.** A connector line must not run through a label, an arrow must not pass under words, a chip must not collide with the text beside it. When two things must share a spot, give the upper one a plate in the page background.

**Every layer knows its depth.** A highlight paints over text, a connector thread paints under it, a card floats beside it. Anything that would obscure reading belongs behind the text at low opacity, and lifts only on hover. The exception proves the rule: a thread whose mark sits inside a block would vanish under that block's panel, so it rides above instead. Depth follows what the line has to reach, not a single global choice.

**A pointer glows, it does not bracket.** The handle that ties a card to its text is a soft radial glow at the corner, not a drawn bracket. Hard geometry announces a widget; a glow suggests a place to put the cursor and disappears when it is not wanted. The thread lands in the middle of that glow rather than on the edge beside it, and is drawn as a blurred halo under a hairline core, so it belongs to the same soft family instead of arriving as wire.

**One weight of ink per idea.** A state label is a small pill, not a heading. A claim is bold, its proof is plain, a code chip is monospace. If two things look equally loud, the reader has to decide what matters, which is the job the page was supposed to do.

**Degrade visibly, never silently.** A card whose text was edited says so. A refused action says why. An empty section shows only its button, not an empty frame waiting to be filled.

**Escape exactly once.** Text is escaped at the boundary it is emitted from, and anything already html is marked as such and never processed again. Two bugs today came from breaking this: json escaped into a script tag it could not survive, and a pre-rendered chip escaped a second time so the anchor printed as source.

**Check it rendered, not that it was written.** Open the page, click every control, read the shapes at the width the reader will use. A number in the dom is not a thing that looks right.

## Ordering: chronology, then cursor

Two rules, in this order.

**1. Order stops by the life of the request, not by file, layer, or importance.** If work happens in phases separated by time (a synchronous request, then a queued background job, then a later user action), those are separate acts with their own headings. Making the phase boundary visible is often the single most valuable thing in the document, because it is where "does this block the user" gets answered.

**2. Inside an act, every stop must be reachable from the previous one by go-to-definition.** Open a file, click a symbol, land on the next stop. Never "now open this other file", the presenter loses their place and the audience loses the thread. If two stops are not connected by a call, either they belong to different acts or a stop is missing between them.

The hop lives in the ordering, not in the words. Stops stay reachable by go-to-definition, but the headline spends itself on meaning; the chip does the navigating. Name a hop inline only when the jump itself is the finding, for instance a call crossing a service boundary.

## Anatomy of a stop

A stop is three things, in this order: a **headline that states what this stop proves**, in a handful of words, with its `file:line` chip beside it; one **live block** that installs this stop's piece of the model; and at most two think-lines under it, each shaped `thing → meaning`. **The headline is a claim, never a direction.** Every chip is already a link and the sidebar already navigates, so words spent on "Open", "Click", "Scroll up to", "Back in", "Line 171" are words that taught nothing. Spend them on the finding instead: not *"Scroll up to `formmap.go:50` gates, the form's own yes/no doors"* but *"One 'no' closes every gift field before a single search runs"*. Real numbers from the run belong in the headline when they are the point ("33 of 119 fields never reach the PDFs", "0.35 clears the real page at 0.49"). If a stop cannot produce such a claim, it is not a stop.

Nothing else. No KEYWORD, no KNOW MORE, no IN/OUT boxes, no labels about the page's own taxonomy; a label appears only when it is an actor in the thought (WORKER, BEFORE, a function name).

```html
<li id="s3">
	<p><span class="action">One "no" closes every gift field before a single search runs</span> <a class="path" href="...">formmap.go:50</a> <code>gates</code></p>
	<!-- one live block here, from `rundown blocks <name>`, with its facts changed -->
	<ul class="think">
		<li><b>append holds a lock</b> → two clicks can land the same instant</li>
	</ul>
</li>
```

### Think lines

Under the block, at most two lines, each one `{claim, proofs}`. They are a real bullet list in a hand (Noteworthy), because these are the lines the reader copies into paper notes; code chips stay monospace so an identifier survives the copy.

```json
"think": [
  { "claim": "a late instance is refused",
    "proofs": ["{extraction_edit.go:107} returns a 400, never a phantom write"] },
  { "claim": "edits cannot overwrite each other",
    "proofs": ["the lock lives in {submission_extractions.sql:19}",
               "the test fires 8 concurrent edits, all 8 land"] }
]
```

One proof renders flat, `claim -> proof` on a single line. Two or more nest, the claim on top and the proofs beneath. **The proof count decides the shape, never the author.**

**The bold line is always a claim, never a location.** "the lock lives in `x.sql:19`" is an address; "edits cannot overwrite each other" is a finding, and the address drops to being one of its proofs. This is the headline rule applied one level down, and the validator enforces it.

### The live blocks

Every block declares what it takes, and the command prints it:

```bash
rundown blocks              # all fourteen, with the keys each one needs
rundown blocks race         # what a race takes, and a config to paste
rundown blocks --demo       # builds a page carrying every block, operable, on real refs
```

Paste the example into the stop's `block` and change its facts. The validator holds a config to that same declaration, so a missing key fails the build and a mistyped one is named in the warning rather than rendering a control that does nothing. Pick by what the stop IS:

| block | fires when the stop is | the reader |
|---|---|---|
| switch | a fix or decision | toggles the line in and out of existence, watches its world change |
| stepper | a transformation | drives one real value through its moments, each moment lighting its code ref |
| dial | a tuned constant | drags the value, watches the consequence, sees the shipped value marked |
| bind | an artifact (prompt, record, config) | hovers a clause, its meaning glows, and back |
| race | concurrency | runs two actors at one row, with and without the lock |
| ledger | a guarantee or invariant | tries to break it with buttons; it holds, and says why |
| probe | a parser or branch | feeds real inputs, watches which branch takes each |
| flow | the whole journey | reads a real flowchart drawn from mermaid source at build time, every node a code ref |
| map | the parts and who owns them | sees the skeleton as a row of linked nodes, for structure rather than sequence |
| space | vector search | embeds a query, watches the nearest pages light with scores |
| angle | similarity math | drags the angle, feels cosine fall past the shipped gate |
| stack | context assembly | assembles the window part by part against the token budget |
| chain | a function, call path, or a value's origin | clicks any hop for its value and one-line description, or runs the whole flow; forward for dataflow, backward for provenance ("trace this value back") |

**The block contract, non-negotiable:**

- the control is fused to a real `file:line` chip; what the line does and where it lives are one object
- every chip inside a block is an editor anchor, never plain text: `<a class="path" href="cursor://file/ABS/PATH/file.go:155">file.go:155</a>`, including the ones a block writes from JS (carry the href in a `data-href` or a `href` field beside the label). The template upgrades any chip left as a bare `span.path` when its filename appears in another anchor, but that is a safety net, not the plan
- every value shown comes from the actual run, never invented
- a block config holds text, never html. The renderer escapes every string in it exactly once, expanding `{chips}` and `` `backticks` `` on the way, so a `<b>` written in a spec reaches the reader as the characters `<b>`
- every interaction produces a visible utterance; a refused action says why it refused
- a running block disables its controls and says it is running ("racing…"); they restore when done
- a selected option shows its selected state
- one-line function descriptions appear only on essential stops, never everywhere
- a question asked from inside a block carries the block type and the part it came from, so an answer can say "node C of the flow chart" instead of guessing
- a mark in the text is threaded to its card with a faint curve behind the text; it lifts on hover and never crosses a word

Use a block only where operating it teaches something; a stop whose whole content is one fact takes a think-line, not a component. Volunteer the weak spot before the reviewer finds it, as a think-line or a BEFORE/AFTER pair. Never pose a question the reviewer already decided.

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

## Claim checks, not decisions

The page ends with a claim ledger, generated on demand rather than written at build time. The reader presses a button when they are done, the question travels the ask loop with `"via": "ledger"`, and you answer with one bullet per claim, each carrying its chip. The page turns those bullets into tickable rows with a running count.

Generate them from what the page actually claimed **and how far the reader took the conversation**: the stops they questioned deserve their claims spelled out, the ones they never touched can stay compressed. Before the button is pressed the section shows only the button, no empty frame.

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

**Every record, payload, and code sample is well formatted at birth.** Pretty-printed, indented, one field or statement per line, written that way in the HTML you generate. Never a crammed one-liner in a `.rec` chip or a `<pre>`; the reader should never have to ask for formatting. The template wraps code to the available width (`pre-wrap`), so pretty-printed content stays readable at any screen size; a one-liner stays a one-liner and helps nobody.

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

Generated by the renderer from the stages and stops, never hand-maintained.

- One entry per `<h2>`, nested entries per stop
- Stop labels are `file:line`, monospace, because that is what the presenter is hunting for
- Never label a stop "Back to line 141", strip the prose: `worker.go:141`
- Scroll spy highlights the current stop, script is already in the template

## Where a rundown lives

One folder per rundown, inside the repo it is about. The folder name is the identity, so nothing is keyed on a filename and a rebuild can never separate a page from its thread:

```
.rundown/ask-loop/
    spec.json          the truth, the only file anyone edits
    page.html          build output, overwritten by every build
    questions.jsonl    what the reader asked
    answers.jsonl      what you answered
    history/*.json     a copy of spec.json taken before each write
```

`store.py` adds `.rundown/` to `.git/info/exclude` on first use, never to the project's `.gitignore`, which is a tracked file in someone else's repo. History is the undo: to reverse an edit, copy a snapshot back over `spec.json` and rebuild.

One command drives all of it. Inside the plugin it is `python3 assets/cli.py`; on the user's PATH it is `rundown`, and they are the same file:

```bash
python3 assets/cli.py list                     # every rundown in this repo, with its question count
python3 assets/cli.py save  <slug> spec.json   # snapshot the old spec, write the new one, rebuild
python3 assets/cli.py build <slug> --fix       # code moved: put every ref back on the line its pattern finds
python3 assets/cli.py verify <slug>            # validate only, write nothing
python3 assets/cli.py serve <slug> --open      # every rundown on one origin, opened at this one
python3 assets/cli.py rm    <slug> --force     # deletes the conversation too, so it prints the counts first
```

The user can also install it as a real command, which is worth telling them once, since it means listing and serving old rundowns never needs a session:

```bash
curl -fsSL https://raw.githubusercontent.com/Bishwas-py/understood/main/install.sh | bash
```

## Build order

**Write a spec, do not write html.** The page is compiled from one json file, and the renderer owns every tag, id, and class. The spec holds `repo` (root, sha, editor), `pipeline`, `stages` of `stops` (headline, ref, block, think), `discussion`, and `skills`. `assets/example.json` is a complete working one. Refs are `{path, symbol, line, pattern}`; the pattern is the authority, since a symbol's first occurrence is usually a call site. Chips are written `{file.go:50}` in any text field and come out as editor anchors. Records go in raw and the page pretty-prints them.

A failing validate is a build error, not a warning: it means a line number in the page is a lie.

1. Write the spec. Start from `assets/example.json`, keep the ids stable, and let every ref carry a pattern.
2. `cli.py save <slug> <spec>`, which snapshots, writes, validates, and builds in one step. Add `--fix` when the only complaint is drift.
3. Serve, then start the waiter.
4. Read the built page at the width the reader will use, and click through every block.

The renderer owns the sidebar, the ids, the editor links, and the escaping. Never hand-edit `page.html`: the next build overwrites it, and the spec is the thing that gets reviewed, corrected, and rebuilt.

For a one-off with no repo behind it, `assets/template.html` can still be filled in by hand, but nothing validates that path and no block gets wired.

## Verify before handing over

Run all of these. Report the counts, do not claim it works.

`validate.py` already refuses a wrong line, a missing file, a nav-verb headline, a claim that is only a reference, an em-dash, and an unknown block type. What it cannot see, you check by looking:

- every block control operates: buttons press and restore, sliders drive their readouts, nodes and hops click, busy states disable and come back, refusals speak
- the page reads at the width the reader will use, and nothing crowds or crosses anything
- two or three sidebar links land where they claim
- the served URL returns 200, and the questions and answers paths printed on stderr are the ones you will watch
- a mark, its thread, and its card still line up after a resize

## Serve it

Hand back a URL, not a file path. A `file://` path cannot be pasted into a call, does not survive a screen share, and the editor links behave better from an http origin.

```bash
python3 assets/cli.py serve <slug> --open
```

It prints one line, the URL, and holds the port until interrupted:

```
http://rundown.localhost:8477/my-change/
```

One process serves every rundown in the repo: `/` is an index of them, `/<slug>/` is one page, and `/<slug>/qa.json` and `/<slug>/ask` are that page's conversation. So a second rundown does not mean a second port, and the browser's editor-link approval is never asked for twice.

Browsers resolve `*.localhost` to loopback on their own, no DNS and no `/etc/hosts` edit, and treat it as a secure context. That last part is the point: editor links (`cursor://`, `vscode://`) trigger the browser's "open this application?" dialog, and only a secure context gets the **Always allow** checkbox. The origin (host and port together) is what the browser remembers the approval for, which is why the host and default port never change and the slug lives in the path. Approve once, never prompted again.

**Why the bundled server and not `python3 -m http.server`.** That serves the whole directory, and a rundown folder holds the spec and the conversation next to the page. This one binds loopback only and answers nothing but the pages and conversations it knows about, so a stray request cannot list or fetch anything else.

Run it in the background, read the URL from its output, hand that to the user. Say the port dies when the process does.

## Watch for questions

The page asks back. Selecting text on it floats an **Ask** chip; the question lands in `.rundown/<slug>/questions.jsonl` (serve.py prints both file paths on stderr). Serving is not finished until you are listening:

```bash
python3 assets/wait_question.py .rundown/<slug>/questions.jsonl .rundown/<slug>/answers.jsonl
```

Run that in the background too. It blocks until a question has no answer, prints the pending question(s) as JSON lines (`id`, `stop`, `selection`, `question`), and exits; that exit is your wake-up. Answer it, then restart the waiter. Append the answer with the same helper, text on stdin:

```bash
python3 assets/wait_question.py <q.jsonl> <a.jsonl> --answer <id> <<'EOF'
- the gate at `formmap.go:50` runs before any mapping is read
- "no" there marks every `properties[]` path NotApplicable, so nothing downstream can invent a value
EOF
```

The page polls and pins the answer beside the text it came from. Answer to produce understanding, not coverage; a card of four dense bullets explains without landing. Build a think flow, in this order:

1. **Lead with the shape, not facts about it.** If the answer is a process, the first line is `flow: a -> b -> c` and everything else only annotates what the chain cannot carry. If it is a definition, the first line IS the definition, compressed: "upsert: try INSERT, row exists, UPDATE it instead".
2. **One concrete instance before any generality.** The real field, the real row, the real value from this run, in the first or second line. "leftover = net salary, AHV number, ~40 today" lands; "whatever survives the settling stages" alone does not.
3. **Answer the question asked, then stop.** 2 lines that land beat 4 that cover. The reply box exists; depth is theirs to pull.
4. **In and out before how.** Mechanism only if they asked how.
5. **Hard terms are fine, prose is not.** Keep the term, drop the sentence around it. `file:line` in backticks; an editor link `[repo.go:427](cursor://file/...)` whenever pointing beats describing.
6. **Changed things come as a pair.** before: x. after: y.

A selection inside an existing card threads: the follow-up arrives with a `parent` id and nests below the card it questions, showing the quoted fragment it carries in `selection`. Answer it the same way, by id; context is the parent card's answer.

The selection chip offers two intents. **Ask** stays inline: the answer pins beside the text. **Quote** carries the selection into the discussion section as an attached reference, and the record arrives with `"via": "spot"` plus the quoted `selection`; the conversation lives in the discussion thread. A quote is how the reader hands you a precise anchor, for a question or for an edit: "make this section shorter" with a quote means that section, and a morph or file rewrite scoped to it. A discussion record with no selection is a question about the whole change.

**A rewording carries its own mark.** When a page change rewrites text that a question was asked on, say what that text became and the mark follows it:

```bash
python3 assets/wait_question.py <q.jsonl> <a.jsonl> --answer <id> --rebind "did the form close this block" <<'EOF'
- reworded and rebuilt, node C now reads as a question
EOF
```

The card then carries both, the words that were quoted struck through and the words they became under them, so the reader can see the thread survived rather than guess. The build says which quotes went missing, and that list is what you owe a rebind:

```
orphaned: 888c4b73 quoted "gate closed this block", answer with --rebind to move its mark
```

**A page change is a spec change.** The discussion box can also command the page, and only when the reader explicitly asks for one (cut a stage, reword a headline, reorder stops, more room between lines). Never on an ordinary question. Whatever they ask for, the answer is the same shape: edit `spec.json`, `store.py save`, and say in one line what changed. Never patch the live page, and never edit `template.html` to satisfy something asked on a page: the template turns json into html and that is its whole job, so a change made there would silently apply to every rundown that follows.

A look request has a home in the spec too, so it survives the rebuild that a content edit would otherwise wipe:

```json
"look": [ { "id": "m1", "sel": ".think li", "css": "line-height: 1.9" } ]
```

Style only. There is no javascript escape hatch, because a page's behaviour comes from its blocks, and a script in the spec is a rule the validator cannot check. To undo a change, copy the snapshot back from `history/` and rebuild.

Answers are mini-markdown: `- ` bullets, backtick code, `[label](cursor://...)` links. Two richer forms, used only when the shape earns them:

- a line starting `flow:` (or a ```flow fence) renders as an arrow chain of pills: `flow: form JSON -> settle -> leftover list`. Use it whenever the answer is a process.
- an ```svg fence renders inline as a diagram. Hand-write it small (a few boxes and arrows, viewBox, currentColor strokes), no scripts, no event handlers, no external references; it is sanitized and falls back to plain code if it fails the check. A diagram is for structure that words genuinely cannot carry, one per answer at most.

Any other fence renders as a code block. Records and payloads go in plain backticks or a ```json fence; the page pretty-prints any JSON into an indented, wrapped block with tinted keys on its own, so paste them raw, never hand-wrap them.

A question starting with `/skill-name` is a skill invocation: invoke that skill and apply it to the selection (or to composing the answer), same as if the user typed it in the terminal. The page's `/` dropdown offers the skills you embedded via `{{SKILLS}}`. If someone hand-types a skill you excluded (code-editing, review, anything that cannot finish as a card), do not run it; say on the card what it does and why it needs the terminal instead.

Keep the watch loop running until the user says stop. Questions asked while nobody is listening queue in the file and the card says so; answer them whenever the user brings the rundown back up.

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

If port `8477` is busy, `serve.py` walks up to the next free port and says so on stderr; a different port is a different origin, so the browser will ask to allow the editor link once more on that origin. Pass that warning on rather than letting it surprise the presenter mid-call. If the browser cannot resolve `rundown.localhost` (rare, some non-mainstream browsers), `http://localhost:<port>/<slug>/` reaches the same server.

## Optional closing sections

The claim checks close the page. These come before them, and only if they carry weight:

- **Spare tabs** — what to have open in case a question goes sideways, usually the tests and the diff
- **If they push** — the two or three points most likely to be challenged, each with its one-line answer

## What this is not

Not documentation. Not a design doc. Not something anyone reads without a call happening. It has one job: keep a person oriented while they talk and click at the same time. Anything that does not serve that comes out.
