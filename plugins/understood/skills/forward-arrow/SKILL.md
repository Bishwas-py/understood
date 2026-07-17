---
name: forward-arrow
description: Rewrite a process/flow explanation into short arrow chains (step → step → step) to cut reading and cognitive load. Use when the user invokes /forward-arrow, asks to "make this understood", wants the "forward-arrow version" of something, or asks to "break this into arrows" / "understood-ify this". Operates on text the user pastes or references, never triggers proactively on Claude's own explanations. Part of the "understood" family of condensing patterns.
---

# forward-arrow

Condenses a process/flow explanation into arrow chains. Built for text like status updates, "here's how X works vs how it's supposed to work", or flow walkthroughs, where the underlying content is really a sequence of steps buried in prose.

The point of this pattern is to cut cognitive and reading load. That means default to the smallest output that answers what was asked, not the most exhaustive one the source material could support.

Node wording uses the caveman-english voice (see the caveman-english skill for the full rule set). This pattern handles finding the flow(s), scoping to what was asked, and chaining steps with arrows on top of that voice.

## Rules

1. **Scope from the request, default to one.** Read what the user actually asked for.
   - A plain ask ("help me understand this flow", "make this understood", `/forward-arrow` with no further qualifier) gets exactly one flow: the single chain that answers it. If the source describes several angles (current state, intended state, work remaining, etc.) but the request didn't ask for a comparison, pick the one angle that actually answers the question asked and leave the rest out.
   - Only produce more than one flow when the request explicitly asks for multiple angles, e.g. "before and after", "how it works vs how it's supposed to work", "current state, intended state, and what's left".
   - The number of sections in the output should never exceed what was actually asked for, even when the source could support more.
2. **Skip headers on a single flow.** If scope resolved to one flow, output the arrow chain(s) directly. No bold header, no colon-labeled title. A header on a single section is overhead the request didn't ask for.
3. **Label each section when there are two or more.** One short bold header per section, ending in a colon, lowercase, describing what that chain represents. A parenthetical qualifier can sit in the header itself when useful, e.g. "(the wrong version, being closed)".
4. **Render each flow as `step → step → step`, each node in caveman-english voice.**
   - Follow the caveman-english skill's rules for wording: drop articles/pronouns/helper verbs, use bare verbs, prefer short plain words, watch the symbols (no equation-stacking).
   - Keep source-specific terms (tool names, product names, people) verbatim, don't genericize them.
   - One line per chain. If a section genuinely has multiple parallel or alternate chains, stack them as separate lines under the same header. No bullets, no numbering.
   - A trailing parenthetical can carry status, caveat, or attribution for that specific chain, e.g. "(not built)", "(waiting on above)".
   - Wrap the whole chain line in a single inline-code span (backticks). Terminal Claude Code renders inline code in its accent color, which visually separates the chain from the bold section header above it. The trailing parenthetical stays inside the backticks too.
5. **Leave non-flow content alone, mostly.** A constraint, a standalone fact, anything that isn't a sequence becomes a short plain bullet, not forced into an arrow chain and not dropped.
6. **Nothing else.** No prose paragraphs, no restating what a chain already said, no closing summary.
7. **If nothing is sequential**, say so plainly instead of fabricating a chain. Arrows are reserved for genuine step-by-step or cause/effect content.

## Worked examples

Source material for both examples below:

> Right now when a user uploads a large PDF, the system just forwards the whole file to the assistant, which has to open the PDF itself, split it into pages, read every page, and hand back all the answers. That's not how it's supposed to work. The document parser should open the PDF, split it into pages, read each page, and hand back the page text and extracted facts. Those facts plus the user's own filled-in form answers should get combined into a single plain text prompt sent to the assistant, so the assistant only ever deals with answers, not files. To get there we still need work: the document parser currently only returns vectors, not text, so it needs to also return page text and facts. The ingestion step needs to call the document parser instead of sending things straight to the assistant. And the backend needs to include the user's filled form as extra context in the prompt, which nobody's built yet.

### Request: "help me understand this flow" (plain ask, default scope)

Output (one flow, no header, picks the flow that actually answers "how does this work"):

`big pdf → sent to doc parser → parser open pdf → parser split into pages → parser read each page → parser give back text + facts`
`facts + user's filled form → combined into one prompt → sent to assistant → assistant just answer, no file`

### Request: "before and after, how it works, how it's supposed to work, and what's left" (explicit multi-angle ask)

Output (three sections, since three angles were explicitly requested):

**how it works right now (unintended, needs closing):**
`big pdf → sent straight to assistant → assistant open pdf itself → assistant split into pages → assistant read each page → assistant give back all answers`

**how it's supposed to work:**
`big pdf → sent to doc parser → parser open pdf → parser split into pages → parser read each page → parser give back text + facts`
`facts + user's filled form → combined into one prompt → sent to assistant → assistant just answer, no file`

**work still needed:**
`doc parser → only give back vectors now, need also give back text + facts (not built)`
`ingestion step → need call doc parser instead of assistant (not built)`
`backend → need add user's filled form json as extra prompt context (not built)`
