<purpose>
Migrate the current project's GSD Reflect configuration to match the installed version. Adds new config fields with sensible defaults, prompts for preferences on new features (in interactive mode), and logs the migration.

This workflow does NOT spawn subagents -- it executes migration logic directly (mechanical config patching + optional questions).
</purpose>

<core_principle>
Upgrades are additive and non-destructive. Existing settings are preserved exactly as they are. Only new fields are added. The version stamp is updated last, ensuring partial migrations are retried on the next run.
</core_principle>

<required_reading>
Read version-migration.md for migration actions and mini-onboarding questions.
Read ui-brand.md for output formatting conventions.
Read .planning/config.json for current project configuration.
</required_reading>

<process>

<step name="detect_versions">
## 1. Detect Versions

Read the installed version:
1. Check `{project}/.claude/get-shit-done/VERSION` first (local install)
2. Fall back to `./.claude/get-shit-done/VERSION` (global install)
3. If neither exists: report "Cannot determine installed version. Run `/gsd:update` first." and exit.

Read the project version:
1. Read `.planning/config.json`
2. If file does not exist: report "Project not initialized. Run `/gsd:new-project` first." and exit.
3. Extract `gsd_reflect_version` field
4. If field is absent: project version is `0.0.0` (pre-tracking)
</step>

<step name="compare_versions">
## 2. Compare Versions

Compare installed vs project using numeric dot-separated comparison (split on dots, compare major.minor.patch).

**If versions match:** Report "Project is up to date (version {version})" and exit.

**If installed version is BEHIND project version:** Report "Installed GSD Reflect version ({installed}) is older than project version ({project}). Run `/gsd:update` to get the latest version." and exit.

**If installed version is AHEAD of project version:** Proceed with migration.
</step>

<step name="display_banner">
## 3. Display Migration Banner

```
## Project Migration: {old_version} -> {new_version}

Migrating project configuration to match installed GSD Reflect version.
All changes are additive -- existing settings are preserved.
```
</step>

<step name="determine_mode">
## 4. Determine Mode

Check if `--auto` flag was passed in arguments OR if `.planning/config.json` has `"mode": "yolo"`:
- If `--auto` or YOLO mode: apply all defaults silently (no questions)
- If interactive mode (no `--auto`): run mini-onboarding questions for new features
</step>

<step name="apply_patches">
## 5. Apply Additive Config Patches

Read the current `.planning/config.json` content. For each migration action defined in version-migration.md:

1. **`gsd_reflect_version`** -- if absent, will be set at the end (after all other changes succeed)
2. **`health_check` section** -- if absent, add with defaults (or user-chosen values in interactive mode)
3. **`devops` section** -- if absent, add with defaults (or user-chosen values in interactive mode)

**In interactive mode**, before adding each new section, ask the user for their preferences per the mini-onboarding questions in version-migration.md:

- Health check frequency: `milestone-only` (default), `on-resume`, `every-phase`, `explicit-only`
- Health check blocking: `false` (default), `true`
- DevOps context: `skip` (apply defaults) or `configure` (ask follow-up questions)

**In YOLO/auto mode**, apply all defaults without prompting.

Write the updated config.json with the new fields added. Preserve ALL existing fields and values exactly as they are. Add new fields at the end of the JSON object (before the closing `}`).

Update `gsd_reflect_version` to the installed version LAST (only after all other changes succeed). This ensures partial migrations are retried on next run.
</step>

<step name="log_migration">
## 6. Log Migration

Append a migration entry to `.planning/migration-log.md`:

- If the file does not exist, create it with the header from the migration log template in version-migration.md
- Prepend the new entry (most recent first, after the header)
- Include: source version, target version, ISO timestamp, changes applied, user choices
</step>

<step name="report_results">
## 7. Report Results

Display a summary of what changed:

```
### Migration Complete: {old} -> {new}

**Changes applied:**
- {list of fields/sections added}

**User choices:**
- {setting}: {value}

Migration logged to `.planning/migration-log.md`
```
</step>

</process>

<error_handling>
**No VERSION file found:** Direct user to run `/gsd:update` first.
**No config.json:** Direct user to run `/gsd:new-project` first.
**Versions already match:** Report up-to-date status and exit cleanly.
**Installed behind project:** Warn user and suggest `/gsd:update`.
**Config write failure:** Report error, do NOT update version stamp (ensures retry on next run).
</error_handling>
