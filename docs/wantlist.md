# Want lists

The opt-in want-list prototype reads a list, matches one item at a time, and uses the
same acquisition bridge, session, deadlines, quota bookkeeping and disk receipts as
`download`. No extra is enabled by default.

Run the built CLI from the checkout (the npm bin is `zlibrary-wantlist`):

```bash
node dist/wantlist/cli.js run /absolute/path/reading.txt --sources libgen,zlibrary --out /absolute/path/books --dry-run --json
node dist/wantlist/cli.js run /absolute/path/reading.txt --sources libgen,zlibrary --out /absolute/path/books --json
node dist/wantlist/cli.js status /absolute/path/reading.txt --json
node dist/wantlist/cli.js choose /absolute/path/reading.txt ITEM_ID b
```

Configure credentials and `ZLIBRARY_OUTPUT_ROOT` as for the MCP server. Sources come
from `--sources`, the list header, then `BOOK_SOURCE_DEFAULT_ORDER`; no implicit
source is selected. Each source is searched in order. A download decision stops
that search, so put LibGen first if you prefer its available editions. Format
ranking applies within a source, rather than combining catalogues globally.

Plain text and Markdown accept `Title — Author`, en dash, double hyphen, hyphen,
and `Title by Author`, plus list/checklist markers. Title-only lines work too.
Trailing `(YYYY)` supplies a year. Options include `[exact]`, `[any]`, `[epub]`,
`[pdf]`, `[formats=epub,pdf]`, `[lang=german]`, `[vol=2]`, `[year=1927]`,
`[translator=Stambaugh]`, `[editor=Name]`, `[id=my-id]` and `[note=why]`.
Unknown options remain notes with parse warnings. Headers set defaults:

```text
# sources: libgen,zlibrary
# mode: any
# formats: epub,pdf
# language: english
Being and Time — Heidegger (1927)
The Republic — Plato [exact] [translator=Grube]
```

CSV and TSV require headers. JSONL accepts one object per line. Fields are title,
author, year, language, formats, mode, volume, translator, editor, notes, item_id,
and edition_note. Aliases include name, creator/authors, lang, format/extension,
edition, vol, why, id/work_id and wanted_edition. Other fields remain under `extra`.
Free-text wanted editions always ask a person. IDs otherwise derive from title,
author, volume and language; editing format, mode or notes retains identity.
Duplicate IDs are reported and processed once.

`any` accepts strong work matches and ranks format, language, catalogue quality,
pages, year, source order and stable identifier. Year does not filter editions in
this mode. `exact` requires affirmative supplied constraints; missing evidence can
allow one local edition probe unless `--no-probe` is passed. Ambiguous works,
languages, volumes, derivatives and near titles ask. Files are retained when local
metadata contradicts the selection, or cannot settle an exact probe.

Each run writes `<list basename>.wantlist/` beside the list (`--state DIR` overrides):

- `state.v1.json`: atomic, synced state after each transition; identifiers, never refs.
- `run.lock`: one live owner per list; a dead PID can be reclaimed.
- `receipts.v1.jsonl`: fetched/have outcomes and their file paths and evidence.
- `needs_choice.md`: up to three candidates and commands to answer.
- `report.md`: every item's outcome, including retained/dropped/duplicate entries.
- `choices.txt`: append-only choices mailbox, also writable with `choose`.

The state is authoritative; reports can be regenerated on a subsequent run.
Choices are `a`, `b`, `c`, `skip`, `keep`, or `retry`. A choice re-searches identifiers
to obtain a current process ref. A missing candidate asks `choice_unavailable`.
`keep` requires a retained file path; an occupied destination whose path is not
provided by the base error cannot currently be kept through this prototype.

Results are `fetched`, `have`, `needs_choice`, `waiting_quota`, `retry_later`,
`not_found`, `failed`, `skipped`, `dropped` or `duplicate`. Their reason says why:
for example `auto_match`, `exact_match`, `receipt_item`, `volume_unspecified`,
`constraint_unverified`, `quota_reserve`, `destination_busy` or `outcome_unknown`.
Pending items remain pending when a run stops before reaching them.

Z-Library quota is read live at startup and after uncertain outcomes. The default
reserve is **20**; use `--reserve 0` to use the full observed balance. Other clients
can change the balance. Unknown quota is labelled unknown; `--max-downloads N`
provides a run-wide cap. A reused artifact spends no transfer budget. LibGen has no
daily budget. Matching continues after quota runs out. No reset time is predicted.

Other run options: `--mode any|exact`, `--formats epub,pdf`, `--language english`,
`--max-minutes N`, `--no-probe`, `--dry-run`, `--retry-not-found`, `--retry-failed`,
`--redo ITEM_ID` (repeatable), `--state DIR`, and `--json`. The first SIGINT/SIGTERM
aborts the active bridge call and saves a resumable item; the second exits at once.
Exit 0 means terminal outcomes or choices; exit 2 is resumable quota/breaker/deadline
or interruption; exit 1 is fatal configuration, authentication or output failure.

Local edition inspection uses EPUB metadata from the standard library. PDF support
uses `pypdf` only if already available, otherwise `unverified: no_pdf_reader`.
The optional dependency extra and lock resolution remain deferred: offline locking
could not resolve build requirements in this build environment. No dependency was
installed or added to the base. The inspector returns metadata/checks, never page
text; OCR and sidecar annotation are outside this prototype.

Set `ZLIBRARY_EXTRAS=wantlist` to register the sixth MCP tool, `acquire_list`. Pass
exactly one of `path` or `items` (1–200 line strings or manifest objects), optional
`output_dir`, `sources`, `mode`, `choices` (at most 50), `dry_run` and `wait_s` (0–50,
default 20). Inline lists use a deterministic directory under the output root.
Repeated calls read/apply progress through the same process worker; another process
holding the lock returns `running_elsewhere`. The run ends when the server closes.
Fetched/have items are counted; details stay in files. Choice and failure reply
lists are capped, with omitted counts in `more`.
