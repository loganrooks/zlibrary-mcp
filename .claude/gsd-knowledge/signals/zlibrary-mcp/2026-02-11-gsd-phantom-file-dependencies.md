---
id: sig-2026-02-11-gsd-phantom-file-dependencies
type: signal
project: zlibrary-mcp
tags: [gsd-framework, phantom-dependencies, missing-files, workflow-integrity, dependency-analysis]
created: 2026-02-11T00:00:00Z
updated: 2026-02-11T00:00:00Z
durability: convention
status: active
severity: critical
signal_type: config-mismatch
phase: 13
plan: 02
polarity: negative
source: manual
occurrence_count: 1
related_signals: [sig-2026-02-11-executor-missed-fixture-dependency]
---

## What Happened

GSD framework has 3 phantom file dependencies referenced across 10+ workflows but never created:

1. **`knowledge-store.md`** (KB conventions spec) — referenced by signal.md workflow, collect-signals.md, reflect.md, run-spike.md, health-check.md, signal-detection.md (6 references)
2. **`kb-templates/signal.md`** (signal entry template) — referenced by signal.md workflow and gsd/signal.md command (2 references)
3. **`kb-rebuild-index.sh`** (index rebuild script) — referenced by signal.md workflow, collect-signals.md, reflect.md, health-check.md, spike-execution.md, reflection-patterns.md (7 references)

The signal workflow's own `<required_reading>` section instructs agents to "Read kb-templates/signal.md for the signal entry template" and "Read the knowledge-store.md agent spec for KB conventions." These files do not exist. Agents that follow instructions encounter missing files and must fall back to inferring schema from inline examples scattered across workflow specs.

Similarly, every workflow that writes to the knowledge base calls `bash ./.claude/agents/kb-rebuild-index.sh` — a script that was never created. This means the KB index is never automatically maintained.

## Context

Discovered during Phase 13 execution while running the `/gsd:signal` workflow for the first time on this project. The agent attempted to read `kb-templates/signal.md` per workflow instructions, found it missing, searched for alternatives, and ultimately had to construct the signal entry from the schema description embedded in the workflow spec. The `kb-rebuild-index.sh` failure was also discovered during the same signal creation.

This is part of a broader pattern observed in the same session: the Phase 13-02 executor removed a shared fixture (`zlib_client`) without checking downstream dependents (see related signal). Both issues stem from the same root cause — changes or decisions made without tracing dependency relationships.

## Potential Cause

**Root cause: KB infrastructure was designed in workflow specs but never implemented.**

The GSD knowledge base system (knowledge-store.md, templates, rebuild script) appears to have been specified as part of a "Phase 1" or "Phase 2" of the GSD Reflect system but the actual files were never created — or were created in a different location/format without updating all referencing workflows.

**Contributing factors:**
- No validation step checks that `@`-referenced files in workflow specs actually exist
- The `<required_reading>` and `<execution_context>` sections in workflow specs are documentation, not enforced contracts — agents silently degrade when referenced files are missing
- Multiple workflows independently reference the same phantom files, suggesting a coordinated design that was partially abandoned

**Actionable convention:** When designing cross-cutting infrastructure (templates, scripts, specs) referenced by multiple workflows, create the files first or gate the referencing workflows behind existence checks. A GSD health check should validate that all `@`-referenced files in workflow specs exist on disk.
