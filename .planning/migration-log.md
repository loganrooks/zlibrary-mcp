# Migration Log

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
