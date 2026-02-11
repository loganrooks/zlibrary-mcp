# Signal Detection Reference

## 1. Overview

Defines detection rules, severity classification, polarity assignment, deduplication, and signal management for post-execution analysis of GSD workflow artifacts.

**Consumers:**
- `gsd-signal-collector` agent (automatic post-execution detection)
- `/gsd:signal` command (manual signal creation)
- `/gsd:collect-signals` command (batch signal collection)

**Input artifacts:**
- PLAN.md -- planned tasks, files, verification criteria
- SUMMARY.md -- execution results, deviations, issues
- VERIFICATION.md -- gap analysis against must_haves
- `.planning/config.json` -- model_profile and workflow settings

**Output:** Signal entries written to `./.claude/gsd-knowledge/signals/{project}/` using the Phase 1 signal template.

## 2. Deviation Detection (SGNL-01)

Compare PLAN.md against SUMMARY.md for each completed plan.

**Detection points:**

| PLAN.md Source | SUMMARY.md Source | What to Check |
|----------------|-------------------|---------------|
| `<tasks>` list (count of `<task>` elements) | `## Task Commits` table (row count) | Task count mismatch (planned vs completed) |
| `files_modified:` frontmatter array | `## Files Created/Modified` section | Unexpected files touched or expected files missing |
| `<verification>` criteria | `## Deviations from Plan` section | Auto-fixes indicate plan gaps or underspecification |
| `must_haves:` truths | VERIFICATION.md `gaps_found` results | Verification gaps -- goals not fully met |

**Positive deviation detection:**
- SUMMARY.md mentions unexpected improvements or cleaner-than-planned outcomes
- Execution completed ahead of schedule (duration well below expected)
- Additional helpful artifacts created beyond plan scope
- These generate positive-polarity signals (see Section 7)

**Detection logic:**
1. Count `<task` elements in PLAN.md, count rows in Task Commits table in SUMMARY.md
2. Parse `files_modified` from plan frontmatter, compare against files listed in SUMMARY.md
3. Check "Deviations from Plan" section -- if it contains "Auto-fixed Issues" subsections, each is a deviation signal candidate
4. If VERIFICATION.md exists, check for `gaps_found: true` or partial passes

## 3. Config Mismatch Detection (SGNL-02)

Compare `.planning/config.json` `model_profile` against executor spawn information.

**Model profile expectations:**

| Profile | Expected Executor Model Class |
|---------|-------------------------------|
| `quality` | opus-class (claude-opus-*) |
| `balanced` | sonnet-class (claude-sonnet-*) |

**Detection rules:**
- Only flag mismatches where the outcome was likely affected
- If `quality` profile but sonnet-class executor was used: flag as critical
- If `balanced` profile and sonnet-class was used: expected, no signal
- Harmless fallbacks (e.g., model temporarily unavailable, fallback produced correct results) should not generate signals

**Where to find executor model info:** SUMMARY.md may reference the model used. If not explicitly stated, check git log commit metadata or skip this detection for the plan.

## 4. Struggle Detection (SGNL-03)

Scan SUMMARY.md for indicators of execution difficulty.

**Struggle indicators:**

| Indicator | Source Section | Threshold |
|-----------|---------------|-----------|
| Non-trivial issues encountered | `## Issues Encountered` | Content beyond "None" or "No issues" |
| Multiple auto-fixes | `## Deviations from Plan` | 3+ auto-fix entries in a single plan |
| Checkpoint returns on autonomous plans | `## Deviations from Plan` | Any checkpoint return when plan has `autonomous: true` |
| Disproportionate duration | `## Performance` section | Duration significantly exceeding plan complexity (use judgment) |

**What qualifies as "non-trivial" in Issues Encountered:**
- Error messages, stack traces, or debugging descriptions
- Workarounds applied instead of clean solutions
- External blockers (API outages, auth failures, dependency issues)

**What does NOT qualify:**
- "None" or "No issues encountered"
- Minor notes about expected behavior
- Informational observations without friction

## 5. Frustration Detection (SGNL-06)

Pattern matching for implicit frustration in conversation context. Used by `/gsd:signal` command when scanning recent messages.

**Frustration patterns:**
- "still not working"
- "this is broken"
- "tried everything"
- "keeps failing"
- "doesn't work"
- "same error"
- "frustrated"
- "why won't"
- "makes no sense"
- "wasting time"

**Trigger threshold:** 2+ patterns detected in recent messages suggests a frustration signal.

**Important:** These patterns are indicators, not definitive triggers. The agent uses judgment -- a user saying "this doesn't work yet" in a calm technical context is different from repeated frustrated messages. The patterns inform a suggestion to create a frustration signal, not an automatic signal creation.

**Scope:** Frustration detection applies to `/gsd:signal` manual command context only. Post-execution automatic detection (via `gsd-signal-collector`) does not have access to conversation context and should not attempt frustration detection.

## 6. Severity Auto-Assignment (SGNL-04)

Automatic severity classification based on detection source and impact.

| Condition | Severity |
|-----------|----------|
| Verification failed (`gaps_found`) | critical |
| Config mismatch (wrong model class spawned) | critical |
| 3+ auto-fixes in a single plan | notable |
| Issues encountered (non-trivial) | notable |
| Positive deviations (unexpected improvements) | notable |
| Task order changed with no impact | trace |
| Minor file differences (extra helper files created) | trace |
| Single auto-fix | trace |

**Persistence rules:**
- **critical** -- always persisted to KB
- **notable** -- always persisted to KB
- **trace** -- logged in collection report output only, NOT written to KB

**Manual override:** The `/gsd:signal` command allows users to set severity explicitly, overriding auto-assignment. Manual signals at any severity level (including trace equivalent) are always persisted since the user explicitly chose to record them.

## 7. Polarity Assignment

Every signal receives a polarity indicating whether the observation is positive, negative, or neutral.

| Detection | Polarity |
|-----------|----------|
| Verification gaps | negative |
| Debugging struggles | negative |
| Config mismatches | negative |
| Frustration indicators | negative |
| Unexpected improvements | positive |
| Ahead-of-schedule completion | positive |
| Cleaner-than-planned implementation | positive |
| Task reordering with no impact | neutral |
| Minor file differences | neutral |

Polarity enables Phase 4 (Reflection Engine) to distinguish problems from happy accidents when analyzing signal patterns.

## 8. Signal Schema Extensions

These optional fields extend the Phase 1 signal schema defined in `knowledge-store.md`. Existing required fields (`severity`, `signal_type`, `phase`, `plan`) remain unchanged.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `polarity` | enum: positive, negative, neutral | negative | Whether the signal represents a positive, negative, or neutral observation |
| `source` | enum: auto, manual | auto | Whether the signal was detected automatically or created manually via `/gsd:signal` |
| `occurrence_count` | integer | 1 | How many times this signal pattern has been observed (starts at 1) |
| `related_signals` | array of signal IDs | [] | IDs of existing signals that match this signal's pattern (for dedup cross-references) |

**Compatibility:** These fields are added to signal frontmatter alongside the Phase 1 base schema and signal extension fields. Agents that do not recognize these fields can safely ignore them. The Phase 1 index rebuild script processes all frontmatter fields without filtering.

## 9. Deduplication Rules (SGNL-05)

Before writing a new signal, check for related existing signals to avoid redundant entries.

**Deduplication process:**

1. Read existing signals for the project from `./.claude/gsd-knowledge/index.md`
2. For each existing active signal, check match criteria:
   - Same `signal_type` (deviation, struggle, config-mismatch, custom)
   - Same `project`
   - Overlapping tags: 2+ shared tags between new and existing signal
3. If match found:
   - Add all matched signal IDs to the `related_signals` array on the NEW signal
   - Set `occurrence_count` to the highest `occurrence_count` among matched signals + 1
4. Do NOT update existing signals (immutability constraint from Phase 1)
5. Write the new signal with `related_signals` populated

**Why not update existing signals:** Signals are immutable after creation (Phase 1 lifecycle rules). Each signal captures a moment in time. Pattern detection across related signals is the responsibility of Phase 4 (Reflection Engine), which reads `related_signals` to identify recurring issues.

**Cross-phase dedup:** Deduplication checks all active signals for the project, not just the current phase. A recurring auth issue in Phase 2 and Phase 3 should be cross-referenced.

## 10. Per-Phase Signal Cap (SGNL-09)

Prevents signal noise from overwhelming the knowledge base.

**Rules:**
- Maximum **10** persistent signals per phase per project
- Trace signals are never persisted and do not count toward the cap
- Only `critical` and `notable` signals count toward the cap

**Cap enforcement:**
1. Before writing a new signal, count existing active signals for this phase and project
2. If count < 10: write normally
3. If count >= 10: compare new signal severity against the lowest-severity existing signal
   - If new signal severity >= lowest existing severity: archive the lowest-severity signal (set `status: archived` in its frontmatter), then write the new signal
   - If new signal severity < lowest existing severity: do not persist (log in report only)

**Severity ordering for cap comparison:** critical > notable

**Archival for cap replacement:**
- Set `status: archived` in the replaced signal's frontmatter
- This is the ONE exception to signal immutability -- archival status changes are permitted for cap management
- Archived signals remain in their original file location
- Archived signals are excluded from the index on next rebuild

## 11. Detection Timing

**Automatic detection (post-execution):**
- Runs after all plans in a phase complete
- Invoked via `/gsd:collect-signals {phase-number}` command
- Reads stable output artifacts only: PLAN.md, SUMMARY.md, VERIFICATION.md, config.json
- Does not run mid-execution (wrapper pattern constraint -- cannot modify executor agents)

**Manual detection (anytime):**
- Via `/gsd:signal` command during any conversation
- User can create signals at any time based on their observations
- Frustration detection (SGNL-06) is available in manual mode via conversation context scanning

**No mid-execution detection:**
- Executor agents run in fresh contexts with no signal collection hooks
- Modifying executor agent instructions would violate the fork constraint (additive-only)
- All automatic detection is retrospective, reading artifacts after execution completes

---

*Reference version: 1.0.0*
*Created: 2026-02-03*
*Phase: 02-signal-collector*
