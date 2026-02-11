<purpose>
Orchestrate post-execution signal collection for a completed phase. Spawns the signal collector agent to analyze execution artifacts and persist detected signals to the knowledge base.
</purpose>

<core_principle>
Signal collection is a retrospective pass — it reads execution artifacts (PLANs, SUMMARYs, VERIFICATION) without modifying them. The workflow validates prerequisites, delegates detection to the signal collector agent, and presents results.
</core_principle>

<required_reading>
Read STATE.md before any operation to load project context.
Read config.json for model_profile and commit_docs settings.
</required_reading>

<process>

<step name="validate_input">
Receive phase number as argument. Validate and locate the phase directory:

```bash
PHASE_ARG="$1"
PADDED_PHASE=$(printf "%02d" ${PHASE_ARG} 2>/dev/null || echo "${PHASE_ARG}")
PHASE_DIR=$(ls -d .planning/phases/${PADDED_PHASE}-* .planning/phases/${PHASE_ARG}-* 2>/dev/null | head -1)

if [ -z "$PHASE_DIR" ]; then
  echo "ERROR: No phase directory found matching phase '${PHASE_ARG}'"
  echo "Check .planning/phases/ for available phases."
  exit 1
fi

echo "Phase directory: $PHASE_DIR"
```

Error if no matching directory exists.
</step>

<step name="locate_artifacts">
Find all execution artifacts in the phase directory:

```bash
# Find all PLAN.md and SUMMARY.md files
PLANS=$(ls -1 "$PHASE_DIR"/*-PLAN.md 2>/dev/null)
SUMMARIES=$(ls -1 "$PHASE_DIR"/*-SUMMARY.md 2>/dev/null)
VERIFICATION=$(ls -1 "$PHASE_DIR"/*-VERIFICATION.md 2>/dev/null)

PLAN_COUNT=$(echo "$PLANS" | grep -c '.' 2>/dev/null || echo 0)
SUMMARY_COUNT=$(echo "$SUMMARIES" | grep -c '.' 2>/dev/null || echo 0)

echo "Plans found: $PLAN_COUNT"
echo "Summaries found: $SUMMARY_COUNT"
echo "Verification: ${VERIFICATION:-none}"
```

Count how many plans have summaries (completed plans only).
</step>

<step name="check_prerequisites">
At least one SUMMARY.md must exist — signals can only be detected from completed plans:

```bash
if [ "$SUMMARY_COUNT" -eq 0 ]; then
  echo "No completed plans to analyze."
  echo "Run /gsd:execute-phase $PHASE_ARG first to execute plans, then collect signals."
  exit 0
fi
```

Report: "Analyzing {N} completed plans for phase {X}"
</step>

<step name="load_config">
Read planning configuration:

```bash
MODEL_PROFILE=$(cat .planning/config.json 2>/dev/null | grep -o '"model_profile"[[:space:]]*:[[:space:]]*"[^"]*"' | grep -o '"[^"]*"$' | tr -d '"' || echo "balanced")
COMMIT_PLANNING_DOCS=$(cat .planning/config.json 2>/dev/null | grep -o '"commit_docs"[[:space:]]*:[[:space:]]*[^,}]*' | grep -o 'true\|false' || echo "true")
git check-ignore -q .planning 2>/dev/null && COMMIT_PLANNING_DOCS=false

PROJECT_NAME=$(basename "$(pwd)" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//;s/-$//')
```

Store `MODEL_PROFILE`, `COMMIT_PLANNING_DOCS`, and `PROJECT_NAME` for use in agent spawn.
</step>

<step name="spawn_signal_collector">
Delegate to the `gsd-signal-collector` agent with all necessary context.

Before spawning, read artifact contents — the `@` syntax does not work across Task() boundaries:

```bash
# Read all artifact files into variables
for plan in $PLANS; do
  PLAN_CONTENT="$PLAN_CONTENT\n--- FILE: $plan ---\n$(cat "$plan")"
done
for summary in $SUMMARIES; do
  SUMMARY_CONTENT="$SUMMARY_CONTENT\n--- FILE: $summary ---\n$(cat "$summary")"
done
if [ -n "$VERIFICATION" ]; then
  VERIFICATION_CONTENT=$(cat "$VERIFICATION")
fi
CONFIG_CONTENT=$(cat .planning/config.json 2>/dev/null)
```

Spawn the agent:

```
Task(
  prompt="Collect signals for phase {PADDED_PHASE}.

  Phase directory: {PHASE_DIR}
  Project name: {PROJECT_NAME}
  Model profile: {MODEL_PROFILE}

  Plan artifacts:
  {PLAN_CONTENT}

  Summary artifacts:
  {SUMMARY_CONTENT}

  Verification (if exists):
  {VERIFICATION_CONTENT}

  Config:
  {CONFIG_CONTENT}

  Follow your execution_flow to detect, classify, filter, and persist signals.
  Return the Signal Collection Report when complete.",
  subagent_type="gsd-signal-collector"
)
```

The agent performs all detection logic and returns a structured Signal Collection Report.
</step>

<step name="receive_report">
The signal collector agent returns a structured report containing:
- Signals detected (with type, severity, polarity, description, status)
- Summary counts (persisted, trace, capped, duplicates)
- Signal files written (paths and IDs)
- Notes and observations

Parse the report for the results presentation step.
</step>

<step name="present_results">
Display user-friendly results using GSD UI patterns:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GSD ► SIGNAL COLLECTION COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Phase {X}: {Name}**
Plans analyzed: {N}

### Severity Breakdown

| Severity | Count | Action |
|----------|-------|--------|
| critical | {N} | Persisted to KB |
| notable  | {N} | Persisted to KB |
| trace    | {N} | Logged only |

### Signals Persisted

{Table from agent report — ID, type, severity, description}

### Signal Files

{List of files written to ./.claude/gsd-knowledge/signals/}

───────────────────────────────────────────────────────────────

Index rebuilt via kb-rebuild-index.

───────────────────────────────────────────────────────────────
```

If zero signals detected:
```
No signals detected for phase {X}. Clean execution.
```
</step>

<step name="commit_signals">
If signals were written and `COMMIT_PLANNING_DOCS` is true, commit the new signal files:

```bash
if [ "$COMMIT_PLANNING_DOCS" = "true" ] && [ "$SIGNALS_WRITTEN" -gt 0 ]; then
  # Stage individual signal files
  for signal_file in $(ls ./.claude/gsd-knowledge/signals/${PROJECT_NAME}/*.md 2>/dev/null); do
    git add "$signal_file"
  done
  # Stage updated index
  git add ./.claude/gsd-knowledge/index.md
  git commit -m "docs(signals): collect phase ${PADDED_PHASE} signals

- ${SIGNALS_WRITTEN} signals persisted
- Index rebuilt"
fi
```

Skip if `COMMIT_PLANNING_DOCS` is false or no signals were written.
</step>

</process>

<error_handling>
**No phase directory:** Report error with available phases and exit.
**No summaries:** Report "no completed plans" and exit cleanly (not an error).
**Agent failure:** Report what was attempted and suggest manual `/gsd:signal` for individual entries.
**KB directory missing:** Agent creates it (mkdir -p) during signal write step.
</error_handling>
