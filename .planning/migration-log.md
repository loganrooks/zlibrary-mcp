# Migration Log

## 1.13.0 -> 1.19.4 (2026-04-16T19:08:49.982Z)

### Changes Applied
- Added `health_check.workflow_thresholds`: {"low":2,"high":5}
- Added `health_check.resolution_ratio_threshold`: 5
- Added `health_check.reactive_threshold`: "RED"
- Added `health_check.cache_staleness_hours`: 24
- Added `release` section (version_file, changelog, changelog_format, ci_trigger, registry, branch)
- Added `signal_lifecycle` section (lifecycle_strictness, manual_signal_trust, rigor_enforcement, severity_conflict_handling, recurrence_escalation, verification_window)
- Added `signal_collection` section (sensors, synthesizer_model, per_phase_cap, auto_collect, reentrancy)
- Added `spike` section (enabled, sensitivity, auto_trigger)
- Added `automation.level`: 1
- Added `automation.overrides`: {}
- Added `automation.context_threshold_pct`: 60
- Added `automation.stats`: {}
- Updated manifest_version: null -> 2

---

Tracks version upgrades applied to this project.

## 0.0.0 -> 1.13.0 (2026-02-11T00:00:00Z)

### Changes Applied
- Added `health_check` section to config.json (frequency: milestone-only, stale_threshold_days: 7, blocking_checks: false)
- Added `devops` section to config.json (ci_provider: none, deploy_target: none, commit_convention: freeform, environments: [])
- Added `gsd_reflect_version: "1.13.0"` to config.json

### User Choices
- Health check frequency: milestone-only (default, YOLO mode)
- Health check blocking: false (default, YOLO mode)
- DevOps context: skipped (defaults applied, YOLO mode)

---

*Log is append-only. Each migration is recorded when applied.*
