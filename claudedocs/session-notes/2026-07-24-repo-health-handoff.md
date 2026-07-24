# Handoff: repo health pass → live verification and release

**From:** cloud session, 2026-07-24 (network-restricted)
**Branch:** `claude/repo-health-roadmap-yrfq0p`
**PR:** [#15](https://github.com/loganrooks/zlibrary-mcp/pull/15) (open, 9 commits)
**Why a handoff:** three items cannot be verified from a sandbox whose egress to
Z-Library, Anna's Archive, and LibGen is proxy-blocked (403 CONNECT). Everything not
requiring live network is done.

---

## State at handoff

Green locally:

```
Jest             177 passed (12 suites)
Pytest (fast)    983 passed, 8 skipped, 184 deselected, 7 xfailed
pip-audit        1 advisory (was 74 across 15 packages)
npm audit        passes at --audit-level=critical
eslint/prettier  clean
docs-check       13/13 tools documented
```

What the branch changed, in one line each:

- **stdout is MCP-clean.** 13 `console.log` calls wrote to the JSON-RPC channel; all
  diagnostics moved to `src/lib/logger.ts` (stderr). This was the cause of issue #11.
- **Release pipeline unblocked.** `npm install -g npm@latest` failed all four publish
  runs; removed. npm has only ever served 1.0.0 (2025-04-11).
- **Audit gate closed.** Constraint floors refreshed; pytest 8→9, cryptography 46→49.
- **Upstream drift detection.** New scheduled workflow + `npm run doctor`.
- **Windows + path traversal.** PR #13 incorporated with 46 tests, plus `ntpath`
  hardening of its sanitizer.
- **Docs corrected.** `CLAUDE.md` described DOM scraping five months after the EAPI
  migration; coverage floors ratcheted (Jest 66→84, pytest 52→60).
- **Phases 20-21 reviewed and revised** — see
  `claudedocs/architecture/phase-20-21-review-2026-07-24.md`.

Full assessment: `claudedocs/architecture/repo-health-and-roadmap-2026-07-24.md`.

Issues handled: #13 closed (incorporated), #12 closed (not a real contribution), #11 and
#14 replied and left open pending a release.

---

## Environment this needs

| Requirement | Why | Symptom if missing |
|---|---|---|
| Egress to `z-library.sk`, `annas-archive.li`, `libgen.is` | The three unverified items all need live upstreams | `npm run doctor` reports `ProxyError: 403 Forbidden` for every source |
| `git lfs` installed | Corpus PDFs are LFS objects; this container had no `git lfs` at all | 8 tests skip with "unhydrated Git LFS pointer" |
| `ZLIBRARY_EMAIL` / `ZLIBRARY_PASSWORD` | The 26 integration tests skip without them | `pytest -m integration` collects but skips everything |
| Permission to force-push (only if stripping trailers — see task 4) | History rewrite was blocked by the permission classifier here | `git filter-branch` denied |

Setup: `npm ci && uv sync && npm run build`, then `git lfs install && git lfs pull`.

---

## Tasks, in order

### 1. Verify the upstreams actually respond — the headline unknown

```bash
npm run doctor          # human-readable
npm run doctor -- --json  # machine-readable
```

This probes response *shape*, not just reachability: the Z-Library EAPI checks that
`/eapi/info/domains` advertises domains and that `/eapi/book/search` returns JSON with a
`books` or `success` key. Anna's checks for `/md5/` links in the search HTML.

Expected on a healthy network: `OK` for both `zlibrary:*` rows. Anna's and LibGen are
`WARN`-only (optional — the router falls back between them).

**Report the full output.** Nobody currently knows whether this project's core integration
works against live Z-Library. That is the single most valuable thing this session can
establish. If a `zlibrary:*` row fails, that is a real finding, not an environment
problem — triage it before the release.

### 2. Run the credentialed integration suite

```bash
uv run pytest -m integration --benchmark-disable -q
```

26 tests that have **never been run automatically**. They exercise real search, metadata
extraction (expect ~60 terms and ~11 booklists per book), and download. Expect some
friction on first run — they were written against a live site months ago. Distinguish
carefully between a stale assertion and a genuine upstream contract change; the latter
belongs in `ISSUES.md`.

### 3. Run the full suite with LFS hydrated

```bash
git lfs install && git lfs pull
uv run pytest        # includes 119 slow/ground_truth corpus tests, ~12min
```

The 8 tests that skip here should now run. Confirm the corpus tests pass — they are the
baseline Phase 20 will build scoring on, so a pre-existing failure matters.

### 4. Decide the attribution trailers, then merge

Four commits predating a mid-session preference change still carry `Co-Authored-By: Claude`
and `Claude-Session:` trailers: `c0fb5e8`, `bc0ae0c`, `7641508`, `c427a47`.

The user's instruction was explicit: **no attribution footers.** Two ways to honor it:

- **Squash-merge #15** — master gets one clean message, no rewrite needed. Simplest.
- **Force-push a rewrite** — strip the trailers, then `git push --force-with-lease`. Safe:
  local and remote are identical, no other branch or file references those SHAs.

Also re-apply the setting in this container, since user settings do not travel:
`~/.claude/settings.json` → `{"attribution": {"commit": "", "pr": "", "sessionUrl": false}}`

### 5. Cut v1.3.0

Only after 1–3 look good.

```bash
# bump package.json to 1.3.0, move CHANGELOG [Unreleased] → [1.3.0] with today's date
git tag v1.3.0 && git push origin v1.3.0
```

Then verify what has never worked before:

- npm shows 1.3.0 (`npm view zlibrary-mcp version`) — it has been stuck on 1.0.0 since
  April 2025
- GHCR has `ghcr.io/loganrooks/zlibrary-mcp:1.3.0` and `:latest`
- The workflow's new tag↔`package.json` check passed rather than being skipped

Then close #11 and #14, referencing the release. Delete or publish the dangling v1.2.0
draft release at `untagged-2f888cb62d7894f40bf5`.

### 6. Smoke-test the new scheduled workflow

```
Actions → Upstream Contract Check → Run workflow
```

Confirm the reachability job passes and that the `report` job does **not** fire on a
successful run. Add repo secrets `ZLIBRARY_EMAIL` / `ZLIBRARY_PASSWORD` so the scheduled
run exercises the live suite, and create the `upstream-drift` label the workflow files
against.

### 7. Then: plan Phase 20 against the revised criteria

Plan Phase 20 per `claudedocs/architecture/phase-20-21-review-2026-07-24.md`. Read it
first — the phase was rewritten because ~60% of its original criteria were already
implemented. In particular task 20-00 (resolve the orphaned `scripts/run_rag_tests.py`)
must come before any new scoring code, or the repo ends up with two JSON quality reporters.

---

## Things to be careful about

- **Do not add `console.log` to `src/`.** stdout is the JSON-RPC channel.
  `__tests__/stdio-purity.test.js` will fail the build, which is the intent.
- **Do not lower a coverage threshold to make a change pass.** They were just raised from
  ~20 points below reality.
- **Do not add a `pip-audit --ignore-vuln` without a reason on the line.** Policy is in
  `SECURITY.md`: anything with a published fix gets a floor in
  `tool.uv.constraint-dependencies` instead.
- **`pymupdf` is pinned to 1.26.5 deliberately** — 1.26.6 lacks a Docker wheel and 1.26.7
  breaks footnote extraction. Dependabot is configured to leave it alone.
- **A quality/scoring run that reports "no regressions" over zero documents is a false
  green.** If LFS is not hydrated, the corpus silently skips. Check counts, not just exit
  codes.
