---
name: gsd:health-check
description: Validate workspace state and report actionable findings
argument-hint: "[--full] [--focus kb|planning] [--fix] [--stale-days N]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

<objective>
Validate workspace state (KB integrity, config validity, stale artifacts) and report actionable findings. Optionally repair issues with `--fix`.

Flags:
- `--full` -- Run all check categories including planning consistency and config drift
- `--focus kb` -- Run only KB Integrity checks
- `--focus planning` -- Run only Planning Consistency checks
- `--fix` -- Enable repair mode (auto in YOLO, prompt in interactive)
- `--stale-days N` -- Override configured staleness threshold
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/health-check.md
@./.claude/get-shit-done/references/health-check.md
</execution_context>

<context>
Arguments: $ARGUMENTS

@.planning/config.json
</context>

<process>
1. **Parse arguments** from $ARGUMENTS for flags (--full, --focus, --fix, --stale-days)
2. **Delegate to workflow** at `get-shit-done/workflows/health-check.md`
   - Workflow loads config and reference specification
   - Determines check scope based on flags
   - Executes mechanical checks via Bash/Read/Grep tools
   - Reports categorized findings with pass/warning/fail status
   - Repairs fixable issues if --fix flag present
   - Optionally persists health-check signal to KB
3. **Report completion** with check counts and next steps
</process>
