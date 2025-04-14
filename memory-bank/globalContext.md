# Global Context

## Product Context
<!-- High-level goals, user stories, constraints -->

## System Patterns
<!-- Architecture diagrams, key components, data flow -->

## Decision Log
<!-- Key decisions, rationale, timestamps -->

## Progress
<!-- Major milestones, completed tasks -->
#### [2025-04-12 22:39:57 UTC] - Decision: Primitive vs. Non-Primitive Memory Scripts
- **Context:** Workspace analysis identified separate memory scripts (`scripts/primitive/*.py` vs `scripts/*.py`).
- **Decision:** Maintain separate primitive memory scripts (`.roo/scripts/primitive/`) exclusively for core system modes (`system-modifier`, `system-strategist`) and non-primitive scripts (`.roo/scripts/`) for standard modes.
- **Justification:** Safety measure to prevent `system-modifier` from modifying its own critical memory access dependencies during plan execution, reducing risk of system instability.
- **Alternatives Considered:** Using a single set of scripts (rejected due to self-modification risk).
---
