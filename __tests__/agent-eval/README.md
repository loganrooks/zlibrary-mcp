# Offline agent interface evaluation

2026-10-19. Implements DESIGN-v2.1 §9 (and its explicitly inherited v2 §9).
This directory is evaluation infrastructure, not a new product interface. All
book data and file bytes are synthetic. No model call happens by default.

## Offline checks

From a checkout with Node dependencies and its uv `.venv` available:

```sh
npm run build
node __tests__/agent-eval/run.mjs --self-test --out test_output/agent-eval-self-test.json
node __tests__/agent-eval/run.mjs --dry-run --driver codex --out test_output/codex-plan.json
node __tests__/agent-eval/matrix.mjs > test_output/agent-eval-matrix.json
npm run test:rehearsal
npm test -- --runInBand
```

The self-test starts the **actual 12-tool A server**, uses a scripted MCP client,
checks the proxy's tool schemas, runs T1–T12's A paths, reads resulting files and
checks fixture identity bytes. It also checks real empty results for unknown
queries, format mismatch, history-only books and empty mode. Jest checks exact
matching, languages, inclusive years, translator separation, cursor/page replay,
wrong-decision argument mutations, usage parsing and comparison bars. Neither is
an agent-performance result. T5/T6/T10 are explicitly outside A's comparison bar.

The pin is `e2517b3e347584333f9c127a0217a3c574f6a22e`; another A can be
specified with `--a-pin SHA --server-root /checkout`. The runner requires that
checkout's HEAD to equal the pin and refuses production source changes on A.
It records SHA, source tree hashes (including vendored Z-Library), observed tools/list count, characters and UTF-8
bytes; it never checks out, stages or commits anything. Build the pinned checkout
before running it. B is a separately built worktree, recorded by SHA and hashes.

## Fixtures and isolation

[inventory.json](inventory.json) lists every fixed record, edition, translator,
source, paging row and account-history row. `../rehearsal/fake_catalogue.py` is
authoritative; the JSON is its dated inventory. There are 13 core Z-Library rows,
6 LibGen rows, 15 fixed rehearsal rows, 60 paging rows, and 2 history rows (one
also a rehearsal row). Account-history-only ID 901 is *Being and Time*, never
pre-created on disk and never returned by search. Each test task starts with two
remaining Z-Library downloads, except T11, which starts with zero. Transfers
spend quota at link issuance, even if subsequent acquisition fails; local reuse
cannot decrement this fake-side counter.

LibGen has *Persuasion* EPUB; Z-Library has PDF. The Graver–Long and Campbell
Seneca editions have distinct IDs, years, detail descriptions and bytes. *The
Glass Orchard* exists only on LibGen. *Phenomenology* has 60 stable volumes.
Arendt has three in-range and two out-of-range books. Anna's search is an
explicitly empty account catalogue, allowing ordered fallback without real
network access; it has no configured download key. Browser/challenge routes are
not simulated. The original rehearsal LibGen row retains its reserved advertised
MD5 for compatibility; it is **not an evaluation download target**. All five
evaluation LibGen downloads advertise the actual synthetic payload MD5.

The server receives only fake credentials and an allowlisted environment. Its PYTHONPATH
forces the selected build’s vendored Z-Library before any editable dependency
installation, so sharing a uv environment cannot silently select another checkout. The
rehearsal Python/Node fences reject non-fixture networking. Evaluation's Python
sitecustomize redirects LibGen httpx resolution/transfer URLs to the same TLS
fake; the real production HTTP clients, parsers, acquisition and digest checks
still execute. The fake exposes per-operation arguments and quota spend through
its loopback control endpoint, never login bodies or cookies. Model drivers do
not receive the fake control endpoint. Server diagnostics stay off stdout.

## Campaign matrix and future paid launch

`matrix.mjs --a-root /A --a-pin SHA --b-root /B --out /receipts` prints **15
commands**, never executes them: A/B, Q1 without text copy, Q2 configured order,
and B without history, each on Codex and Claude; Claude additionally has tool
search on. Main Claude arms have tool search off. The optional C arm is deferred.
A runner invocation needs `--paid` to execute a driver; do not use it until the
lead authorizes the real comparison. Example commands for that later campaign:

```sh
node __tests__/agent-eval/run.mjs --paid --arm A --driver codex --server-root /A --a-pin SHA --runs 5 --warm-runs 1 --out /receipts/A-codex.json
node __tests__/agent-eval/run.mjs --paid --arm B --driver claude --server-root /B --runs 5 --warm-runs 1 --out /receipts/B-claude.json
node __tests__/agent-eval/run.mjs --paid --arm B --driver claude --tool-search --server-root /B --runs 5 --warm-runs 1 --out /receipts/B-claude-search.json
node __tests__/agent-eval/report.mjs /receipts/*.json > /receipts/comparison.json
```

**Cell definition (implementation choice):** one full ordered T1–T12 episode,
with five independently identified replicates. Each replicate starts a fresh
model session for the cold episode, then continues that exact session for a warm
episode (more with `--warm-runs`). This keeps T2→T3 conversational context real;
T6 receives the actual scripted first page/cursor as stated prior context. T6's
setup is excluded from model decisions/usage; its server response is included in
the prompt. Cold/warm labels apply to episodes, not a claim that all twelve tasks
are individually first-turn cold. Each episode uses a fresh artifact subdirectory
to separate prompt-cache effects from pre-existing files. Provider limits are
reset per task, but counters are differenced rather than cleared. The underlying
server survives driver reconnects so refs remain live. Independent replicates
use fresh model sessions and destinations; they share the same server process.

**Q1:** proxy removes only the text copy when structuredContent exists; schemas
stay fixed. **Q2:** `BOOK_SOURCE_DEFAULT_ORDER=libgen,zlibrary` versus unset;
`--default-order-env NAME` can adapt a future build (recorded in receipt).
`ZLIBRARY_OUTPUT_ROOT` bounds B's destinations. **History-disabled:** proxy
unregisters history on tools/list and rejects calls; account history is not
replaced with disk receipts. T7 must admit inability; any download/quota is wrong.

## Driver pins and settings

[drivers.js](drivers.js) constructs exact argv arrays (no shell interpolation).
`--dry-run --driver NAME` records the full command, environment changes and model.
Offline-observed CLIs: **Codex 0.162.1**, **Claude Code 2.1.303**. Launch refuses a
version mismatch. Default model IDs are **gpt-6.1-sol** and
**claude-opus-5-5**, both with explicit high effort, default temperature. Model
availability and the Anthropic full model ID have **not** been established by a
paid invocation; `--model EXACT_ID` is recorded when the lead supplies a different
pin. No silent fallback model is configured.

Claude flags: `-p --model claude-opus-5-5 --effort high --output-format stream-json
--verbose --setting-sources '' --strict-mcp-config --mcp-config /CELL/mcp.json
--tools '' --allowedTools 'mcp__books__*' --permission-mode dontAsk
--disable-slash-commands --system-prompt 'Evaluation NONCE…' --session-id UUID`.
Warm turns replace `--session-id` with `--resume UUID`. Tool-search-on uses
`ENABLE_TOOL_SEARCH=true`, `alwaysLoad:false`, `--tools ToolSearch`, and also
allows `ToolSearch`; main arms use `ENABLE_TOOL_SEARCH=false`, `alwaysLoad:true`.
`MCP_CONNECTION_NONBLOCKING=0` fixes startup behavior. Every
`DISABLE_PROMPT_CACHING*` model override is explicitly removed from the inherited
environment. Caching is on, not set to the string `false` (which can still disable
it). The actual driver request behavior is untested without paid execution.

Codex flags: `exec --ignore-user-config --ignore-rules --skip-git-repo-check
--json --model gpt-6.1-sol --disable code_mode_tool_search --disable code_mode
--disable multi_agent --disable memories --disable plugins --disable shell_tool`,
plus recorded `-c` values for high effort, read-only sandbox, no approvals, web
search disabled, the single stdio `mcp_servers.books` proxy and fixed developer
instructions. Warm turns use `exec resume UUID` with the same settings. Local
`codex features list` shows `code_mode_tool_search` and `code_mode` available;
legacy `tool_search` and `tool_search_always_defer_mcp_tools` are removed and are
**not** passed. A supported provider-cache flush/off control was not found. Tool
exposure/resume were exercised only on the lead's supplied Codex 0.162.1 smoke
path; no new driver invocation is part of this repair. Any Codex
command/web/file-change event invalidates the cell; fixture metrics are captured
at the broker, not inferred from model narration.

Sources checked 2026-10-19: [Codex non-interactive usage](https://developers.openai.com/codex/noninteractive)
(`turn.completed.usage`, JSONL and resume), [configuration reference](https://developers.openai.com/codex/config-reference)
(removed tool-search switches), [Claude MCP](https://code.claude.com/docs/en/mcp#configure-tool-search)
(search env and alwaysLoad), [Claude env vars](https://code.claude.com/docs/en/env-vars)
(non-empty DISABLE_PROMPT_CACHING disables caching), plus installed CLI `--help`,
`--version`, and Codex `features list`. No claim about account settings follows.

## Scoring, receipts and strict cold limit

`tasks.js` is the explicit per-arm oracle table; `oracles.js` scores tool **and
argument** decisions with original argument values, selection provenance, file
identity bytes, edition/source/format/year/cursor correctness, required details,
read-only tasks and honest negative answers. Calls, invalid calls,
ref_unavailable, per-task fake quota spend, final answers and raw tool replies
are saved. File paths in receipts are ephemeral: the bytes are checked before
cleanup, not promised to remain available. No provider quota is real.

Tokens come only from driver usage: Codex `turn.completed.usage` (now normalized
from cumulative totals per the round-1 repair below); Claude's final
`result.usage`, without double-counting streaming assistant usage blocks. Claude
input total includes uncached + cache-read + cache-write; Codex input total
already includes cached reads. Missing usage is an error, never zero. Input
cache writes not exposed by Codex are null, not guessed. Neither driver exposes
cached output; `outputCached:null` is distinct from generated `outputUncached`.
Raw events and incremental receipts persist under `OUT.artifacts`, including
uniquely named per-attempt output/stderr and a latest-output alias on driver errors. Temporary TLS credentials, servers
and files are removed on normal completion/error.

A fresh session is **not** evidence of an empty provider cache. A unique cell
nonce reduces reuse but cannot establish which definitions were cached. Claude's
first-request cache-read counter is retained. Codex's final turn aggregate does
not establish first-request cache status, so its strict cold eligibility stays
unknown. `report.mjs` deliberately returns **inconclusive** rather than passing
the strict cold bar without that evidence. Resolving this needs a measured
driver/transport receipt from the lead, not a fabricated cache-disable flag.

The report gives median and min/max spread, cold input totals and summed warm
input totals separately, wrong-decision/zero-where-A-zero and overall/per-task
success checks, tool-list size, no-quota absolutes, and history usage. A history
call in any enabled arm means retain history. Zero observed calls in an
incomplete matrix does not authorize removing it. Scripted/dry receipts are
never compared as model results. Live providers, tunnels, ChatGPT rendering,
want lists, and strict first-request Codex cache telemetry remain untested.

## Round-1 repair contract (supersedes the original scoring/scope wording above)

2026-10-19. Authority: `EVAL-FIXTURES-sol/FIX-EVAL-r1.md`,
`ZLIB-EVAL-GATE-astra-r1.md` and root's `ZLIB-EVAL-GATE-DISPOSITION-r1.md`
under campaign evidence. Root corroborated six concrete evaluator counterexamples;
this repair does not claim a new paid matrix or a fresh review gate.

### Answers are not paths (EVAL-R1-01)

Every scored row now retains `pathCorrect` separately from `answer.status`.
T2 checks translator/year associations, T4 the actual fake-side remaining quota
and LibGen cap, T7 affirmative membership in the **observed account history**, and
T12 the observed matching titles. T5 and the A filename/history-disabled negative
controls also have explicit fact contracts. An unknown answer cannot pass merely
because its tool trace is correct. `success:null` / `manual-review` means the
prose cannot be confidently scored by this deterministic evaluator; it is not
silently counted as success or omitted from a denominator. Such evidence is
ineligible for an automatic comparison until resolved outside this scorer.

The runner appends a JSON-only answer-shape instruction for these tasks. The
instruction uses placeholders, never the expected translations, years, quota
number or result titles. Arrays must contain all matching observed facts; the
example is an item shape, not a count. `answers.js` compares exact keys/types and
facts; swapped editions, duplicate translators, extra contradictory properties
and duplicate JSON keys cannot pass. The original scripted control's *whole*
canonical sentences/list grammar also remains supported. Arbitrary prose,
including correct-looking text followed by a contradictory sentence, goes to
manual review. This is intentionally not a general semantic judge. Other
acquisition tasks still require their real artifact and decision checks.

### Evidence admission and bars (EVAL-R1-02/03/05)

`admission.js` requires receipt schema 2, the exact completed measured status,
`sourceStable:true`, `fencePassed:true`, no receipt/task driver/fence/source/cleanup
failure, fixed model/CLI/build/settings, complete nonnegative usage and decision
metrics, and the exact unique `(run, phaseIndex, task)` grid. There must be five
replicates; each has T1–T12 at cold index 0 and at every configured warm index.
Sessions remain identical through a replicate and differ between replicates.
CLI version/requested model fields must agree throughout. Build SHA, baseline
pin and all production tree digests must be present and consistent.

Invalid, legacy, failed, ambiguous-answer and incomplete receipts remain in
`diagnostics`, with rejection reasons, but are never aggregated as eligible
model evidence. Multiple same-key receipts are refused as duplicate or
incompatible complete cells, not concatenated. A/B may have different build
identities and the explicitly selected arm changes, but their driver/model/CLI,
baseline and other comparison settings must agree. No receipt format can attest
an unreported server-side model alias change; these are requested model pins.
The runner now persists final source/fence/cleanup failures as failed status.

Root settled the success-estimator interpretation: gate empirical success
**counts/fractions** overall and per common task, not binary-success medians.
Tokens, calls and wrong decisions retain medians and min/max spread. When A's
median wrong decisions for a task is zero, **every** B observation for that task
must be zero. The nine common tasks exclude T5/T6/T10 as before; B's T5 additionally
has a B-only negative guard requiring correct inability, no forbidden
search/download, zero wrong decisions and zero quota. A's T5 remains outside
relative totals. Invalid evidence or a failed guard cannot become `bar met`.

### Attempts, including rejected calls (EVAL-R1-04)

The broker traces the attempted name/arguments before checking exposure. Unknown
or disabled calls record rejection/error and `forwarded:false`, without invoking
the production server. They count as calls, invalid calls and off-oracle decisions.
The real-A scripted self-test also sends an unknown request through the actual
proxy and checks one retained invalid/off-oracle attempt with no forwarding;
this is not a B-runtime integration claim.

`reconcileAttempts` consumes explicitly identified Codex `mcp_tool_call` events
for server `books` and Claude `mcp__books__…` tool-use/result events. Started and
completed forms are merged by driver call ID; completed events may use arguments
already observed at start. Matching against broker calls is a name/argument
multiset: each broker call can match only one driver attempt. A rejected call
seen at both layers is counted once. A recognized CLI-side rejection with no
broker call is added to the trace with its exposed arguments. If the name/ID is
known but arguments are unavailable, the attempted call remains diagnostic and
telemetry is marked incomplete; arguments are not invented. An apparently
successful unmatched attempt invalidates the cell rather than disappearing.

The drivers may suppress attempts before emitting any identifiable event. That
signal is unavailable: zero *recognized* extra attempts is not an attestation
that a CLI never rejected anything internally. Opaque CLI errors remain driver
failures, not invented tool names/counts. These parsers are deterministic fixture
tests, not a new paid confirmation of either driver's event coverage.

### Usage scope is CLI/path bounded (EVAL-R1-06)

Root's supplied two-turn smoke and exact-OK probe recorded Codex 0.162.1 totals:
input/cache-read/output **39031/19328/118**, **78605/58240/236**,
**101125/77952/241** in the same session. The +5 output for exact OK corroborated
cumulative, not per-invocation, counters on that path. This lane reuses those
numeric receipts only; it does not rerun models.

`usageFrom('codex')` preserves raw cumulative counters/snapshots and selects the
last total, never sums snapshots. A version-bounded tracker starts from zero for
the first invocation, then differences the exact resumed session's counters
before task/episode aggregation. T7 deltas are 39574 input, 38912 cache-read,
662 uncached and 118 output; the third turn is 22520/19712/2808/5. Cache writes
are differenced when exposed; missing writes stay null. Negative/incomplete
counters, disappearing optional counters, derived negative uncached input,
unexpected session IDs and uncorroborated CLI versions fail closed. Receipts
retain the raw totals, prior totals, normalized `scope:session-delta` and source
provenance. Admission independently recomputes the deltas in exact task order.

Claude's `result.usage` remains invocation-scoped, not differenced on an assumption
borrowed from Codex. No Claude process ran in this repair. Neither driver exposes
a cached-output split here; outputCached stays null. **Codex first-request cache
eligibility remains unknown**, and its aggregate cumulative counters cannot close
the strict cold bar even after normalization.

### Offline repair checks

```sh
node --experimental-vm-modules node_modules/jest/bin/jest.js __tests__/agent-eval/ --coverage=false --runInBand
node __tests__/agent-eval/run.mjs --self-test --a-pin f9d56a04d79c6e84a087e68481db2b66b2798c65 --out /private/tmp/eval-r1-self-test.json
```

`regression-controls.json` preserves the root's actual A read-only traces and
recorded numeric usage probe with provenance. `receipt-controls.js` constructs
synthetic complete receipts solely for positive/negative report controls; these
are not observations about model performance. The tests reproduce all six
reviewer/root counterexamples plus malformed/duplicate grids, warm indices,
CLI/model/session mismatch, missing usage, ambiguous facts, delta resets and
cross-layer rejection deduplication. The real A positive exercise remains
separate. No B runtime/full matrix/live-provider boundary is closed by these
checks; root owns the fresh round-2 gate and git operations.
