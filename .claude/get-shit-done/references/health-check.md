# Health Check Reference

## 1. Overview

Defines check definitions, thresholds, output format, repair rules, and signal integration for workspace validation via `/gsd:health-check`.

**Purpose:** Validate workspace state and report actionable findings. The health check is the primary workspace maintenance tool -- the first thing users reach for when something seems wrong.

**Consumers:**
- `/gsd:health-check` command (user-facing entry point)
- `get-shit-done/workflows/health-check.md` (orchestration logic)

**Modes:**

| Mode | Flag | Checks Included | Expected Duration |
|------|------|-----------------|-------------------|
| Default (quick) | (none) | KB Integrity, Config Validity, Stale Artifacts | <5s |
| Full | `--full` | Default + Planning Consistency, Config Drift | <15s |
| Focused KB | `--focus kb` | KB Integrity only | <3s |
| Focused Planning | `--focus planning` | Planning Consistency only | <3s |

**Flags:**
- `--full` -- Run all check categories including full-tier checks
- `--focus kb` -- Run only KB Integrity checks
- `--focus planning` -- Run only Planning Consistency checks
- `--fix` -- Enable repair mode (auto in YOLO, prompt in interactive)
- `--stale-days N` -- Override configured staleness threshold (default: 7 days)

## 2. Check Categories

### 2.1 KB Integrity (Default Tier)

Validates the knowledge base at `./.claude/gsd-knowledge/` is structurally sound.

| # | Check | Pass Condition | Fail Severity |
|---|-------|----------------|---------------|
| KB-01 | Index file exists | `./.claude/gsd-knowledge/index.md` exists | FAIL |
| KB-02 | Index is parseable | Index contains `## Signals`, `## Spikes`, `## Lessons` table headers | FAIL |
| KB-03 | Signal count matches | Index entries match filesystem files (non-archived) | WARNING |
| KB-04 | Spike count matches | Index entries match filesystem files (non-archived) | WARNING |
| KB-05 | Lesson count matches | Index entries match filesystem files (non-archived) | WARNING |
| KB-06 | No frontmatter errors | 5 random entry files parse without YAML errors | WARNING |

**Shell patterns for KB checks:**

```bash
KB_DIR="$HOME/.claude/gsd-knowledge"
INDEX="$KB_DIR/index.md"

# KB-01: Index exists
test -f "$INDEX" && echo "PASS" || echo "FAIL"

# KB-02: Index parseable (has required section headers)
grep -q "## Signals" "$INDEX" && grep -q "## Spikes" "$INDEX" && grep -q "## Lessons" "$INDEX" && echo "PASS" || echo "FAIL"

# KB-03: Signal count match
index_signals=$(grep -c "^| sig-" "$INDEX" 2>/dev/null || echo "0")
actual_signals=0
while IFS= read -r -d '' file; do
  status=$(grep "^status:" "$file" 2>/dev/null | head -1 | sed 's/^status:[[:space:]]*//')
  [ "$status" != "archived" ] && actual_signals=$((actual_signals + 1))
done < <(find "$KB_DIR/signals" -name '*.md' -print0 2>/dev/null)
[ "$index_signals" -eq "$actual_signals" ] && echo "PASS: $index_signals indexed, $actual_signals on disk" || echo "WARNING: $index_signals indexed, $actual_signals on disk"

# KB-04: Spike count match
index_spikes=$(grep -c "^| spk-" "$INDEX" 2>/dev/null || echo "0")
actual_spikes=0
while IFS= read -r -d '' file; do
  status=$(grep "^status:" "$file" 2>/dev/null | head -1 | sed 's/^status:[[:space:]]*//')
  [ "$status" != "archived" ] && actual_spikes=$((actual_spikes + 1))
done < <(find "$KB_DIR/spikes" -name '*.md' -print0 2>/dev/null)
[ "$index_spikes" -eq "$actual_spikes" ] && echo "PASS: $index_spikes indexed, $actual_spikes on disk" || echo "WARNING: $index_spikes indexed, $actual_spikes on disk"

# KB-05: Lesson count match
index_lessons=$(grep -c "^| les-" "$INDEX" 2>/dev/null || echo "0")
actual_lessons=0
while IFS= read -r -d '' file; do
  status=$(grep "^status:" "$file" 2>/dev/null | head -1 | sed 's/^status:[[:space:]]*//')
  [ "$status" != "archived" ] && actual_lessons=$((actual_lessons + 1))
done < <(find "$KB_DIR/lessons" -name '*.md' -print0 2>/dev/null)
[ "$index_lessons" -eq "$actual_lessons" ] && echo "PASS: $index_lessons indexed, $actual_lessons on disk" || echo "WARNING: $index_lessons indexed, $actual_lessons on disk"

# KB-06: Frontmatter parse check (sample 5 random files)
errors=0
while IFS= read -r file; do
  # Check that frontmatter delimiters exist (--- ... ---)
  head_lines=$(head -20 "$file" 2>/dev/null)
  first_line=$(echo "$head_lines" | head -1)
  if [ "$first_line" != "---" ]; then
    errors=$((errors + 1))
  fi
done < <(find "$KB_DIR" -name '*.md' ! -name 'index.md' -print 2>/dev/null | shuf -n 5 2>/dev/null || find "$KB_DIR" -name '*.md' ! -name 'index.md' -print 2>/dev/null | head -5)
[ "$errors" -eq 0 ] && echo "PASS: No frontmatter errors in sampled files" || echo "WARNING: $errors files with frontmatter issues"
```

**Edge case:** If `./.claude/gsd-knowledge/` directory does not exist at all, KB-01 through KB-06 all FAIL. Report as "KB not initialized" and suggest user runs initialization.

### 2.2 Config Validity (Default Tier)

Validates `.planning/config.json` structure and required fields.

| # | Check | Pass Condition | Fail Severity |
|---|-------|----------------|---------------|
| CFG-01 | Config file exists | `.planning/config.json` exists | FAIL |
| CFG-02 | JSON is parseable | `node -e "JSON.parse(...)"` succeeds | FAIL |
| CFG-03 | Required fields present | `mode` and `depth` fields exist | FAIL |
| CFG-04 | Field values valid | `mode` is `yolo\|interactive`, `depth` is `quick\|standard\|comprehensive` | WARNING |
| CFG-05 | Version tracking exists | `gsd_reflect_version` field exists | WARNING |
| CFG-06 | Health check config exists | `health_check` section exists | WARNING |

**Shell patterns for config checks:**

```bash
CONFIG=".planning/config.json"

# CFG-01: Config exists
test -f "$CONFIG" && echo "PASS" || echo "FAIL"

# CFG-02: JSON parseable
node -e "JSON.parse(require('fs').readFileSync('$CONFIG','utf8'))" 2>/dev/null && echo "PASS" || echo "FAIL"

# CFG-03: Required fields
for field in mode depth; do
  node -e "const c=JSON.parse(require('fs').readFileSync('$CONFIG','utf8')); if(!c.$field) process.exit(1)" 2>/dev/null && echo "PASS: $field present" || echo "FAIL: $field missing"
done

# CFG-04: Field values valid
MODE=$(node -e "const c=JSON.parse(require('fs').readFileSync('$CONFIG','utf8')); console.log(c.mode||'')" 2>/dev/null)
DEPTH=$(node -e "const c=JSON.parse(require('fs').readFileSync('$CONFIG','utf8')); console.log(c.depth||'')" 2>/dev/null)
echo "$MODE" | grep -qE "^(yolo|interactive)$" && echo "PASS: mode=$MODE" || echo "WARNING: mode=$MODE is not yolo|interactive"
echo "$DEPTH" | grep -qE "^(quick|standard|comprehensive)$" && echo "PASS: depth=$DEPTH" || echo "WARNING: depth=$DEPTH is not quick|standard|comprehensive"

# CFG-05: Version tracking
node -e "const c=JSON.parse(require('fs').readFileSync('$CONFIG','utf8')); if(!c.gsd_reflect_version) process.exit(1)" 2>/dev/null && echo "PASS" || echo "WARNING: Missing gsd_reflect_version (pre-version-tracking project)"

# CFG-06: Health check config
node -e "const c=JSON.parse(require('fs').readFileSync('$CONFIG','utf8')); if(!c.health_check) process.exit(1)" 2>/dev/null && echo "PASS" || echo "WARNING: Missing health_check section (use --fix to add defaults)"
```

**Edge case:** If `.planning/config.json` does not exist, CFG-01 FAILs and CFG-02 through CFG-06 are skipped. Report "No config found -- run `/gsd:new-project` to initialize."

### 2.3 Stale Artifacts (Default Tier)

Detects orphaned, abandoned, or incomplete workspace artifacts.

| # | Check | Detection Rule | Fail Severity |
|---|-------|---------------|---------------|
| STALE-01 | Orphaned .continue-here files | `.continue-here.md` files older than threshold | WARNING |
| STALE-02 | Abandoned debug sessions | Files in `.planning/debug/` without `status:.*resolved`, older than threshold | WARNING |
| STALE-03 | Incomplete spikes | Directories in `.planning/spikes/` with `DESIGN.md` but no `DECISION.md` | WARNING |

**Staleness threshold:** Configurable via `health_check.stale_threshold_days` in config.json (default: 7 days). Override with `--stale-days N` flag.

**Shell patterns for stale artifact detection:**

```bash
STALE_THRESHOLD_DAYS=${STALE_DAYS_FLAG:-${CONFIG_STALE_THRESHOLD:-7}}

# STALE-01: Orphaned .continue-here files
stale_continue=0
while IFS= read -r file; do
  stale_continue=$((stale_continue + 1))
  age_days=$(( ($(date +%s) - $(stat -f %m "$file" 2>/dev/null || stat -c %Y "$file" 2>/dev/null || echo "0")) / 86400 ))
  echo "  - $file (${age_days} days old)"
done < <(find .planning/phases -name '.continue-here.md' -mtime +$STALE_THRESHOLD_DAYS 2>/dev/null)
[ "$stale_continue" -eq 0 ] && echo "PASS: No orphaned .continue-here files" || echo "WARNING: $stale_continue orphaned .continue-here files"

# STALE-02: Abandoned debug sessions
stale_debug=0
while IFS= read -r file; do
  if ! grep -q "status:.*resolved" "$file" 2>/dev/null; then
    stale_debug=$((stale_debug + 1))
    echo "  - $file (no resolution marker)"
  fi
done < <(find .planning/debug -name '*.md' -mtime +$STALE_THRESHOLD_DAYS 2>/dev/null)
[ "$stale_debug" -eq 0 ] && echo "PASS: No abandoned debug sessions" || echo "WARNING: $stale_debug abandoned debug sessions"

# STALE-03: Incomplete spikes
incomplete_spikes=0
while IFS= read -r file; do
  dir=$(dirname "$file")
  if [ ! -f "$dir/DECISION.md" ]; then
    incomplete_spikes=$((incomplete_spikes + 1))
    echo "  - $dir (DESIGN.md present, no DECISION.md)"
  fi
done < <(find .planning/spikes -name 'DESIGN.md' 2>/dev/null)
[ "$incomplete_spikes" -eq 0 ] && echo "PASS: No incomplete spikes" || echo "WARNING: $incomplete_spikes incomplete spikes"
```

### 2.4 Planning Consistency (Full Tier)

Validates planning artifact consistency across the project. Only runs with `--full` or `--focus planning`.

| # | Check | Pass Condition | Fail Severity |
|---|-------|----------------|---------------|
| PLAN-01 | Phase directories exist | Every phase in ROADMAP.md has a directory in `.planning/phases/` | WARNING |
| PLAN-02 | Completed plans have summaries | Every PLAN.md has a SUMMARY.md for completed phases | WARNING |
| PLAN-03 | STATE.md exists | `.planning/STATE.md` file exists and has "Current Position" section | FAIL |

**Shell patterns:**

```bash
# PLAN-01: Phase directories match ROADMAP.md
# Extract phase numbers from ROADMAP.md, check each has a directory
grep -oE "Phase [0-9]+" .planning/ROADMAP.md 2>/dev/null | sort -u | while read -r line; do
  phase_num=$(echo "$line" | grep -oE "[0-9]+")
  padded=$(printf "%02d" "$phase_num")
  dir_match=$(ls -d .planning/phases/${padded}-* 2>/dev/null | head -1)
  [ -n "$dir_match" ] && echo "PASS: Phase $phase_num -> $dir_match" || echo "WARNING: Phase $phase_num has no directory"
done

# PLAN-02: Completed plans have summaries
find .planning/phases -name '*-PLAN.md' 2>/dev/null | while read -r plan; do
  summary="${plan/PLAN.md/SUMMARY.md}"
  # Only check if the phase appears completed (has at least one SUMMARY.md in directory)
  dir=$(dirname "$plan")
  has_any_summary=$(ls "$dir"/*-SUMMARY.md 2>/dev/null | head -1)
  if [ -n "$has_any_summary" ]; then
    [ -f "$summary" ] && echo "PASS: $plan has summary" || echo "WARNING: $plan missing summary (phase has other summaries)"
  fi
done

# PLAN-03: STATE.md exists
test -f .planning/STATE.md && grep -q "Current Position" .planning/STATE.md && echo "PASS" || echo "FAIL: STATE.md missing or malformed"
```

### 2.5 Config Drift (Full Tier)

Detects when a project config is behind the current template. Only runs with `--full`.

| # | Check | Pass Condition | Fail Severity |
|---|-------|----------------|---------------|
| DRIFT-01 | Template field coverage | All fields in config template exist in project config | WARNING |
| DRIFT-02 | Version compatibility | `gsd_reflect_version` in config matches installed VERSION | WARNING |

**Shell patterns:**

```bash
TEMPLATE="$HOME/.claude/get-shit-done/templates/config.json"
CONFIG=".planning/config.json"

# DRIFT-01: Template field coverage
if [ -f "$TEMPLATE" ] && [ -f "$CONFIG" ]; then
  template_fields=$(node -e "const t=JSON.parse(require('fs').readFileSync('$TEMPLATE','utf8')); console.log(Object.keys(t).sort().join('\n'))" 2>/dev/null)
  config_fields=$(node -e "const c=JSON.parse(require('fs').readFileSync('$CONFIG','utf8')); console.log(Object.keys(c).sort().join('\n'))" 2>/dev/null)
  missing=$(comm -23 <(echo "$template_fields") <(echo "$config_fields") 2>/dev/null)
  [ -z "$missing" ] && echo "PASS: All template fields present" || echo "WARNING: Missing fields from template: $missing"
fi

# DRIFT-02: Version compatibility
INSTALLED=$(cat "$HOME/.claude/get-shit-done/VERSION" 2>/dev/null || echo "unknown")
PROJECT=$(node -e "const c=JSON.parse(require('fs').readFileSync('$CONFIG','utf8')); console.log(c.gsd_reflect_version||'none')" 2>/dev/null)
[ "$INSTALLED" = "$PROJECT" ] && echo "PASS: Version $INSTALLED matches" || echo "WARNING: Installed $INSTALLED vs project $PROJECT"
```

## 3. Focused Modes

Focused modes run a single check category, regardless of its tier.

**`--focus kb`:**
- Runs only KB Integrity checks (KB-01 through KB-06)
- Useful for quick validation before knowledge surfacing operations
- Skips all other categories

**`--focus planning`:**
- Runs only Planning Consistency checks (PLAN-01 through PLAN-03)
- Implies full-tier scope for that category (planning checks are normally full-tier only)
- Useful for validating planning artifacts before phase execution

**Flag precedence:**
- `--focus` takes priority over `--full`
- `--focus kb --full` is the same as `--focus kb` (focus overrides full)
- `--focus` and `--fix` are compatible (repairs run within the focused category)

## 4. Output Format

Health check results use a hybrid categorized checklist format.

```markdown
## Workspace Health Report
**Project:** {project-name} | **Version:** {gsd_reflect_version|unknown} | **Date:** {YYYY-MM-DD}

### KB Integrity [{PASS|WARNING|FAIL}]
- [x] Index exists and is parseable ({N} entries)
- [x] Signal count matches: {N} indexed, {N} on disk
- [x] Spike count matches: {N} indexed, {N} on disk
- [x] Lesson count matches: {N} indexed, {N} on disk
- [x] No frontmatter parse errors in sampled files

### Config Validity [{PASS|WARNING|FAIL}]
- [x] config.json exists and is valid JSON
- [x] Required fields present (mode, depth)
- [x] Field values valid (mode={value}, depth={value})
- [ ] Missing gsd_reflect_version (use --fix to set)
- [ ] Missing health_check section (use --fix to add defaults)

### Stale Artifacts [{PASS|WARNING|FAIL}]
- [x] No orphaned .continue-here files
- [ ] 1 abandoned debug session
  - .planning/debug/auth-loop.md (no resolution, 21 days old)
- [x] No incomplete spikes

### Summary
**{N} checks passed** | **{M} warnings** | **{K} failures**
```

**Category status rules:**
- **PASS** -- All checks in category passed
- **WARNING** -- At least one WARNING, no FAILs
- **FAIL** -- At least one FAIL in category

**Remediation hints:** Failed or warned checks include a brief hint in parentheses. Repairable issues include "(use --fix to repair)" suffix.

**Final summary line:** Aggregated counts across all categories. If warnings or failures exist, append: `Run /gsd:health-check --fix to auto-repair.`

## 5. Repair Rules

The `--fix` flag enables repair mode for repairable issues.

**Autonomy behavior:**
- **YOLO mode:** Auto-repair without prompting. Report what was fixed.
- **Interactive mode:** Ask before each repair using AskUserQuestion. User can approve, skip, or abort.

### Repairable Issues

| Issue | Repair Action | Risk |
|-------|--------------|------|
| KB index mismatch (KB-03/04/05) | Run `kb-rebuild-index.sh` to regenerate index from files | None -- index is derived data |
| Missing `gsd_reflect_version` (CFG-05) | Set to installed VERSION value in config.json | None -- additive field |
| Missing `health_check` section (CFG-06) | Add default health_check config to config.json | None -- additive section |
| Missing config template fields (DRIFT-01) | Add missing fields with template defaults | Low -- additive fields with safe defaults |
| Orphaned `.continue-here` files (STALE-01) | Delete the stale files | Low -- files are past their useful life |

**Repair execution pattern:**

```bash
# Example: Add missing health_check section to config.json
node -e "
const fs = require('fs');
const config = JSON.parse(fs.readFileSync('.planning/config.json', 'utf8'));
if (!config.health_check) {
  config.health_check = {
    frequency: 'milestone-only',
    stale_threshold_days: 7,
    blocking_checks: false
  };
  fs.writeFileSync('.planning/config.json', JSON.stringify(config, null, 2) + '\n');
  console.log('Added health_check section with defaults');
}
"
```

### Non-Repairable Issues

These are reported but not auto-fixed. User action required.

| Issue | Why Not Repairable | User Action |
|-------|-------------------|-------------|
| Missing `.planning/config.json` (CFG-01) | Project not initialized | Run `/gsd:new-project` |
| Missing KB directory | KB infrastructure not set up | Run KB initialization |
| Abandoned debug sessions (STALE-02) | User must decide resolution | Review and resolve or delete manually |
| Incomplete spikes (STALE-03) | User must decide if spike is still needed | Complete the spike or remove it |
| Missing phase directories (PLAN-01) | May indicate ROADMAP.md is stale | Review ROADMAP.md alignment |
| Missing SUMMARY.md files (PLAN-02) | Plan may not have been executed yet | Execute the plan or mark as skipped |

## 6. Signal Integration

Health check findings can be persisted as signals to enable the reflection engine to detect recurring workspace issues.

**When to persist:**
- If findings include WARNING or FAIL results, persist a health-check signal
- If all checks PASS, log as trace (not persisted)

**Signal properties:**

| Field | Value |
|-------|-------|
| `type` | signal |
| `signal_type` | custom |
| `severity` | notable (warnings or failures found) |
| `polarity` | negative (issues found) or positive (clean report after previous issues) |
| `tags` | `workspace/health-check`, `workspace/{category}` (for each failing category) |
| `source` | auto |

**Signal body template:**

```markdown
## What Happened

Health check on {date} found {N} warnings and {K} failures.

Categories affected: {list of WARNING/FAIL categories}

## Context

Project: {project-name}
Mode: {default|full|focused}
Repair applied: {yes|no}

## Potential Cause

{Brief assessment based on findings -- e.g., "KB index drifted after manual file edits" or "Config predates health_check feature"}
```

**Autonomy behavior for signal persistence:**
- YOLO mode: auto-persist signal if findings exist
- Interactive mode: ask user if they want to persist the signal

## 7. Configuration

Health check behavior is controlled by these `config.json` fields:

```json
{
  "health_check": {
    "frequency": "milestone-only",
    "stale_threshold_days": 7,
    "blocking_checks": false
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `health_check.frequency` | enum | `milestone-only` | When health check runs automatically: `milestone-only` (at milestone boundaries), `on-resume` (when resuming a project), `every-phase` (before each phase), `explicit-only` (only when user runs command) |
| `health_check.stale_threshold_days` | number | `7` | Days before an artifact is considered stale. Overridden by `--stale-days` flag. |
| `health_check.blocking_checks` | boolean | `false` | If true, FAIL results block further operations until resolved. If false, FAILs are reported as warnings and execution continues. |

**Frequency behavior:**

| Frequency | When It Runs | Typical Use |
|-----------|-------------|-------------|
| `milestone-only` | At milestone completion boundaries | Default -- minimal overhead |
| `on-resume` | When resuming after a break (detected via session timestamp gap) | For users who want assurance after time away |
| `every-phase` | Before `/gsd:execute-phase` starts | For users who want continuous validation |
| `explicit-only` | Only when user runs `/gsd:health-check` | For minimal-overhead preference |

**Flag override:** `--stale-days N` overrides `health_check.stale_threshold_days` for a single invocation without changing the config.

---

*Reference version: 1.0.0*
*Created: 2026-02-09*
*Phase: 06-production-readiness*
