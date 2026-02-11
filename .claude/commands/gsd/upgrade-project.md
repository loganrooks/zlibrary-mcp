---
name: gsd:upgrade-project
description: Migrate project to current GSD Reflect version with mini-onboarding for new features
argument-hint: "[--auto]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

<objective>
Migrate the current project's GSD Reflect configuration to match the installed version.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/upgrade-project.md
@./.claude/get-shit-done/references/version-migration.md
@./.claude/get-shit-done/references/ui-brand.md
</execution_context>

<context>
Arguments: $ARGUMENTS

@.planning/config.json
</context>

<process>
Execute the upgrade workflow from @./.claude/get-shit-done/workflows/upgrade-project.md end-to-end.

Pass arguments (including `--auto` flag if present) to the workflow. The workflow handles:
- Version detection (installed vs project)
- Version comparison and migration decision
- Interactive or auto mode config patching
- Migration logging
- Results reporting
</process>
