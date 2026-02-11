# Reflection Patterns Reference

Reference specification for pattern detection, lesson distillation, phase-end reflection, and semantic drift detection in the GSD self-improvement loop.

**Version:** 1.0.0
**Phase:** 04-reflection-engine

---

## 1. Overview

The Reflection Engine is the closing loop of the GSD self-improvement cycle. It transforms accumulated signals into actionable knowledge by:

1. **Detecting patterns** in recurring signals using severity-weighted thresholds
2. **Comparing execution** against plans at phase boundaries
3. **Distilling lessons** from qualifying patterns
4. **Tracking semantic drift** through metric trend analysis
5. **Surfacing improvement suggestions** based on recurring friction points

**Core principle:** The system never makes the same mistake twice. Signals capture what went wrong, patterns identify recurring issues, and lessons prevent future occurrences.

**When reflection runs:**
- On explicit `/gsd:reflect` command
- At phase-end (optional, configurable)
- During milestone completion (optional integration)

**What reflection does NOT do:**
- Modify execution behavior (retrospective only)
- Run continuously (event-driven, not background)
- Require external ML models (heuristics on structured data)

---

## 2. Pattern Detection Rules

### 2.1 Severity-Weighted Thresholds

Pattern detection uses severity-weighted occurrence thresholds rather than a single number. This catches critical issues early while filtering noise from minor friction.

| Signal Severity | Threshold | Rationale |
|-----------------|-----------|-----------|
| `critical` | 2 occurrences | Cannot risk missing dangerous patterns |
| `high` | 2 occurrences | High-impact issues warrant early attention |
| `medium` | 4 occurrences | Moderate issues need recurrence confirmation |
| `low` | 5+ occurrences | Must be truly recurring, not noise |

**Threshold application:**
```bash
# Pseudocode for severity-weighted threshold check
case "$max_severity" in
  critical|high)
    [ "$count" -ge 2 ] && emit_pattern ;;
  medium)
    [ "$count" -ge 4 ] && emit_pattern ;;
  low)
    [ "$count" -ge 5 ] && emit_pattern ;;
esac
```

### 2.2 Signal Clustering Criteria

Signals cluster into patterns based on shared characteristics. Criteria in priority order:

| Priority | Criteria | Match Strength | Use Case |
|----------|----------|----------------|----------|
| 1 | Same `signal_type` + 2+ overlapping tags | Strongest | Core pattern identification |
| 2 | Same project + same `signal_type` + similar slug | Strong | Project-specific recurrence |
| 3 | Cross-project: same tags + same `signal_type` | Moderate | Candidate global pattern |

**Clustering algorithm:**
1. Group signals by `signal_type` (deviation, struggle, config-mismatch)
2. Within each group, cluster by tag overlap (2+ shared tags)
3. For each cluster, take the highest severity among members
4. Apply severity-weighted threshold to cluster count

**Example clustering:**
```bash
# Extract pattern keys from index
# Pattern key = signal_type + first two tags
extract_patterns() {
  grep "^| sig-" "$KB_DIR/index.md" | while read -r row; do
    signal_type=$(get_signal_type_from_file "$row")
    tags=$(echo "$row" | cut -d'|' -f5 | tr -d ' ')
    primary_tags=$(echo "$tags" | cut -d',' -f1-2)
    echo "${signal_type}:${primary_tags}"
  done
}
```

### 2.3 Pattern Output Format

When a pattern qualifies (meets threshold), emit in this structure:

```markdown
## Pattern: {pattern-name}

**Signal type:** {deviation|struggle|config-mismatch}
**Occurrences:** {count}
**Severity:** {highest severity among grouped signals}
**Confidence:** {HIGH|MEDIUM|LOW} ({count} occurrences)

**Signals in pattern:**

| ID | Project | Date | Tags |
|----|---------|------|------|
| sig-X | project-a | 2026-02-01 | tag1, tag2 |
| sig-Y | project-b | 2026-02-03 | tag1, tag3 |

**Root cause hypothesis:** {Agent's assessment of why this pattern recurs}

**Recommended action:** {What to do about it}
```

### 2.4 Time and Persistence

**Critical rule:** No time-based rolling windows.

Time-based windows lose infrequent but persistent issues (e.g., library bug recurring across versions over months). Instead:

- **Recency affects priority ranking**, not exclusion
- Old signals with same tags/type still cluster with new signals
- Signals remain in pattern detection pool regardless of age
- Archival (via `status: archived`) is the only exclusion mechanism

---

## 3. Phase-End Reflection (RFLC-01)

Compare PLAN.md against SUMMARY.md at phase completion to identify systemic deviations.

### 3.1 Comparison Points

| PLAN.md Source | SUMMARY.md Source | Deviation Type |
|----------------|-------------------|----------------|
| Task count (`<task>` elements) | Task Commits table rows | Task mismatch |
| `files_modified` frontmatter | Files Created/Modified section | File scope creep/shrink |
| Estimated duration (if present) | Actual duration | Time estimation error |
| `must_haves.truths` | VERIFICATION.md results | Goal achievement failure |
| `autonomous: true` | Checkpoint returns documented | Autonomy failure |
| Empty "Issues Encountered" | Non-trivial issues documented | Unexpected friction |

### 3.2 Deviation Analysis

For each comparison point, calculate:
- **Delta:** Absolute difference (e.g., +2 tasks, -1 file)
- **Direction:** Expansion (+) or contraction (-)
- **Impact:** Assessment of whether deviation was beneficial, neutral, or problematic

### 3.3 must_haves vs VERIFICATION.md Gaps

Cross-reference `must_haves` from PLAN.md frontmatter against VERIFICATION.md:

```yaml
# From PLAN.md
must_haves:
  truths:
    - "Pattern detection rules exist for severity-weighted thresholds"
    - "Lesson distillation criteria and flow are documented"
  artifacts:
    - path: "./.claude/get-shit-done/references/reflection-patterns.md"
      provides: "Pattern detection rules"
```

Compare against VERIFICATION.md success criteria results. Any failed criterion is a gap.

### 3.4 Reflection Output Format

```markdown
## Phase {N} Reflection

**Plan:** {phase}-{plan}-PLAN.md
**Summary:** {phase}-{plan}-SUMMARY.md
**Overall alignment:** {HIGH|MEDIUM|LOW}

### Deviations Found

| Category | Planned | Actual | Delta | Impact |
|----------|---------|--------|-------|--------|
| Task count | 5 | 6 | +1 | Auto-fix added |
| File scope | 4 files | 7 files | +3 | Supporting files needed |
| Duration | ~30min | 48min | +60% | Blocking issue encountered |

### Auto-Fixes Applied

| # | Rule | Description | Files |
|---|------|-------------|-------|
| 1 | Rule 1 - Bug | Fixed null pointer in auth | src/auth.ts |
| 2 | Rule 2 - Missing Critical | Added input validation | src/api/users.ts |

### Issues Encountered

[Summary of non-trivial issues from SUMMARY.md]

### Patterns Detected This Phase

[Patterns found from signals collected during this phase]

### Lessons Suggested

[Draft lessons based on deviations and patterns]
```

---

## 4. Lesson Distillation (RFLC-02)

Convert qualifying signal patterns into actionable lesson entries.

### 4.1 Distillation Criteria

A pattern qualifies for lesson distillation when ALL of:
1. **Meets threshold:** Pattern occurrence count meets severity-weighted threshold
2. **Consistent root cause:** Signals in pattern share similar root cause hypothesis
3. **Actionable:** A concrete recommendation can be derived

### 4.2 Lesson Creation Flow

```
1. Identify qualifying pattern
       |
       v
2. Draft lesson content
   - category: From taxonomy (tooling, architecture, testing, workflow, external, environment)
   - insight: One-sentence actionable lesson
   - evidence: List of signal IDs supporting this lesson
   - confidence: Based on occurrence count and consistency
   - durability: workaround, convention, or principle
       |
       v
3. Determine scope (project vs global)
   - Apply heuristics (see 4.3)
       |
       v
4. Write lesson file
   - Use kb-templates/lesson.md
   - Write to ./.claude/gsd-knowledge/lessons/{category}/
       |
       v
5. Rebuild index
   - Run kb-rebuild-index.sh
```

### 4.3 Scope Determination Heuristics

**Global scope indicators:**
- References named library or framework (e.g., "Vitest", "Next.js", "Prisma")
- Root cause is external (library bug, documentation gap, tool limitation)
- Would affect any project using similar technology stack
- Signal has `likely_scope: global` hint

**Project scope indicators:**
- References specific file paths (e.g., `src/lib/auth.ts`)
- References project structure or local configuration
- Root cause is internal (our code, our design choices)
- Pattern limited to one project

**Default rule:** When uncertain, default to project-scoped. Safer to keep lessons project-local than pollute global namespace with noise.

**Autonomy tie-in:**
- **YOLO mode:** High-confidence global lessons auto-promote
- **Interactive mode:** Suggest global promotion, user confirms

### 4.4 Lesson Content Structure

From kb-templates/lesson.md:

```yaml
---
id: les-{YYYY-MM-DD}-{slug}
type: lesson
project: {project-name|_global}
tags: [{tag1}, {tag2}]
created: {timestamp}
updated: {timestamp}
durability: {workaround|convention|principle}
status: active
category: {category}
evidence_count: {number}
evidence: [{signal-id-1}, {signal-id-2}]
confidence: {high|medium|low}
---

## Lesson

{One-sentence actionable insight}

## When This Applies

{Conditions, contexts, or triggers}

## Recommendation

{Specific guidance for agents}

## Evidence

{References to supporting signals with descriptions}
```

---

## 5. Cross-Project Detection (SGNL-07)

Scan signals across all projects to identify patterns that transcend individual projects.

### 5.1 Detection Approach

1. **Read index.md** - Already contains all projects' signals
2. **Group by tag + signal_type** - Ignore project field during grouping
3. **Apply severity-weighted thresholds** - Same rules as single-project
4. **Check `likely_scope: global` hints** - Signals flagged at creation time
5. **Validate cross-project span** - Pattern must span 2+ projects

### 5.2 Global Lesson Criteria

A pattern qualifies as global lesson when:
- Pattern spans **2+ distinct projects**
- Signals share **same root cause hypothesis**
- Root cause is **external** (library, framework, tool, environment)

### 5.3 Cross-Project Query

```bash
# Query index for cross-project patterns
# Group by signal_type + tags, ignoring project column

KB_INDEX="$HOME/.claude/gsd-knowledge/index.md"

# Extract all signal rows
grep "^| sig-" "$KB_INDEX" | while read row; do
  project=$(echo "$row" | cut -d'|' -f3 | tr -d ' ')
  tags=$(echo "$row" | cut -d'|' -f5 | tr -d ' ')
  # Track project count per tag combination
  echo "$tags:$project"
done | sort | uniq | cut -d':' -f1 | sort | uniq -c
# Patterns appearing with 2+ unique projects are candidates
```

### 5.4 Cross-Project Access Control

- **Default:** Cross-project detection enabled (KB is user-level)
- **User setting:** Opt-in or opt-out in `/gsd:settings`
- **Per-project override:** `.planning/config.json` can disable cross-project sharing
- **Privacy:** Lessons from private projects stay project-scoped

---

## 6. Semantic Drift Detection (RFLC-06)

Track whether agent output quality degrades over time using heuristic indicators.

### 6.1 Drift Indicators

No ML required. Track these metrics across phases:

| Metric | Source | What It Measures |
|--------|--------|------------------|
| Verification gap rate | VERIFICATION.md `gaps_found` | Are more plans failing verification? |
| Auto-fix frequency | SUMMARY.md "Deviations" | Are plans needing more corrections? |
| Signal severity rate | Signal index | Is critical/high proportion increasing? |
| Deviation-to-plan ratio | PLAN vs SUMMARY comparison | Are executions deviating more from plans? |

### 6.2 Detection Algorithm

```bash
# Compare recent N phases against baseline M phases
RECENT_PHASES=5
BASELINE_PHASES=10

# Calculate metric rates for recent period
recent_gap_rate=$(calculate_gap_rate last $RECENT_PHASES)
recent_autofix_rate=$(calculate_autofix_rate last $RECENT_PHASES)
recent_severity_rate=$(calculate_severity_rate last $RECENT_PHASES)

# Calculate baseline rates
baseline_gap_rate=$(calculate_gap_rate previous $BASELINE_PHASES)
baseline_autofix_rate=$(calculate_autofix_rate previous $BASELINE_PHASES)
baseline_severity_rate=$(calculate_severity_rate previous $BASELINE_PHASES)

# Flag if recent is 50%+ worse than baseline
for metric in gap_rate autofix_rate severity_rate; do
  if recent > baseline * 1.5; then
    emit_drift_warning "$metric increased by 50%+"
  fi
done
```

### 6.3 Detection Thresholds

| Condition | Assessment |
|-----------|------------|
| All metrics within 20% of baseline | STABLE |
| Any metric 20-50% worse than baseline | DRIFTING |
| Any metric 50%+ worse than baseline | CONCERNING |

### 6.4 Drift Report Format

```markdown
## Semantic Drift Check

**Period:** Last {N} phases
**Baseline:** Previous {M} phases

| Metric | Baseline | Recent | Change | Status |
|--------|----------|--------|--------|--------|
| Verification gaps | 12% | 18% | +50% | CONCERNING |
| Auto-fixes/plan | 1.2 | 1.8 | +50% | CONCERNING |
| Critical signals | 0.4/phase | 0.5/phase | +25% | DRIFTING |
| Deviation ratio | 0.15 | 0.18 | +20% | STABLE |

**Overall assessment:** {STABLE|DRIFTING|CONCERNING}

**Recommendation:**
{If CONCERNING: Review recent plans for pattern, consider pausing for investigation}
{If DRIFTING: Monitor in next phase, flag if continues}
{If STABLE: No action needed}
```

---

## 7. Workflow Improvement Suggestions (RFLC-05)

Generate actionable improvement suggestions based on recurring signal patterns.

### 7.1 Suggestion Triggers

Generate suggestions when:
- Pattern reaches HIGH confidence (6+ occurrences)
- Pattern spans multiple phases or plans
- Root cause analysis points to workflow issue

### 7.2 Suggestion Template

```markdown
## Workflow Improvement Suggestion

**Pattern observed:** {pattern-name}
**Occurrences:** {count} across {N} phases
**Impact:** {Description of workflow friction this causes}

**Root cause:** {Why this keeps happening}

**Recommended workflow change:**

1. {Specific modification to workflow/process}
2. {Expected benefit}
3. {How to implement}

**Evidence:**
- {signal-id-1}: {brief description}
- {signal-id-2}: {brief description}
```

### 7.3 Suggestion Categories

| Category | Trigger Pattern | Example Suggestion |
|----------|-----------------|-------------------|
| Planning | Consistent task count mismatches | "Break large tasks into smaller atomic units" |
| Verification | Repeated verification gaps | "Add verification criteria to plan frontmatter" |
| Configuration | Config mismatch patterns | "Document model requirements in CONTEXT.md" |
| Testing | Test-related struggles | "Add test infrastructure check to plan start" |

---

## 8. Category Taxonomy

Predefined top-level categories with emergent subcategories.

### 8.1 Top-Level Categories

| Category | Scope | Examples |
|----------|-------|----------|
| `tooling` | Build tools, test runners, linters | Vitest, ESLint, Webpack |
| `architecture` | Code structure, patterns, design | Barrel exports, service layers |
| `testing` | Test strategies, fixtures, mocking | Snapshot testing, mock setup |
| `workflow` | GSD workflow, CI/CD, automation | Plan structure, verification |
| `external` | Third-party services, APIs, libraries | Claude API, npm, OAuth providers |
| `environment` | OS, runtime, configuration | Node versions, env vars |

### 8.2 Subcategory Emergence

Subcategories emerge organically as lessons accumulate:
- `tooling/vitest` - Vitest-specific lessons
- `external/claude-api` - Claude API quirks and workarounds
- `workflow/planning` - GSD planning process lessons

**Naming convention:** `{top-level}/{specific}` using kebab-case

### 8.3 Category Assignment

When creating a lesson:
1. Identify primary concern from pattern context
2. Match to top-level category
3. If pattern is tool/library-specific, add subcategory
4. If no existing subcategory fits and pattern is specific, create new one

---

## 9. Confidence Expression

Use categorical confidence with occurrence count evidence.

### 9.1 Confidence Levels

| Level | Criteria | Expression |
|-------|----------|------------|
| **HIGH** | 6+ occurrences, empirical evidence, consistent root cause | "HIGH (7 occurrences across 3 projects)" |
| **MEDIUM** | 3-5 occurrences, inference from patterns | "MEDIUM (4 occurrences, same root cause)" |
| **LOW** | 2-3 occurrences, educated guess | "LOW (2 occurrences, similar symptoms)" |

### 9.2 Actionability Levels

Based on confidence, lessons have different actionability:

| Confidence | Actionability | Lesson Framing |
|------------|--------------|----------------|
| HIGH | Directive | "Always do X when Y occurs" |
| MEDIUM | Recommendation | "Consider X when encountering Y" |
| LOW | Observation | "Pattern observed: X tends to cause Y" |

### 9.3 Confidence in Output

Always include occurrence count when stating confidence:
- "Confidence: HIGH (12 occurrences, 4 projects)"
- "Confidence: MEDIUM (4 occurrences, consistent root cause)"
- "Confidence: LOW (2 occurrences, same tags)"

---

## 10. Anti-Patterns to Avoid

Common mistakes in reflection implementation.

### 10.1 Time-Based Rolling Windows

**Anti-pattern:** "Delete signals older than 30 days"
**Problem:** Loses infrequent but persistent issues (e.g., library bug recurring across versions)
**Correct approach:** Use recency for priority ranking, not exclusion. Archive via status field only.

### 10.2 Automatic Global Promotion in Interactive Mode

**Anti-pattern:** Auto-promoting lessons to global scope without user confirmation
**Problem:** Pollutes global namespace with project-specific noise
**Correct approach:** In interactive mode, suggest promotion and wait for user confirmation. Auto-promote only in YOLO mode for HIGH confidence lessons.

### 10.3 Pattern Detection on Every Signal Write

**Anti-pattern:** Running full pattern detection when each new signal is written
**Problem:** Performance overhead, unnecessary computation
**Correct approach:** Pattern detection runs on reflection trigger (explicit command, phase-end, milestone). Not continuous.

### 10.4 Circular Evidence in Lessons

**Anti-pattern:** Lesson references signals created after the lesson existed
**Problem:** Circular reasoning - lesson can't be evidence for itself
**Correct approach:** Evidence links point to signal IDs created BEFORE the lesson's `created` timestamp. New signals after lesson creation are updates, not circular.

### 10.5 ML-Based Classification

**Anti-pattern:** Using embedding models or semantic similarity for pattern detection
**Problem:** Adds dependencies, opacity, unpredictability
**Correct approach:** Signals have explicit tags and types. String matching on structured frontmatter is sufficient and debuggable.

### 10.6 Modifying Existing Signals

**Anti-pattern:** Editing signal files to update or correct information
**Problem:** Signals are immutable snapshots of moments in time
**Correct approach:** Only status field changes are allowed (for archival). Create new signal for new information.

---

## 11. Integration Points

### 11.1 Knowledge Store Integration

- Read from: `./.claude/gsd-knowledge/index.md` (signal listing)
- Read from: `./.claude/gsd-knowledge/signals/{project}/` (signal details)
- Write to: `./.claude/gsd-knowledge/lessons/{category}/` (new lessons)
- Execute: `./.claude/agents/kb-rebuild-index.sh` (after writes)

### 11.2 Phase Artifact Integration

- Read from: `.planning/phases/{phase}/` directory
- Files: `*-PLAN.md`, `*-SUMMARY.md`, `*-VERIFICATION.md`
- Extract: Task counts, file lists, deviations, issues

### 11.3 Configuration Integration

- Read from: `.planning/config.json`
- Fields: `mode` (yolo/interactive), `depth`, cross-project settings

---

*Reference version: 1.0.0*
*Created: 2026-02-05*
*Phase: 04-reflection-engine, Plan: 01*
