# Walkthrough page questions

Select text on a served walkthrough page, ask a question about it right there,
and get the answer back on the page from the Claude session that built the
walkthrough.

## Flow

select text -> Ask chip -> type question -> page POSTs {id, stop, selection,
question} to serve.py -> appended to `<stem>.questions.jsonl` next to the HTML
-> a background waiter in the building session exits, waking the session ->
Claude answers with full context, appends {id, answer} to
`<stem>.answers.jsonl` -> page (polling /qa.json while pending) pins a Q&A card
under the stop the selection came from.

## Pieces

**serve.py** stays single-file and loopback-only, gains:

- `POST /ask`: JSON body, size-capped (64 KB), fields capped (id 64, stop 64,
  selection 2000, question 2000 chars). Appends one line to the questions file.
  204 on success, 400 on bad body, 404 on any other POST path.
- `GET /qa.json`: `{"questions": [...], "answers": [...]}` read tolerantly from
  both jsonl files, so the page restores all cards on reload.
- Prints the questions/answers file paths on stderr at startup.

**assets/wait_question.py**, two modes:

- wait (default): poll both files every 0.5 s; when a question id has no
  matching answer id, print the pending question(s) as JSON lines and exit 0.
  Run in the background; its exit is the wake-up signal.
- `--answer <id>`: append `{"id", "answer"}` to the answers file, answer text
  read from stdin (heredoc-safe).

**template.html**: no dependencies added.

- Selecting 2+ chars inside `main` floats an Ask chip near the selection;
  clicking it opens a one-line input; Enter submits, Escape dismisses.
- The Q&A card renders immediately under the enclosing `ol.steps > li[id]`
  (page end if the selection is outside any stop): quoted selection, question,
  then "answering..." state.
- Poll `/qa.json` every 2 s only while something is pending; stop when all
  answered. After 60 s pending, the card flips to "queued, no session
  listening" but keeps polling; the question stays in the file for any later
  session.
- Answers render with a minimal transform after HTML-escaping: `- ` lines
  become bullets, backticks become `code`, `[label](cursor://|vscode://|http(s)://...)`
  become links. Nothing else.

**SKILL.md**: serving is not done until the session is watching. Start the
waiter in the background after serve.py; on wake, answer, append via
`--answer`, restart the waiter. Answer voice matches the page: 2-4 glanceable
bullets, `file:line` in backticks, editor deep links where useful, no
paragraphs. Watch until the user says stop; questions asked while nobody
watches queue in the file.

## Testing

- curl: POST /ask happy path, oversized body, malformed JSON; GET /qa.json
  merge and reload behavior.
- Round trip without a browser: POST, waiter exits with the question, append
  answer, /qa.json shows both.
- Real browser pass on a generated page: select, ask, card pending, answer
  arrives, card updates; reload restores the card.
