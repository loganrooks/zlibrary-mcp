# Connector repair round 1

2026-10-19. Authority: lane `FIX-CONNECTOR-r1.md` and the full lead
`ZLIB-EVAL-CONNECTOR-DISPOSITION-r1.md`; all four findings accepted there.
This is an offline implementation handoff, not a model or review verdict.

## Scope and plan

Only this directory's evaluator source, tests and documentation are owned.
Preserve all other work, partial receipts and the existing `.venv` symlink.
No Git mutation, external models/reviewers, live providers or production/fake edits.

- Implemented and focused-verified: EVAL-C1-03 — test same-task per-title provenance for A/B,
  retaining interleaved searches/downloads; require distinct matching searches.
- Implemented and focused-verified: EVAL-C1-04 — synthetic local children test the real capture path;
  await drained close, bound timeout/signal/spawn-error/inherited-pipe failures,
  and preserve raw output before parsing or failing.
- Implemented and focused-verified: EVAL-C1-01 — independently compile pinned clean inputs into scratch,
  compare exact runtime output manifests/bytes with selected dist, race-check
  inputs/compiler/runtime identity, require schema-3 build proof at admission.
- Implemented and focused-verified: EVAL-C1-02 — default to source-equivalent baseline checkout HEAD,
  never infer baseline from B; resolve one exact A identity in runner/matrix/docs.
- Done: final focused tests 145/145, default and explicit A self-tests 12/12 each,
  15 generated dry commands with a common A identity, build, full Jest 571/571,
  rehearsal35 stable, and format/diff checks. The lane's
  `READY-CONNECTOR-r1.txt` indexes exact commands, hashes, attempts and limits.

## Settled implementation boundaries

Compile using the existing installed TypeScript compiler and pinned config, not
package scripts or model-supplied shell commands. Scratch output never replaces
selected source/dist. Runtime JavaScript/data outputs are compared byte-for-byte;
declarations/maps/build metadata are not executed and are excluded from that
comparison, while the full selected dist tree digest is still recorded.
Legacy receipts are diagnostic only. The lead owns independent counterexamples,
B preflight, Git integration, topic propagation and connector round 2.

Attempt evidence will be retained under unique `/private/tmp/evalfx-connector-r1-*`
paths and indexed with SHA256 in `READY-CONNECTOR-r1.txt` in the lane folder.

The first capture red run reached the old unbounded wait, hit Jest's test deadline
and was interrupted via its owned execution session. Test cleanup was strengthened;
green synthetic children now terminate and retained raw attempts are printed by Jest.
One additional input-control attempt failed on missing scratch ignore rules rather
than the intended compiler failure; the mirror now copies ignore rules and proves
clean pinned input bytes before each mutation. Both attempt logs are retained.

The final actual-A receipts use schema 3, prove 11 baseline runtime files against
fresh compilation, and retain all 44 selected dist files in the full tree hash.
This does not assert B's file count or its runtime result. No production/fake
source was changed, and the lead-owned stopped model receipt was not modified.
The lead still owns independent counterexamples, clean B preflight, Git and the
connector round-2 review; no additional reviewer or model was called here.
