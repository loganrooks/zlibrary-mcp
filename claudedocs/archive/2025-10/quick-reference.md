# Quick Reference: Documentation Guide

**Last Updated**: 2025-10-21

## Where to Document

| I Need To... | Put It Here | Naming Convention |
|-------------|------------|-------------------|
| Save session summary | `claudedocs/session-notes/` | `YYYY-MM-DD-topic.md` |
| Document research findings | `claudedocs/research/{topic}/` | `{subtopic}-findings.md` |
| Write phase report | `claudedocs/phase-reports/phase-X/` | `{milestone}.md` |
| Analyze architecture | `claudedocs/architecture/` | `{component}-analysis.md` |
| Create technical spec | `docs/specifications/` | `{FEATURE}_SPEC.md` (SCREAMING_SNAKE) |
| Record architecture decision | `docs/adr/` | `ADR-NNN-Title-With-Hyphens.md` |
| Development workflow guide | `.claude/` | `{TOPIC}_WORKFLOW.md` (SCREAMING_SNAKE) |

## Naming Standards

### kebab-case (Preferred)
**Use for**: Session notes, research, architecture analysis, general documentation
**Examples**:
- `sous-rature-validation.md`
- `performance-optimization-findings.md`
- `phase-2-integration-complete.md`

### SCREAMING_SNAKE_CASE (Limited use)
**Use for**: Formal specifications, workflow guides in `.claude/`
**Examples**:
- `docs/specifications/SOUS_RATURE_RECOVERY_SPEC.md`
- `.claude/TDD_WORKFLOW.md`

### **DON'T USE**:
- ❌ `SCREAMING_CASE_IN_CLAUDEDOCS.md` - Reserved for specs only
- ❌ Redundant markers: `FINAL`, `COMPLETE`, `V2`, `UPDATED`
- ❌ Unclear names: `analysis.md`, `notes.md`, `report.md`

## Timestamp Guidelines

**Always timestamp**:
- Session summaries: `2025-10-21-session-summary.md`
- Research validations: `sous-rature-validation-2025-10-20.md`
- Phase reports: `phase-2-complete-2025-10-18.md`

**Never timestamp**:
- Living documents that get updated (use git history instead)
- Specifications (use version numbers)
- Workflow guides

## Document Lifecycle

```
CREATE → EDIT → [SUPERSEDE] → ARCHIVE

1. CREATE: Follow naming convention above
2. EDIT: Update in place (git tracks history)
3. SUPERSEDE: Add notice at top, link to replacement
4. ARCHIVE: Move to archive/YYYY-MM/ after 30 days
```

## Quick Actions

### Starting New Session
```bash
# 1. Check current documentation
cat claudedocs/README.md

# 2. Create session note
code claudedocs/session-notes/$(date +%Y-%m-%d)-{topic}.md
```

### Research Documentation
```bash
# 1. Create topic directory
mkdir -p claudedocs/research/{topic}

# 2. Create findings doc
code claudedocs/research/{topic}/findings.md

# 3. Update research INDEX
code claudedocs/research/INDEX.md
```

### Formal Specification
```bash
# 1. Create spec
code docs/specifications/{FEATURE}_SPEC.md

# 2. Update spec catalog
code docs/specifications/README.md
```

## Common Questions

**Q**: Where do I put this analysis I just wrote?
**A**: Is it:
- About a specific session? → `session-notes/`
- Research findings? → `research/{topic}/`
- Architecture analysis? → `architecture/`
- Formal spec? → `docs/specifications/`

**Q**: How do I know if something should be archived?
**A**:
- >30 days old AND superseded by newer doc? → Archive
- Still referenced/relevant? → Keep in current location
- Historical context only? → Archive with clear README

**Q**: What if I don't know where it belongs?
**A**: Default to `claudedocs/session-notes/` with date, then we can move it later

## Navigation

- **Master Map**: [DOCUMENTATION_MAP.md](../DOCUMENTATION_MAP.md)
- **ADR Index**: [docs/adr/README.md](../docs/adr/README.md)
- **Spec Catalog**: [docs/specifications/README.md](../docs/specifications/README.md)
- **Full Audit**: [DOCUMENTATION_AUDIT_AND_REORGANIZATION_PLAN.md](DOCUMENTATION_AUDIT_AND_REORGANIZATION_PLAN.md)

---

**Pro Tip**: Bookmark `/DOCUMENTATION_MAP.md` - it's your entry point for everything!
