# Milestone Reflection Integration

Reference specification for integrating reflection into the milestone completion workflow. This documents how `/gsd:complete-milestone` can optionally trigger reflection on all milestone phases.

**Version:** 1.0.0
**Phase:** 04-reflection-engine

---

## Purpose

Document the optional reflection step that can be triggered as part of milestone completion. This integrates RFLC-04 (milestone integration) without modifying the upstream complete-milestone.md workflow.

Milestone reflection serves as a retrospective: analyze all signals accumulated during the milestone, detect patterns across the milestone's phases, and distill lessons before archiving.

---

## Integration Point

The complete-milestone workflow can optionally call `/gsd:reflect` after gathering stats and before creating the milestone entry. This is not automatic -- it's a documented option that users can choose.

**Workflow sequence:**

```
1. verify_readiness        -- Check milestone phases complete
2. gather_stats            -- Calculate stats from phases
3. [OPTIONAL] reflection   -- Analyze signals, detect patterns, create lessons
4. extract_accomplishments -- Extract achievements from summaries
5. create_milestone_entry  -- Write to MILESTONES.md
6. evolve_project_full_review
7. reorganize_roadmap
8. archive_milestone
... (remaining steps)
```

---

## Default Behavior

- Reflection is **OPTIONAL** during milestone completion
- User can skip reflection to proceed faster
- Reflection does **NOT** block milestone completion
- Skipping reflection does not lose data (signals remain in KB for future reflection)

---

## How to Trigger

During milestone completion, after the stats gathering step:

```
Optional: Run reflection on milestone phases?

This will:
- Analyze signals from all phases in this milestone (phases {X}-{Y})
- Detect patterns across the milestone
- Suggest lessons for the knowledge base

Estimated time: {quick: <1min | standard: 2-5min | comprehensive: 5-15min}

(yes / skip)
```

**If yes:** Run `/gsd:reflect` with milestone phase range scope.

**If skip:** Continue to extract_accomplishments step.

---

## What Gets Reflected

When reflection runs during milestone completion:

1. **Scope:** All phases included in the milestone (e.g., phases 1-4 for v1.0)

2. **Signals analyzed:** All signals in KB from the milestone's project, collected during milestone execution

3. **Phase-end comparisons:** PLAN.md vs SUMMARY.md for each plan in the milestone

4. **Pattern detection:** Cross-phase patterns using severity-weighted thresholds

5. **Lesson candidates:** Patterns meeting distillation criteria

---

## Output Inclusion

If reflection runs during milestone completion, results are incorporated into the milestone record:

### Milestone Archive Addition

Pattern summary is appended to the milestone archive (`.planning/milestones/v[X.Y]-ROADMAP.md`):

```markdown
## Reflection Summary

**Patterns detected:** 3
**Lessons created:** 2

### Top Patterns

1. {pattern-name} (4 occurrences, HIGH confidence)
   - Root cause: {brief}
   - Action: {brief}

2. {pattern-name} (2 occurrences, MEDIUM confidence)
   - Root cause: {brief}
   - Action: {brief}

### Lessons Added

- les-2026-02-05-{slug} (tooling/vitest)
  - Insight: {one-sentence lesson}

- les-2026-02-05-{slug} (external/claude-api)
  - Insight: {one-sentence lesson}

### Drift Assessment

Status: {STABLE|DRIFTING|CONCERNING}

{If not STABLE: recommendation}
```

### Milestone Entry Reference

The MILESTONES.md entry includes a reflection summary line:

```markdown
## v1.0 MVP (Shipped: 2026-02-05)

**Delivered:** [Description]

**Phases completed:** 1-4 (8 plans total)

**Key accomplishments:**
- [List]

**Reflection:** 3 patterns detected, 2 lessons added
See: milestones/v1.0-ROADMAP.md#reflection-summary
```

---

## Configuration

Can be configured in `.planning/config.json`:

```json
{
  "milestone_reflection": "optional"
}
```

**Values:**

| Value | Behavior |
|-------|----------|
| `optional` (default) | Prompt user during milestone completion |
| `required` | Must run reflection before milestone completes |
| `skip` | Never prompt for reflection |

**Example configurations:**

```json
// Fast iterations - skip reflection
{
  "mode": "yolo",
  "depth": "quick",
  "milestone_reflection": "skip"
}

// Thorough approach - require reflection
{
  "mode": "interactive",
  "depth": "comprehensive",
  "milestone_reflection": "required"
}
```

---

## Depth for Milestone Reflection

Milestone reflection uses a summary-focused approach by default:

| Aspect | Behavior |
|--------|----------|
| Phase coverage | All phases in milestone |
| Pattern reporting | Aggregate patterns only (not per-plan) |
| Lesson suggestions | Top 3 candidates (not all) |
| Drift check | Included only if depth=comprehensive |
| Detail level | Summary in archive, full via `/gsd:reflect` |

**For full detail:** Run `/gsd:reflect --phase {N}` for specific phases after milestone completion.

---

## Mode Interaction

Milestone reflection respects the project's autonomy mode:

**YOLO mode:**
- Reflection runs if `milestone_reflection: required` or user selects yes
- HIGH confidence lessons auto-approved
- MEDIUM/LOW confidence lessons written with project scope
- No interactive confirmation needed

**Interactive mode:**
- Prompt shown if `milestone_reflection: optional` (default)
- Each lesson candidate presented for confirmation
- User can edit lessons before writing

---

## Fork Constraint Compliance

This is a **NEW reference file** (additive). The complete-milestone.md workflow is **NOT modified**.

Integration is documentation-based: users who want milestone reflection follow this reference to understand:
1. When reflection can be triggered
2. How to configure it
3. What output to expect

The complete-milestone workflow remains unchanged. This reference documents an optional enhancement pattern.

---

## Implementation Notes

### For Workflow Authors

If adding reflection support to complete-milestone workflow in the future:

1. Add config check for `milestone_reflection` setting
2. After gather_stats step, check setting:
   - `skip`: Continue without prompting
   - `optional`: Prompt user
   - `required`: Run reflection automatically
3. If running reflection:
   - Calculate phase range from milestone scope
   - Run `/gsd:reflect` with phase range
   - Capture report output
   - Append to milestone archive
4. Continue with remaining steps

### For Users

To manually run milestone reflection:

```bash
# After completing milestone phases but before /gsd:complete-milestone
/gsd:reflect 1   # Phase 1
/gsd:reflect 2   # Phase 2
/gsd:reflect 3   # Phase 3
/gsd:reflect 4   # Phase 4

# Or batch reflection
/gsd:reflect --all  # Cross-project patterns
```

Then run `/gsd:complete-milestone` as usual. Lessons created will be in the KB.

---

## Example Milestone Reflection Flow

```
User: /gsd:complete-milestone

GSD: Milestone: v1.0 MVP
     Phases 1-4 complete (8 plans)
     Ready to mark as shipped?

User: yes

GSD: Gathering stats...
     - 8 plans, 24 tasks
     - 47 files modified
     - 2,400 LOC TypeScript

     Optional: Run reflection on milestone phases?
     This will analyze signals from phases 1-4.
     (yes / skip)

User: yes

GSD: Running reflection...

     Patterns detected: 3
     - vitest-async-cleanup (4 occurrences, HIGH)
     - env-var-missing (2 occurrences, MEDIUM)
     - type-assertion-needed (3 occurrences, MEDIUM)

     Lessons suggested: 2

     Lesson 1: vitest/async-cleanup (HIGH confidence)
     "Always call cleanup() in afterEach for async Vitest tests"
     Create? (yes / no / edit)

User: yes

GSD: Lesson created: les-2026-02-05-vitest-async-cleanup

     Lesson 2: environment/env-validation (MEDIUM confidence)
     "Validate required env vars at startup, not at use time"
     Create? (yes / no / edit)

User: yes

GSD: Lesson created: les-2026-02-05-env-validation

     Reflection complete: 3 patterns, 2 lessons

     Continuing milestone completion...
```

---

*Reference version: 1.0.0*
*Created: 2026-02-05*
*Phase: 04-reflection-engine, Plan: 02*
