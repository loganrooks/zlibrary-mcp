<purpose>
Orchestrate workspace health validation. Runs mechanical checks against KB integrity, config validity, stale artifacts, and optionally planning consistency and config drift. Reports categorized findings and optionally repairs issues.
</purpose>

<core_principle>
Health checks are mechanical -- every check is binary (pass/fail) based on file existence, JSON parsability, count matching, or timestamp comparison. No subjective assessment. The executing agent runs all checks directly via Bash/Read/Grep tools (no subagent spawning needed).
</core_principle>

<required_reading>
Read `get-shit-done/references/health-check.md` for check definitions, thresholds, output format, and repair rules.
Read `.planning/config.json` for health_check settings and autonomy mode.
</required_reading>

<process>

<step name="parse_arguments">
Parse command arguments for execution flags.

Supported flags:
- `--full` -- Run all check categories (default + full tier)
- `--focus kb` -- Run only KB Integrity checks
- `--focus planning` -- Run only Planning Consistency checks
- `--fix` -- Enable repair mode
- `--stale-days N` -- Override staleness threshold

```
Arguments: $ARGUMENTS

Parse flags:
  FULL_MODE = true if "--full" present
  FOCUS_MODE = "kb" | "planning" | null (from "--focus {value}")
  FIX_MODE = true if "--fix" present
  STALE_DAYS_OVERRIDE = N if "--stale-days N" present
```

Validate flag combinations:
- `--focus` takes priority over `--full`
- `--focus` and `--fix` are compatible
- `--stale-days` requires a numeric value
</step>

<step name="load_configuration">
Read workspace configuration for health check settings and autonomy mode.

```bash
CONFIG=".planning/config.json"

# Read config if it exists
if [ -f "$CONFIG" ]; then
  MODE=$(node -e "const c=JSON.parse(require('fs').readFileSync('$CONFIG','utf8')); console.log(c.mode||'interactive')" 2>/dev/null)
  STALE_THRESHOLD=$(node -e "const c=JSON.parse(require('fs').readFileSync('$CONFIG','utf8')); console.log((c.health_check||{}).stale_threshold_days||7)" 2>/dev/null)
else
  MODE="interactive"
  STALE_THRESHOLD=7
fi

# Flag override for stale days
if [ -n "$STALE_DAYS_OVERRIDE" ]; then
  STALE_THRESHOLD="$STALE_DAYS_OVERRIDE"
fi
```

Store:
- `MODE` -- yolo or interactive (controls repair prompting)
- `STALE_THRESHOLD` -- days before artifacts are considered stale
</step>

<step name="load_reference">
Load the health check reference specification for check definitions.

```
@./.claude/get-shit-done/references/health-check.md
```

The reference defines:
- All check IDs and their pass/fail conditions (Section 2)
- Shell patterns for each check (Section 2)
- Output format (Section 4)
- Repair actions for fixable issues (Section 5)
- Signal integration rules (Section 6)
</step>

<step name="determine_scope">
Select which check categories to run based on flags.

```
If FOCUS_MODE == "kb":
  categories = [KB Integrity]
Else if FOCUS_MODE == "planning":
  categories = [Planning Consistency]
Else if FULL_MODE:
  categories = [KB Integrity, Config Validity, Stale Artifacts, Planning Consistency, Config Drift]
Else (default):
  categories = [KB Integrity, Config Validity, Stale Artifacts]
```

Report scope to user:
```
Running health check: {mode} mode
Categories: {list of categories}
Staleness threshold: {N} days
```
</step>

<step name="execute_checks">
For each category in scope, execute the checks defined in the reference specification.

**Execution approach:** Use Bash tool for shell commands (file existence, JSON parsing, grep counts, find for stale files). Collect results as a structured list of check outcomes.

**Result format per check:**
```
{
  id: "KB-01",
  category: "KB Integrity",
  description: "Index file exists",
  status: "PASS" | "WARNING" | "FAIL",
  detail: "Additional context or remediation hint",
  repairable: true | false
}
```

**Category execution order:**
1. KB Integrity (KB-01 through KB-06) -- if in scope
2. Config Validity (CFG-01 through CFG-06) -- if in scope
3. Stale Artifacts (STALE-01 through STALE-03) -- if in scope
4. Planning Consistency (PLAN-01 through PLAN-03) -- if in scope (full/focus only)
5. Config Drift (DRIFT-01 through DRIFT-02) -- if in scope (full only)

**For each check:**
1. Run the shell pattern from the reference specification
2. Capture the result (pass, warning, or fail)
3. Capture detail information (counts, file paths, field names)
4. Record whether the issue is repairable (per Section 5 of reference)

**Early termination within categories:**
- If KB-01 (index exists) fails, skip KB-02 through KB-06
- If CFG-01 (config exists) fails, skip CFG-02 through CFG-06
- If CFG-02 (JSON parseable) fails, skip CFG-03 through CFG-06
</step>

<step name="report_findings">
Display the categorized checklist output format defined in Section 4 of the reference.

```markdown
## Workspace Health Report
**Project:** {project-name} | **Version:** {gsd_reflect_version|unknown} | **Date:** {YYYY-MM-DD}

### {Category} [{PASS|WARNING|FAIL}]
- [x] Passed check description (detail)
- [ ] Failed check description (remediation hint)

### Summary
**{N} checks passed** | **{M} warnings** | **{K} failures**
```

**Category status determination:**
- PASS -- all checks in category passed
- WARNING -- at least one WARNING, no FAILs
- FAIL -- at least one FAIL in category

If warnings or failures exist, append:
```
Run `/gsd:health-check --fix` to auto-repair fixable issues.
```
</step>

<step name="repair_if_requested">
If `--fix` flag is set and repairable issues exist, execute repairs.

**YOLO mode (`mode: yolo`):**
- Auto-repair each repairable issue without prompting
- Report each repair action taken

**Interactive mode (`mode: interactive`):**
- For each repairable issue, use AskUserQuestion:
  ```
  AskUserQuestion("Repair: {description}. {repair_action}. Proceed? (yes/no/abort)")
  ```
  - "yes" -- apply repair, continue to next
  - "no" -- skip this repair, continue to next
  - "abort" -- stop all repairs

**Repair actions (from reference Section 5):**
- KB index mismatch: Run `./.claude/agents/kb-rebuild-index.sh`
- Missing gsd_reflect_version: Set to installed VERSION value
- Missing health_check section: Add default config section
- Missing config template fields: Add with template defaults
- Orphaned .continue-here files: Delete the stale files

**After repairs:** Re-run affected checks and update the report with repaired status.
</step>

<step name="signal_integration">
If findings include WARNING or FAIL results, optionally persist a health-check signal.

**Determine signal need:**
- Warnings or failures found: persist as `notable` severity signal
- All clean: log as trace (not persisted)

**Autonomy behavior:**
- YOLO mode: auto-persist signal
- Interactive mode: ask user via AskUserQuestion

**Signal creation (if persisting):**
Write a signal file to `./.claude/gsd-knowledge/signals/{project-name}/` following the signal schema from knowledge-store.md.

Signal fields:
- `type: signal`
- `signal_type: custom`
- `severity: notable`
- `polarity: negative` (or positive if clean after previous issues)
- `tags: [workspace/health-check, workspace/{failing-category}]`
- `source: auto`

After writing, run `./.claude/agents/kb-rebuild-index.sh` to update the index.
</step>

<step name="final_summary">
Display final summary with next steps.

```
Health check complete.

{N} checks passed | {M} warnings | {K} failures
{R} issues repaired (if --fix was used)
{S} signal persisted (if signal was written)

Next steps:
- {Actionable suggestions based on findings}
```

Possible next steps:
- "Run `/gsd:health-check --fix` to repair fixable issues" (if unfixed issues remain)
- "Review abandoned debug sessions in .planning/debug/" (if STALE-02 warned)
- "Complete or remove incomplete spikes in .planning/spikes/" (if STALE-03 warned)
- "Run `/gsd:new-project` to initialize workspace" (if config missing)
- "All clear -- workspace is healthy" (if everything passed)
</step>

</process>

<error_handling>
**Missing KB directory:** Report all KB checks as FAIL with "KB not initialized" message. Not repairable via --fix.
**Missing config.json:** Report CFG-01 as FAIL and skip remaining config checks. Not repairable via --fix.
**No .planning/ directory:** Report "Project not initialized -- run `/gsd:new-project`" and exit.
**Repair failure:** Report the failed repair and continue to next repairable issue. Do not abort all repairs on a single failure.
**Shell command failure:** Report the check as FAIL with the error message. Continue to next check.
</error_handling>
