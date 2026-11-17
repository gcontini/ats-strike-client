# Working in this repository

Rules the code follows. They are not style preferences; each one is here
because breaking it has a cost we have already paid once. They come from the
ats-strike repository, where the client lived until it moved here.

## Shape

- **One job per class.** `HttpApi` speaks HTTP and nothing else. `Workspace`
  owns paths and moves and nothing else. `WorkingProcessor` decides where a
  job folder goes next and makes every move. If you cannot say what a class
  does in one sentence without "and", split it.
- **Depend on protocols, not implementations.** `CVApi`, `JDSource`,
  `Confirmer`, `Tracker` exist so the modes can be tested with no server, no
  terminal and no spreadsheet. A new source of job descriptions should be a
  new `JDSource` and no change anywhere else.
- **One-way dependencies:** `client → contracts`. The client never imports the
  server or the pipeline, and talks to them over HTTP only;
  `client/tests/test_architecture.py` enforces it. The contracts package
  imports nothing but pydantic — it is loaded by a frozen executable and has
  to stay cheap.
- **No hidden global state.** Configuration is passed in, not imported.
  Anything cached at module level must be immutable; anything personal must
  not be cached at all.

## Restraint

- **Build what was asked.** No speculative options, no "while we are here".
  A knob nobody asked for is a knob that must be documented, tested and kept
  working.
- **Prefer deleting.** Less surface has consistently been the better answer.
- **Simple over clever.** Each stage of the watcher takes one posting at a
  time. The stages run side by side — the inbox on a thread, the CV writer on
  a thread per server, you on the main thread — because most postings no
  longer need a question: a CV takes minutes, and it is written while you read
  the next posting. That is the one concurrency there is; still nothing inside
  a stage runs in parallel.
- **KISS: this runs for one person, not at scale.** Don't add retries,
  caching layers, queues, connection pools or config knobs to handle load that
  will never arrive.

## Tests

- No test may need an API key, a network or a terminal.
- Fake at the boundary: `CVApi` is a protocol, and the modes run against an
  in-memory one. The real client against real servers is
  ats-integration-tests' job, not this repository's.

## House rules

- `uv` for everything: `uv sync`, `uv run pytest`, `uv lock`.
- `contracts/` is a git submodule, the ats-strike-contract repository, shared
  with the server. Change it there, not as a copy; a change is a commit in
  that repository plus the new pointer here.
- Do not commit or push. Changes are left in the working tree for review.
