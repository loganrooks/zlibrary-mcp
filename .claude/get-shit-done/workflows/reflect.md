<purpose>

Analyze accumulated signals from the knowledge base, detect recurring patterns using severity-weighted thresholds, distill qualifying patterns into actionable lessons, and optionally run phase-end or semantic drift analysis. This workflow closes the self-improvement loop: signals become patterns become lessons that prevent future mistakes.

</purpose>

<core_principle>

Reflection is retrospective analysis. It reads signals, phase artifacts, and KB state without modifying execution behavior. The workflow validates prerequisites, delegates analysis to the reflector agent, and presents results with appropriate confirmation based on autonomy mode.

</core_principle>

<required_reading>

Read these references for pattern detection rules and distillation criteria:
- get-shit-done/references/reflection-patterns.md
- .claude/agents/knowledge-store.md
- .claude/agents/kb-templates/lesson.md

Read STATE.md before any operation to load project context.
Read config.json for mode and depth settings.

</required_reading>

<trigger_modes>

1. **Explicit command:** `/gsd:reflect` or `/gsd:reflect {phase}`
2. **Phase-end:** `/gsd:reflect --phase {N}` for specific phase reflection
3. **Cross-project:** `/gsd:reflect --all` for cross-project pattern detection
4. **Milestone:** Called from milestone completion workflow (optional)

</trigger_modes>

<process>

<step name="parse_arguments">

Parse arguments from the command invocation:

```bash
# Default values
SCOPE="project"
PHASE=""
PATTERNS_ONLY=false
DRIFT_CHECK=false

# Parse arguments
for arg in "$@"; do
  case "$arg" in
    --all)
      SCOPE="all"
      ;;
    --phase)
      # Next arg will be phase number
      EXPECT_PHASE=true
      ;;
    --patterns-only)
      PATTERNS_ONLY=true
      ;;
    --drift|--drift-check)
      DRIFT_CHECK=true
      ;;
    [0-9]*)
      if [ "$EXPECT_PHASE" = true ]; then
        PHASE="$arg"
        EXPECT_PHASE=false
      else
        # Bare number = phase argument
        PHASE="$arg"
      fi
      ;;
  esac
done
```

**Argument meanings:**
- `--all`: Cross-project scope (scan all projects in KB)
- `{phase}` or `--phase {N}`: Include phase-end reflection for specific phase
- `--patterns-only`: Skip lesson distillation, report patterns only
- `--drift` or `--drift-check`: Include semantic drift analysis

</step>

<step name="load_configuration">

Read planning configuration:

```bash
# Load config
MODE=$(cat .planning/config.json 2>/dev/null | grep -o '"mode"[[:space:]]*:[[:space:]]*"[^"]*"' | grep -o '"[^"]*"$' | tr -d '"' || echo "interactive")
DEPTH=$(cat .planning/config.json 2>/dev/null | grep -o '"depth"[[:space:]]*:[[:space:]]*"[^"]*"' | grep -o '"[^"]*"$' | tr -d '"' || echo "standard")
COMMIT_PLANNING_DOCS=$(cat .planning/config.json 2>/dev/null | grep -o '"commit_docs"[[:space:]]*:[[:space:]]*[^,}]*' | grep -o 'true\|false' || echo "true")
git check-ignore -q .planning 2>/dev/null && COMMIT_PLANNING_DOCS=false

PROJECT_NAME=$(basename "$(pwd)" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//;s/-$//')
```

**Config integration:**
- `mode: yolo` - Auto-approve HIGH confidence lessons
- `mode: interactive` - Present all lesson candidates for confirmation
- `depth: quick` - Check only current project, skip drift check
- `depth: standard` - Current project with drift check
- `depth: comprehensive` - Cross-project with full drift analysis

**Depth auto-adjustments:**
If `DEPTH="comprehensive"` and `SCOPE="project"`, auto-enable `--drift-check` if not already set.
If `SCOPE="all"`, depth is effectively comprehensive regardless of setting.

</step>

<step name="verify_kb_exists">

Check that the knowledge base exists and has content:

```bash
KB_DIR="$HOME/.claude/gsd-knowledge"
KB_INDEX="$KB_DIR/index.md"

if [ ! -f "$KB_INDEX" ]; then
  echo "No knowledge base found at $KB_INDEX"
  echo "Run /gsd:collect-signals first to create the KB and collect signals."
  exit 0
fi

# Count signals in index
SIGNAL_COUNT=$(grep -c "^| sig-" "$KB_INDEX" 2>/dev/null || echo 0)
echo "KB index found with $SIGNAL_COUNT signals"
```

**Empty state handling:**
- No KB: Report "No knowledge base found. Run /gsd:collect-signals first."
- KB exists but no signals: Report "No signals found in knowledge base. Nothing to reflect on."

</step>

<step name="prepare_context">

Read artifact contents to pass to the agent. The `@` syntax does not work across Task() boundaries.

```bash
# Read index.md content
INDEX_CONTENT=$(cat "$KB_INDEX")

# If phase-end reflection, read phase artifacts
if [ -n "$PHASE" ]; then
  PADDED_PHASE=$(printf "%02d" ${PHASE} 2>/dev/null || echo "${PHASE}")
  PHASE_DIR=$(ls -d .planning/phases/${PADDED_PHASE}-* .planning/phases/${PHASE}-* 2>/dev/null | head -1)

  if [ -n "$PHASE_DIR" ]; then
    PLAN_CONTENT=""
    SUMMARY_CONTENT=""
    for plan in "$PHASE_DIR"/*-PLAN.md; do
      [ -f "$plan" ] && PLAN_CONTENT="$PLAN_CONTENT\n--- FILE: $plan ---\n$(cat "$plan")"
    done
    for summary in "$PHASE_DIR"/*-SUMMARY.md; do
      [ -f "$summary" ] && SUMMARY_CONTENT="$SUMMARY_CONTENT\n--- FILE: $summary ---\n$(cat "$summary")"
    done
    VERIFICATION_CONTENT=$(cat "$PHASE_DIR"/*-VERIFICATION.md 2>/dev/null || echo "")
  fi
fi

# Read config for agent
CONFIG_CONTENT=$(cat .planning/config.json 2>/dev/null)
```

For cross-project scope, also read signal files from all project directories:

```bash
if [ "$SCOPE" = "all" ]; then
  SIGNAL_FILES_CONTENT=""
  for project_dir in "$KB_DIR/signals"/*/; do
    [ -d "$project_dir" ] || continue
    for signal_file in "$project_dir"/*.md; do
      [ -f "$signal_file" ] && SIGNAL_FILES_CONTENT="$SIGNAL_FILES_CONTENT\n--- FILE: $signal_file ---\n$(cat "$signal_file")"
    done
  done
fi
```

</step>

<step name="spawn_reflector">

Delegate to the `gsd-reflector` agent with prepared context:

```
Task(
  prompt="Run reflection analysis.

  Scope: {SCOPE}
  Project: {PROJECT_NAME}
  Phase: {PHASE or 'none'}
  Patterns only: {PATTERNS_ONLY}
  Drift check: {DRIFT_CHECK}
  Mode: {MODE}

  Knowledge Base Index:
  {INDEX_CONTENT}

  {If phase specified:}
  Plan artifacts:
  {PLAN_CONTENT}

  Summary artifacts:
  {SUMMARY_CONTENT}

  Verification:
  {VERIFICATION_CONTENT}

  {If scope is all:}
  Signal files:
  {SIGNAL_FILES_CONTENT}

  Config:
  {CONFIG_CONTENT}

  Follow your execution_flow to:
  1. Load and filter signals
  2. Detect patterns using severity-weighted thresholds
  3. Perform phase-end reflection if phase specified
  4. Distill lessons (unless patterns-only)
  5. Check semantic drift (if requested)
  6. Return the Reflection Report

  Return the structured Reflection Report when complete.",
  subagent_type="gsd-reflector"
)
```

The agent performs all analysis logic and returns a structured Reflection Report.

</step>

<step name="receive_report">

The reflector agent returns a structured report containing:
- Patterns detected (with type, severity, confidence)
- Phase deviations (if phase-end reflection)
- Lesson candidates (with evidence and scope)
- Drift assessment (if drift check)

Parse the report for results presentation and lesson handling.

</step>

<step name="present_results">

Display user-friendly results:

```
--------------------------------------------------------------
 GSD | REFLECTION COMPLETE
--------------------------------------------------------------

**Scope:** {project / cross-project}
**Project:** {PROJECT_NAME}
**Signals analyzed:** {count}
**Patterns detected:** {count}

### Patterns Found

| # | Pattern | Type | Occurrences | Severity | Confidence |
|---|---------|------|-------------|----------|------------|
| 1 | {name}  | {type} | {count}   | {severity} | {confidence} |

{For each pattern: brief root cause hypothesis}

{If phase-end:}
### Phase {N} Deviations

| Category | Planned | Actual | Delta |
|----------|---------|--------|-------|
| Tasks    | {N}     | {N}    | {+/-N}|

Overall alignment: {HIGH|MEDIUM|LOW}

{If drift check:}
### Semantic Drift Assessment

Status: {STABLE|DRIFTING|CONCERNING}

| Metric | Baseline | Recent | Change |
|--------|----------|--------|--------|
| {metric} | {value} | {value} | {%} |

--------------------------------------------------------------
```

</step>

<step name="handle_lesson_creation">

Based on autonomy mode, handle lesson candidates from the report.

<if mode="yolo">

Auto-approve lessons based on confidence:

```
### Lesson Creation (YOLO Mode)

HIGH confidence lessons (6+ evidence) auto-approved:
- {lesson-1}: written to {path}
- {lesson-2}: written to {path}

MEDIUM/LOW confidence lessons:
- {lesson-3}: written to {path} (project scope)
- {lesson-4}: written to {path} (project scope)

{count} lessons created automatically.
```

Write lesson files using kb-templates/lesson.md format.

</if>

<if mode="interactive">

Present each lesson candidate for confirmation:

```
### Lesson Candidates

**Lesson 1:**
- Category: {category}
- Confidence: {level} ({count} supporting signals)
- Insight: {one-sentence lesson}
- Scope: {project|_global}

Create this lesson? (yes / no / edit)
```

For each response:
- **yes**: Write lesson file
- **no**: Skip
- **edit**: Allow user to modify insight before writing

</if>

Track lessons created for the completion report.

</step>

<step name="rebuild_index">

After any lesson writes, rebuild the KB index:

```bash
if [ "$LESSONS_CREATED" -gt 0 ]; then
  bash ./.claude/agents/kb-rebuild-index.sh
  echo "Index rebuilt after creating $LESSONS_CREATED lessons"
fi
```

</step>

<step name="report_completion">

Display final completion summary:

```
--------------------------------------------------------------
 GSD | REFLECTION SUMMARY
--------------------------------------------------------------

**Scope:** {project / cross-project}
**Signals analyzed:** {count}
**Patterns detected:** {count}
**Lessons created:** {count}

{If phase-end:}
**Phase {N} alignment:** {HIGH|MEDIUM|LOW}

{If drift check:}
**Drift status:** {STABLE|DRIFTING|CONCERNING}

### Patterns Found

| Pattern | Confidence | Action |
|---------|------------|--------|
| {name}  | {level}    | Lesson created / Logged for reference |

### Lessons Created

| File | Category | Insight |
|------|----------|---------|
| {path} | {category} | {brief} |

--------------------------------------------------------------

Next: Lessons will surface via /gsd:kb-search during future planning.

--------------------------------------------------------------
```

</step>

<step name="commit_lessons">

If lessons were written and `COMMIT_PLANNING_DOCS` is true, commit the new lesson files:

```bash
if [ "$COMMIT_PLANNING_DOCS" = "true" ] && [ "$LESSONS_CREATED" -gt 0 ]; then
  # Stage individual lesson files
  for lesson_file in $(find ./.claude/gsd-knowledge/lessons/ -name "les-*.md" -newer ./.claude/gsd-knowledge/index.md 2>/dev/null); do
    git add "$lesson_file"
  done
  # Stage updated index
  git add ./.claude/gsd-knowledge/index.md
  git commit -m "docs(lessons): distill ${LESSONS_CREATED} lessons from reflection

- Patterns analyzed: ${PATTERNS_DETECTED}
- Scope: ${SCOPE}
- Index rebuilt"
fi
```

Skip if `COMMIT_PLANNING_DOCS` is false or no lessons were created.

</step>

</process>

<empty_state_handling>

**No KB:**
```
No knowledge base found at ./.claude/gsd-knowledge/index.md
Run /gsd:collect-signals first to create the KB and collect signals.
```

**KB exists but no signals:**
```
No signals found in knowledge base. Nothing to reflect on.

Signals are collected after phase execution via /gsd:collect-signals.
```

**Signals but no patterns:**
```
{N} signals analyzed but no recurring patterns detected.

Pattern detection requires:
- Critical/high severity: 2+ occurrences
- Medium severity: 4+ occurrences
- Low severity: 5+ occurrences

Consider accumulating more signals or check thresholds in reflection-patterns.md.
```

**Patterns but no lesson candidates:**
```
{N} patterns found but none meet distillation criteria.

Lesson distillation requires:
- Pattern meets threshold (confirmed)
- Consistent root cause across signals
- Actionable recommendation possible

Patterns are logged for future reference.
```

</empty_state_handling>

<error_handling>

**No phase directory (when phase specified):** Report error with available phases.
**Agent failure:** Report what was attempted and the error.
**Write failure:** Report which lesson failed to write and continue with others.
**Index rebuild failure:** Report error but don't fail the workflow.

</error_handling>
