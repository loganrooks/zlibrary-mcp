<purpose>
Create a manual signal entry in the knowledge base capturing an observation from the current conversation. Supports inline arguments for zero-interaction usage or guided fill with at most one follow-up round.

The signal is written to the persistent knowledge store and indexed for future retrieval by the Reflection Engine and Knowledge Surfacing phases.
</purpose>

<core_principle>
Manual signals capture user observations that automated signal collection cannot detect. The workflow prioritizes low-friction input (inline arguments, auto-inference) while preserving signal quality (dedup checking, cap enforcement, proper metadata).
</core_principle>

<required_reading>
Read STATE.md before any operation to load project context (phase, plan).
Read config.json for commit_docs settings.
Read the knowledge-store.md agent spec for KB conventions.
Read signal-detection.md for severity rules, dedup logic, and cap enforcement.
Read kb-templates/signal.md for the signal entry template.
</required_reading>

<process>

<step name="parse_arguments">
## Step 1: Parse Arguments

Extract from inline arguments if provided:
- **description** -- the quoted string (required, but can be asked for)
- **--severity** -- `critical` or `notable` (optional, auto-assigned if missing)
- **--type** -- `deviation`, `struggle`, `config-mismatch`, or `custom` (optional, inferred if missing)

Store what was provided. Identify what is missing.
</step>

<step name="extract_context">
## Step 2: Extract Conversation Context

Scan the current conversation and project state for context:

1. **Phase and plan**: Check conversation for current phase/plan references. If not evident, read `.planning/STATE.md` for current position.
2. **Project name**: Derive from working directory basename, converted to kebab-case.
3. **Frustration detection**: Scan recent conversation messages for frustration indicators from signal-detection.md Section 5 (SGNL-06):

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

   **Threshold:** 2+ patterns detected in recent messages.

   **If threshold met:** Mention the detected frustration patterns to the user and offer to include frustration context in the signal. This is suggestive, not automatic -- the user decides whether frustration is relevant. Example:

   ```
   I noticed some frustration indicators in our recent conversation
   ("still not working", "keeps failing"). Would you like to include
   frustration context in this signal? (y/n)
   ```
</step>

<step name="fill_missing">
## Step 3: Fill Missing Information (Max 1 Follow-up)

Collect all missing required information in a single follow-up if needed. If the user provided everything inline, skip this step entirely (zero follow-ups).

**Single follow-up round** combining all missing fields:

- **If no description provided:** Ask "What did you observe?" (this is the only truly required input)
- **If no severity provided:** Auto-assign using signal-detection.md Section 6 (SGNL-04) severity rules:

  | Condition | Severity |
  |-----------|----------|
  | Verification failed, config mismatch | critical |
  | Multiple issues, non-trivial problems, unexpected improvements | notable |

  Show the auto-assignment and allow override: `Severity auto-assigned: notable (override? or press enter to accept)`

- **If no type provided:** Infer from description keywords:
  - Contains "deviat", "unexpected", "changed", "different from plan" -> `deviation`
  - Contains "struggle", "stuck", "debug", "retry", "failing" -> `struggle`
  - Contains "config", "environment", "model", "setting" -> `config-mismatch`
  - Otherwise -> `custom`

- **Polarity:** Auto-assign based on content:
  - Negative indicators (problems, failures, struggles, frustration) -> `negative`
  - Positive indicators (improvements, faster, cleaner, better) -> `positive`
  - Otherwise -> `neutral`
</step>

<step name="preview">
## Step 4: Show Preview Before Writing

Display the signal preview for confirmation:

```
## Signal Preview

**Description:** {description}
**Severity:** {severity}
**Type:** {type}
**Polarity:** {polarity}
**Phase:** {phase} | **Plan:** {plan}
**Source:** manual

Save this signal? (y/n)
```

Wait for user confirmation. If rejected, allow edits or cancel.
</step>

<step name="dedup_check">
## Step 5: Deduplication Check

Before writing, check for related existing signals per signal-detection.md Section 9 (SGNL-05):

1. Read the knowledge store index at `./.claude/gsd-knowledge/index.md` (if it exists).
2. For each existing active signal, check:
   - Same `signal_type`
   - Same `project`
   - 2+ shared tags between new and existing signal
3. If matches found:
   - Show the related signals to the user
   - Add matched signal IDs to the `related_signals` array on the new signal
   - Set `occurrence_count` to the highest `occurrence_count` among matches + 1
4. If no matches: `related_signals: []`, `occurrence_count: 1`

Do NOT modify existing signals (immutability constraint).
</step>

<step name="cap_check">
## Step 6: Per-Phase Signal Cap Check

Enforce per-phase cap per signal-detection.md Section 10 (SGNL-09):

1. Count existing active signals for this phase and project (from index).
2. If count < 10: proceed normally.
3. If count >= 10: compare new signal severity against the lowest-severity existing signal.
   - If new >= lowest: archive the lowest-severity signal (set `status: archived` in its frontmatter), then write the new signal.
   - If new < lowest: inform user the signal cannot be persisted due to cap, offer to override.

Severity ordering for cap: critical > notable.
Trace signals are never persisted and do not count toward cap.
</step>

<step name="write_signal">
## Step 7: Write Signal File

Generate the signal entry using the kb-templates/signal.md template.

**File location:** `./.claude/gsd-knowledge/signals/{project}/`

**Filename:** `{YYYY-MM-DD}-{slug}.md` where slug is derived from the description (kebab-case, max 50 chars).

**ID:** `sig-{YYYY-MM-DD}-{slug}`

**Frontmatter fields** (base schema + signal extensions + Phase 2 extensions):

```yaml
---
id: sig-{YYYY-MM-DD}-{slug}
type: signal
project: {project-name}
tags: [{inferred-tags}]
created: {ISO-8601-now}
updated: {ISO-8601-now}
durability: {workaround|convention|principle}
status: active
severity: {critical|notable}
signal_type: {deviation|struggle|config-mismatch|custom}
phase: {phase-number}
plan: {plan-number}
polarity: {positive|negative|neutral}
source: manual
occurrence_count: {count}
related_signals: [{ids}]
---
```

**Body sections:**
- `## What Happened` -- the user's description, expanded with context
- `## Context` -- phase, plan, task context from conversation
- `## Potential Cause` -- agent's assessment if inferable, or "User observation -- no automated cause analysis"

Create parent directories if needed (`mkdir -p`).
</step>

<step name="rebuild_index">
## Step 8: Rebuild Index

Run the knowledge base index rebuild script:

```bash
bash ./.claude/agents/kb-rebuild-index.sh
```

This regenerates `./.claude/gsd-knowledge/index.md` from all entry files.
</step>

<step name="git_commit">
## Step 9: Git Commit (Conditional)

Check `commit_planning_docs` setting:

```bash
COMMIT_DOCS=$(cat .planning/config.json 2>/dev/null | grep -o '"commit_docs"[[:space:]]*:[[:space:]]*[^,}]*' | grep -o 'true\|false' || echo "true")
```

Also check if `.planning` is gitignored:
```bash
git check-ignore -q .planning 2>/dev/null && COMMIT_DOCS=false
```

**If commit_docs is true:**
```bash
git add -f ./.claude/gsd-knowledge/signals/{project}/{filename}
git commit -m "docs(signal): {slug}"
```

**If commit_docs is false:** Skip git operations, inform user the signal was saved but not committed.
</step>

<step name="confirm">
## Step 10: Confirm

Display confirmation:

```
Signal created: {id}
File: ./.claude/gsd-knowledge/signals/{project}/{filename}
Index rebuilt.
```
</step>

</process>

<design_notes>
- **Maximum 2 interaction rounds:** Arguments + one follow-up if needed. If everything is inline, zero follow-ups.
- **Frustration detection is suggestive:** The agent mentions patterns found but the user decides whether to include frustration context. No automatic signal creation from frustration alone.
- **Git behavior follows commit_planning_docs setting** from .planning/config.json.
- **All manual signals are persisted** regardless of severity level, since the user explicitly chose to record them (per signal-detection.md Section 6 manual override rule).
- **Source field is always `manual`** for signals created via this command (distinguishes from `auto` signals created by gsd-signal-collector).
</design_notes>
