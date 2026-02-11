# Run Spike Workflow

Orchestrates the full spike flow: workspace creation, Design phase (DESIGN.md), agent spawn for Build/Run/Document, and RESEARCH.md integration.

## References

@get-shit-done/references/spike-execution.md
@.claude/agents/gsd-spike-runner.md
@.claude/agents/kb-templates/spike-design.md
@.claude/agents/kb-templates/spike-decision.md
@.claude/agents/knowledge-store.md

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| question | /gsd:spike argument or user prompt | yes |
| phase | /gsd:spike --phase argument | no |
| mode | .planning/config.json "mode" field | no (default: interactive) |
| sensitivity | .planning/config.json "spike_sensitivity" or derived from depth | no |

## Execution Flow

### 1. Parse Inputs

```bash
# Get question from argument or prompt
QUESTION="${1:-}"
if [ -z "$QUESTION" ]; then
  # Interactive: prompt user for question
  echo "What question would you like to investigate?"
  read QUESTION
fi

# Get phase linkage
PHASE="${2:-project-level}"

# Get mode
MODE=$(cat .planning/config.json 2>/dev/null | grep -o '"mode"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4)
MODE="${MODE:-interactive}"
```

### 2. Create Workspace

```bash
# Find next index
EXISTING=$(ls -d .planning/spikes/[0-9][0-9][0-9]-* 2>/dev/null | wc -l | tr -d ' ')
NEXT_INDEX=$(printf "%03d" $((EXISTING + 1)))

# Generate slug from question
SLUG=$(echo "$QUESTION" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//;s/-$//' | cut -c1-40)

# Create workspace
WORKSPACE=".planning/spikes/${NEXT_INDEX}-${SLUG}"
mkdir -p "$WORKSPACE"
```

### 3. Draft DESIGN.md (Design Phase)

Using the spike-design template, create DESIGN.md with:

- **Question:** {from input}
- **Type:** Infer from question patterns:
  - "Which/what/best" -> Comparative
  - "Can/is/does/will" -> Binary
  - "How does/why/explore" -> Exploratory
  - Other -> Open Inquiry (user can adjust)
- **Hypothesis:** Draft initial hypothesis from question
- **Success Criteria:** Draft measurable criteria based on type
- **Experiment Plan:** Draft 2-3 experiments

Write to `$WORKSPACE/DESIGN.md`.

### 4. User Confirmation (Interactive Mode)

**If mode == interactive:**

Present DESIGN.md to user:

```markdown
## SPIKE DESIGN

**Workspace:** {workspace path}
**Question:** {question}
**Type:** {inferred type}

### Hypothesis

{drafted hypothesis}

### Success Criteria

{drafted criteria}

### Experiment Plan

{drafted experiments}

---

**Options:**
1. Approve and proceed to Build phase
2. Edit DESIGN.md (opens for modification)
3. Cancel spike

Select [1/2/3]:
```

Wait for user response. If option 2, allow edits, then re-present.

**If mode == yolo:**

Auto-approve DESIGN.md, proceed immediately.

### 5. Spawn Spike Runner Agent

```markdown
**Spawning gsd-spike-runner agent**

@.claude/agents/gsd-spike-runner.md

Execute Build -> Run -> Document phases for:
- Workspace: {workspace path}
- DESIGN.md: {workspace}/DESIGN.md

Return when complete with outcome and decision summary.
```

### 6. Handle Agent Result

Parse agent output:
- outcome: confirmed | rejected | partial | inconclusive
- decision: one-line summary
- kb_entry: path to KB spike entry

### 7. Update RESEARCH.md (If Phase-Linked)

**If phase was specified:**

Read `{PHASE_DIR}/*-RESEARCH.md` and add/update "Resolved by Spike" section:

```markdown
## Open Questions

### Resolved by Spike

1. **{Question}**
   - Decision: {one-line answer from DECISION.md}
   - Evidence: {brief summary}
   - Full analysis: {path to DECISION.md}
   - Confidence: {HIGH|MEDIUM|LOW}
```

If RESEARCH.md doesn't exist yet, note that spike resolution should be added when it's created.

### 8. Report Result

```markdown
## SPIKE COMPLETE

**Spike:** {index}-{slug}
**Outcome:** {outcome}
**Decision:** {one-line decision}

### Artifacts

- Workspace: {workspace path}
- DESIGN.md: {workspace}/DESIGN.md
- DECISION.md: {workspace}/DECISION.md
- KB Entry: {kb_entry path}

{If phase-linked:}
### Integration

RESEARCH.md updated with spike resolution at:
{phase RESEARCH.md path}
```

## Error Handling

- **No .planning/ directory:** Error - run from project root with GSD initialized
- **Agent checkpoint:** Surface to user, await guidance
- **KB write failure:** Log warning, spike artifacts still valid in workspace

## Mode Behaviors

| Mode | Design Confirmation | Inconclusive Round 1 |
|------|---------------------|----------------------|
| interactive | User confirms | Checkpoint for narrowing approval |
| yolo | Auto-approve | Auto-proceed with agent's narrowed hypothesis |

## Sensitivity Behaviors

Sensitivity affects spike triggering from orchestrators (plan-phase, new-project), not this manual command. /gsd:spike always runs the requested spike regardless of sensitivity setting.
