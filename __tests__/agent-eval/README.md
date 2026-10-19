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
exposure and resume behavior still need a paid driver smoke check. Any Codex
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

Tokens come only from driver usage: Codex `turn.completed.usage`; Claude's final
`result.usage`, without double-counting streaming assistant usage blocks. Claude
input total includes uncached + cache-read + cache-write; Codex input total
already includes cached reads. Missing usage is an error, never zero. Input
cache writes not exposed by Codex are null, not guessed. Neither driver exposes
cached output; `outputCached:null` is distinct from generated `outputUncached`.
Raw events and incremental receipts persist under `OUT.artifacts`, including
last-driver output/stderr on driver errors. Temporary TLS credentials, servers
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
