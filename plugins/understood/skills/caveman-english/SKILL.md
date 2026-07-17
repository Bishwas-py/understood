---
name: caveman-english
description: Reword text into blunt, clipped, low-cognitive-load phrasing (drop articles, pronouns, helper verbs, use bare verbs, short plain words). Preserves the source's structure and ideas, only the wording changes. Use when the user invokes /caveman-english, asks to "caveman this", "make this blunt", "make this clipped", or wants a lower cognitive-load version of existing text. Operates on text the user pastes or references, never triggers proactively on Claude's own answers. Shared voice used by other "understood" patterns like forward-arrow.
---

# caveman-english

Rewords text into blunt, clipped phrasing to cut reading and cognitive load, without changing what it says or how it's organized. Structure stays: same paragraphs, same bullets, same set of ideas. Only the wording changes.

This is a voice, not a compressor. If the goal is trimming the content itself down to a gist, that's a different job (see forward-arrow, which uses this voice for its chain steps but also decides what to cut).

## Rules

1. **Keep the structure.** Same paragraph breaks, same lists, same order, same set of ideas. Nothing gets cut or merged for length. Only the wording inside each sentence changes.
2. **Drop what doesn't earn its place.** Articles (a/an/the), pronouns, and helper verbs go when the meaning survives without them.
3. **Use the bare verb.** Skip conjugation (-s, -ed, "to be") where it doesn't cost clarity: "parser open pdf", not "the parser opens the pdf".
4. **Short plain words over long ones.** "need", not "needs to"; "give back", not "return"; "check", not "validate" when a plainer word says the same thing.
5. **Let clauses sit next to each other instead of connecting them with words.** Caveman speech implies cause and effect through order, not conjunctions: "fail, backend send 400" over "if it fails, the backend sends a 400".
6. **Watch the symbols, don't turn it into math.** `=` is fine for "means/becomes" ("fail = 400"). Avoid `+` for joining more than two things, and avoid stacking more than one symbol in a single clause. Once a sentence needs more than one symbol to parse, it reads as an equation, not caveman speech. When in doubt, use a plain short word ("with", "and") instead of a symbol.
7. **All lowercase**, except source-specific terms that are case-sensitive on their own (product names, acronyms).
8. **Keep source-specific terms verbatim.** Tool names, product names, people, don't genericize them.
9. **Emphasis is selective, not blanket.** Most of the output stays plain text. Only two things ever get marked up:
   - **The important liner(s).** The sentence (or short run of sentences) that states the actual rule, decision, constraint, or definition, the line that is the point, not the lead-up to it. Wrap that in a single inline-code span (backticks). Terminal Claude Code renders inline code in its accent color, so this is what makes the payoff line pop out of the surrounding narrative.
   - **Section labels, if the source has named angles.** When the text is naturally split into labeled parts (e.g. "before" / "after", or two distinct topics), bold just the label word, followed by a colon, same convention forward-arrow uses for its headers. Don't bold anything else.
   - If nothing in the source is a clear rule/decision/definition, don't force one into existence. It's fine for output to have no blue line at all, plain caveman prose is still the default.
   - Context, background, and narrative sentences stay completely plain. No backticks, no bold. The restraint is what makes the emphasis mean something.

## Worked example

Input:

> Before, we tried giving the search endpoint a new job: it would open the file itself, split it into chunks, run a prompt per chunk, and hand back all chunk answers in one call. The lead said no. The search endpoint's job is one query in, one result out. It must not touch files and must not know about documents, so we closed both changes and undid this from search. After, the search endpoint stays unchanged from before this whole effort. It still just has two jobs: lookup (query in, result out) and rank (results in, ordered list out). No new file-opening code lives on search at all. The chunking work moves to the ingest endpoint instead. Ingest is already file-aware by design, so the new chunking logic sits there now, not on search.

Output:

**before:** we try give search new job. give it open file itself, split into chunks, run prompt per chunk, hand back all chunk answers in one call.

lead say no. `search job = one query in, one result out. search must not touch files, must not know about documents. so we close both change, undo this from search.`

**after:** search endpoint unchanged from before this whole effort. still just two jobs, lookup (query in, result out) and rank (results in, ordered list out). no new file-opening code lives on search at all.

chunking work move to ingest endpoint instead. ingest already file-aware by design, so new chunking logic sit there now, not on search.
