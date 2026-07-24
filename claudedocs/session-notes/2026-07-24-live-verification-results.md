# Handoff: live verification results → local integration run and release

**From:** cloud session, 2026-07-24 (partial egress)
**Supersedes the unknowns in:** `2026-07-24-repo-health-handoff.md`
**Branch:** `claude/zlibrary-repo-health-cont-06cqz0` (same commit as PR #15 head, `b1e3fd1`)
**PR:** [#15](https://github.com/loganrooks/zlibrary-mcp/pull/15) — still open, still unmerged

Two of the three previously-unverified items are now settled. The third needs credentials
this container did not have.

---

## The headline: the Z-Library integration works

This was the open question. It is answered, and the answer is good.

`/eapi/book/search` returns `['books', 'exactBooksCount', 'pagination', 'success']` — the
contract the code expects. Verified not just with `curl` but through the project's own code
path: `EAPIClient.search()` + `normalize_eapi_search_response()` returned correctly
normalized results (Heidegger, *Being and Time*, 1962, Basil Blackwell, 589pp, with
`cover`/`url`/`hash` populated). **No EAPI drift.**

### But `npm run doctor` fails by default here, for an environmental reason

```
FAIL  zlibrary:eapi/info/domains  ConnectError:
FAIL  zlibrary:eapi/book/search   ConnectError:
WARN  annas-archive:search        reachable but no /md5/ links found
WARN  libgen:search               ConnectTimeout:
```

This container's egress is **SNI-filtered, not proxy-blocked** — unlike the previous
session, where the agent proxy returned `403 CONNECT`. Here the tunnel is established
(`HTTP/1.1 200 Connection Established`) and the reset arrives at TLS Client Hello, for
specific names only. `example.com`, `libgen.li`, and `annas-archive.li` all return 200.

`z-library.sk` is blocked here; `articles.sk` is not. Upstream itself advertises
`z-library.sk` as `contentAvailable: true`, so the domain is alive. With a reachable domain:

```
$ ZLIBRARY_EAPI_DOMAIN=articles.sk npm run doctor
OK    zlibrary:eapi/info/domains  5 domain(s) advertised: z-library.sk, 1lib.sk, article.sk...
OK    zlibrary:eapi/book/search   JSON response with keys: [books, exactBooksCount, pagination, success]
2 passing, 0 required failing, 2 optional failing
```

**On a normal network, expect `OK` on both without the override.** If a `zlibrary:*` row
fails for you locally, that is real.

---

## New findings — none of these were known before

### 1. `annas-archive.li` is a parked domain, and the code sends the API key to it

The default `ANNAS_BASE_URL` (`lib/sources/config.py:28,47`) no longer belongs to Anna's
Archive:

- TLS cert `CN=egyptianculture.net`, Let's Encrypt, issued 2026-07-16
- Resolves to `lb-182-250.above.com` — Trellian/Above.com domain parking
- Body reads "This domain may be for sale", loads `assets.abovedomains.com/.../forsale.min.js`

`lib/sources/annas.py:122-133` sends the key as a URL query parameter:

```python
url = f"{self.base_url}/dyn/api/fast_download.json"
params = {"md5": md5, "key": self.secret_key, "domain_index": 1}
```

So any user with `ANNAS_SECRET_KEY` set and the default base URL discloses it to a third
party, in a query string, over a connection that terminates at a parking service. Search
queries go the same way.

**Not fixed — awaiting a decision.** The obvious repair is to default to
`annas-archive.org` and refuse to send the key to an unverified host, but this container
cannot reach `.org` or `.se` to confirm which mirror is currently canonical. Verify that
locally before changing the default.

The doctor already flags this as a `WARN`, but attributes it to a layout change. Teaching
the probe to recognise a parking page would turn a vague warning into a specific one.

### 2. The LibGen probe checks a mirror the code never uses

`scripts/check_upstream.py:154` hardcodes `libgen.is`. `lib/sources/config.py:29` defaults
`libgen_mirror` to `"li"`. `libgen.li` returns 200; `libgen.is` times out. So the `WARN` is
misleading, and it contradicts the script's own docstring — "Mirrors the runtime defaults
in `lib/python_bridge.py` and `lib/sources/config.py` so the probe reports on what the
server would actually contact."

### 3. Two corpus documents have no recall baseline

Inside an otherwise-green corpus run:

```
SKIPPED test_recall_baseline.py:86 — Baseline text file missing for DerridaJacques_OfGrammatology_1268316.pdf
SKIPPED test_recall_baseline.py:86 — Baseline text file missing for UnknownAuthor_MarginsOfPhilosophy_984933.pdf
```

The PDFs hydrate fine; the *baseline text* artifacts are absent. Recall is therefore
unmeasured for two corpus documents and skips silently. This is the "false green over zero
documents" failure mode from the previous handoff, in miniature — worth closing before
Phase 20 builds scoring on this corpus.

### 4. One test is fragile by construction

`__tests__/python/test_garbled_performance.py:168` asserts `avg_time < 0.01` from a plain
`time.perf_counter()` loop with no benchmark fixture, so `--benchmark-disable` does not
exempt it. It will misfire on any loaded or instrumented runner, CI included.

---

## Test state

Full suite, LFS hydrated, run three times:

| Run | Coverage | Result | Wall clock |
|---|---|---|---|
| 1 | on | 2 failed, 1143 passed | 19:16 |
| 2 | off | **0 failed**, 1145 passed | 16:26 |
| 3 | on | **0 failed**, 1145 passed | 18:49 |

Final: `1145 passed, 30 skipped, 7 xfailed`, coverage **73.43%** against the 60% floor.

Run 1's two failures (`test_large_region_acceptable`, `test_markerless_continuation_detected`)
did not reproduce in either subsequent run. I proposed coverage instrumentation as the cause
and run 3 disproved it. They are intermittent; the cause is unidentified. Both pass in
isolation and within the corpus subset.

**Corpus baseline for Phase 20: 117 passed, 2 skipped, 0 failed of 119 collected.** Sound.

Integration tests: **33 collect, not 26** — 25 credentialed in
`__tests__/python/integration/test_real_zlibrary.py`, plus 8 in
`test_pipeline_integration.py` that need no credentials. **The 8 pass.**

---

## What is left, in order

### 1. Run the 25 credentialed tests — the only remaining unknown

```bash
uv run pytest -m integration --benchmark-disable -q
```

They have never run automatically. Expect friction: written against a live site months ago.
Distinguish a stale assertion from a genuine contract change; the latter belongs in
`ISSUES.md`. Metadata extraction expects ~60 terms and ~11 booklists per book.

They honor `ZLIBRARY_EAPI_DOMAIN`, so a blocked default domain is not a blocker — but on an
unrestricted network no override should be needed.

### 2. Decide the Anna's Archive defect

See finding 1. This ships in whatever release comes next, so decide before tagging.

### 3. Merge #15

`mergeable_state: clean`. **Squash-merge** — it disposes of the four commits still carrying
`Co-Authored-By: Claude` / `Claude-Session:` trailers (`c0fb5e8`, `bc0ae0c`, `7641508`,
`c427a47`) without a history rewrite.

The PR body currently ends with a `Generated by Claude Code` footer. Strip it before
merging, or it lands in the squash commit message.

### 4. Cut v1.3.0

Bump `package.json` to 1.3.0, move CHANGELOG `[Unreleased]` → `[1.3.0]`, then:

```bash
git tag v1.3.0 && git push origin v1.3.0
```

Verify what has never worked: `npm view zlibrary-mcp version` shows 1.3.0 (stuck on 1.0.0
since 2025-04-11), GHCR has `:1.3.0` and `:latest`, and the tag↔`package.json` check ran
rather than being skipped.

Then close #11 and #14 referencing the release, and dispose of the dangling v1.2.0 draft at
`untagged-2f888cb62d7894f40bf5`.

### 5. Enable the scheduled drift check

Add `ZLIBRARY_EMAIL` / `ZLIBRARY_PASSWORD` at
**Settings → Secrets and variables → Actions**. Names must match exactly — the workflow
treats an empty value as "not configured" and skips with a warning, which reads as success.

**Order matters:** `upstream-check.yml` exists only on the PR branch. GitHub shows the
*Run workflow* button only for workflows on the **default branch**, so it cannot be
dispatched until #15 merges. Secrets themselves are branch-independent and can be added now.

Secrets are safe here: the repo is public but you are the sole collaborator, no workflow
uses `pull_request_target`, and fork PRs never receive secrets. Note that `live.log` uploads
as a public artifact and artifacts are *not* secret-masked the way logs are — currently
harmless, since the run does not pass `--showlocals` and the `credentials` fixture
(`test_real_zlibrary.py:46`) would otherwise render its values into tracebacks. Keep
`--showlocals` off. Prefer a throwaway Z-Library account.

**Create the `upstream-drift` label** — it does not exist. The report job calls
`issues.listForRepo({labels: 'upstream-drift'})` and then creates an issue with it, so the
drift path fails at exactly the moment it is needed.

### 6. Then plan Phase 20

`$gsdr-plan-phase 20`, after reading
`claudedocs/architecture/phase-20-21-review-2026-07-24.md`. Task 20-00 (the orphaned
`scripts/run_rag_tests.py`) comes before any new scoring code. Close the two missing recall
baselines from finding 3 first, or the corpus scores over 117 of 119 documents while
reporting success.

---

## Environment notes

- **`git-lfs` is not preinstalled** in these containers: `apt-get install -y git-lfs`.
- **`git lfs install` fails** — the repo has its own `pre-push` hook and lfs refuses to
  overwrite it. Run `git lfs pull` directly; the hook is only needed for pushing LFS
  objects. Do not use `--force` unless you intend to replace the repo's hook.
- 19 LFS objects hydrate to real PDFs (22MB Derrida, 77MB Kant). Verify with `file`, not
  just exit codes.
- **Piping pytest hides its exit code.** `uv run pytest ... | tail` reports `tail`'s status;
  the first run here looked like exit 0 while 2 tests failed. Check counts.
- `~/.claude/settings.json` → `{"attribution": {"commit": "", "pr": "", "sessionUrl": false}}`
  does not travel between containers; re-apply per session.
- Do not add `console.log` to `src/` — stdout is the JSON-RPC channel and
  `__tests__/stdio-purity.test.js` will fail the build.
- Do not lower a coverage threshold to make a change pass.
