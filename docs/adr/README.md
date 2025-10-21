# Architecture Decision Records (ADR) Index

**Purpose**: Index of all architecture decisions for the Z-Library MCP server
**Format**: ADR template follows [MADR](https://adr.github.io/madr/) lightweight format
**Status**: 7 ADRs recorded (ADR-005 missing - under investigation)

---

## Quick Reference by Topic

### Python Bridge & Integration
- **[ADR-004](ADR-004-Python-Bridge-Path-Resolution.md)**: Python Bridge Path Resolution ⭐

### Z-Library API Integration
- **[ADR-002](ADR-002-Download-Workflow-Redesign.md)**: Download Workflow Redesign ⭐
- **[ADR-003](ADR-003-Handle-ID-Lookup-Failure.md)**: Handle ID Lookup Failure ⭐

### RAG Pipeline & Quality
- **[ADR-006](ADR-006-Quality-Pipeline-Architecture.md)**: Quality Pipeline Architecture ⭐
- **[ADR-007](ADR-007-Phase-2-Integration-Complete.md)**: Phase 2 Integration Complete
- **[ADR-008](ADR-008-Stage-2-Independence-Correction.md)**: Stage 2 Independence Correction

### Testing & Infrastructure
- **[ADR-001](ADR-001-Jest-ESM-Migration.md)**: Jest ESM Migration

---

## All ADRs (Chronological)

### ADR-001: Jest ESM Migration
**Status**: ✅ Accepted
**Date**: 2024-04-13
**Context**: Need to test ES modules in Node.js/TypeScript codebase
**Decision**: Migrate Jest configuration to support ESM with `node --experimental-vm-modules`
**Consequences**:
- ✅ Can test ES module imports/exports
- ⚠️ Requires experimental Node.js flag
- ✅ Better alignment with modern JavaScript ecosystem

**Related**:
- Implementation: `jest.config.js`
- Documentation: Testing section in README.md

---

### ADR-002: Download Workflow Redesign
**Status**: ✅ Accepted
**Date**: 2024-04-15
**Context**: Direct book ID downloads failing due to Z-Library API limitations
**Decision**: Use `bookDetails` object from search results instead of direct ID lookup
**Consequences**:
- ✅ More reliable downloads (uses complete book metadata)
- ✅ Avoids unreliable ID-based detail page scraping
- ⚠️ Requires search step before download
- ✅ Better error messages and debugging

**Key Insight**: Z-Library's EAPI doesn't provide stable ID-based downloads; always search first

**Related**:
- [ADR-003](ADR-003-Handle-ID-Lookup-Failure.md) - ID lookup deprecation
- Implementation: `src/lib/zlibrary-api.ts`, `lib/python_bridge.py`
- Documentation: [docs/ZLIBRARY_TECHNICAL_IMPLEMENTATION.md](../ZLIBRARY_TECHNICAL_IMPLEMENTATION.md)

---

### ADR-003: Handle ID Lookup Failure
**Status**: ✅ Accepted (Deprecation)
**Date**: 2024-04-15
**Context**: `get_book_by_id()` unreliable due to Z-Library HTML structure changes
**Decision**: Deprecate ID lookup, always use search-first approach
**Consequences**:
- ✅ More reliable workflow
- ❌ No direct ID-based retrieval (must search first)
- ✅ Simpler codebase (removed fragile scraping logic)

**Deprecation Notice**: `get_book_by_id()` marked deprecated, will be removed in v3.0

**Related**:
- [ADR-002](ADR-002-Download-Workflow-Redesign.md) - Download workflow redesign
- Implementation: `lib/python_bridge.py` (deprecated function)
- Migration Guide: See comments in deprecated function

---

### ADR-004: Python Bridge Path Resolution
**Status**: ✅ Accepted
**Date**: 2024-04-16
**Context**: Need reliable path resolution for Python scripts from compiled TypeScript
**Decision**: Keep Python scripts in source `lib/` directory, resolve paths at runtime
**Consequences**:
- ✅ Single source of truth (no file duplication)
- ✅ Development-friendly (edit Python directly)
- ✅ No build process changes needed
- ⚠️ Runtime path calculation required (`__dirname` + relative paths)

**Implementation Pattern**:
```typescript
// From dist/lib/python-bridge.js at runtime:
const scriptPath = path.resolve(__dirname, '..', '..', 'lib', 'python_bridge.py');
// Navigation: dist/lib/ → dist/ → project_root/ → lib/python_bridge.py
```

**Path Helper Module** (Recommended):
```typescript
import { getPythonScriptPath } from './lib/paths.js';
const scriptPath = getPythonScriptPath('python_bridge.py');
```

**Related**:
- Implementation: `src/lib/venv-manager.ts`, `src/lib/zlibrary-api.ts`, `src/lib/paths.ts`
- Documentation: [docs/DEPLOYMENT.md](../DEPLOYMENT.md) (edge cases)
- Validation: Build process validates Python files exist

---

### ADR-005: [MISSING]
**Status**: ⚠️ Investigation Needed
**Date**: Unknown
**Context**: Gap in ADR sequence
**Investigation**:
- Check git history for deleted ADR-005
- Determine if intentionally skipped or lost
- Update this index once resolved

**Action Items**:
- [ ] Search git history: `git log --all --full-history -- "*ADR-005*"`
- [ ] Check if number was skipped intentionally
- [ ] Document findings in this index

---

### ADR-006: Quality Pipeline Architecture for RAG Processing
**Status**: ✅ Accepted
**Date**: 2025-10-17
**Context**: Need to distinguish intentional philosophical markup (sous-rature) from OCR failures
**Decision**: Implement sequential waterfall quality pipeline (Statistical → Visual → OCR)
**Consequences**:
- ✅ Preserves philosophical content (strikethrough/X-marks)
- ✅ Recovers OCR failures appropriately
- ⚠️ Three-stage sequential pipeline (performance overhead)
- ✅ Clear decision boundaries (visual markers take precedence)

**Pipeline Architecture**:
```
Stage 1: Statistical Detection (garbled text metrics)
   ↓ if garbled
Stage 2: Visual Analysis (X-marks, strikethrough formatting)
   ├─ X-marks found → Flag 'sous_rature' → PRESERVE (stop)
   └─ No X-marks → Continue to Stage 3
   ↓
Stage 3: OCR Recovery (Tesseract re-processing)
   ├─ High confidence (>0.8) → Attempt recovery
   └─ Success → Replace text, flag 'recovered'
```

**Related**:
- [ADR-007](ADR-007-Phase-2-Integration-Complete.md) - Phase 2 integration
- Specifications: [docs/specifications/SELECTIVE_OCR_STRATEGY.md](../specifications/SELECTIVE_OCR_STRATEGY.md)
- Specifications: [docs/specifications/SOUS_RATURE_RECOVERY_STRATEGY.md](../specifications/SOUS_RATURE_RECOVERY_STRATEGY.md)
- Implementation: `lib/garbled_text_detection.py`, `lib/rag_processing.py`

---

### ADR-007: Phase 2 Integration Complete
**Status**: ✅ Accepted (Implementation Record)
**Date**: 2025-10-19
**Context**: Complete integration of Phase 2 quality pipeline into RAG processing
**Decision**: Integrate statistical detection, visual analysis, and OCR recovery into `process_pdf()`
**Consequences**:
- ✅ Quality pipeline active in production
- ✅ Backward compatible (feature flags)
- ✅ Performance validated (<100ms overhead)
- ✅ Real-world tested (Derrida, Heidegger PDFs)

**Integration Points**:
- `process_pdf()` → calls quality pipeline stages
- Feature flag: `RAG_USE_QUALITY_PIPELINE='true'` (default)
- Metrics: Performance budgets enforced (see `test_files/performance_budgets.json`)

**Related**:
- [ADR-006](ADR-006-Quality-Pipeline-Architecture.md) - Pipeline architecture
- [ADR-008](ADR-008-Stage-2-Independence-Correction.md) - Stage 2 correction
- Status Report: [claudedocs/PHASE_2_INTEGRATION_COMPLETE_2025_10_18.md](../../claudedocs/PHASE_2_INTEGRATION_COMPLETE_2025_10_18.md)
- Implementation: `lib/rag_processing.py`, `lib/garbled_text_detection.py`, `lib/strikethrough_detection.py`

---

### ADR-008: Stage 2 Independence Correction
**Status**: ✅ Accepted (Correction)
**Date**: 2025-10-19
**Context**: Stage 2 (Visual Analysis) incorrectly depended on Stage 1 (Statistical Detection) results
**Decision**: Make Stage 2 independent - always run visual analysis before OCR recovery
**Consequences**:
- ✅ Sous-rature preserved even if statistical detection misses it
- ✅ More robust visual marker detection
- ⚠️ Slight performance overhead (always checks visual markers)
- ✅ Aligns with ADR-006 design intent (visual markers take precedence)

**Original Problem**: Stage 2 skipped if Stage 1 didn't detect garbled text, risking X-mark loss

**Corrected Flow**:
```
Block-level processing
   ↓
ALWAYS run Stage 2: Visual Analysis (check X-marks/strikethrough)
   ├─ Visual markers found → Preserve (stop)
   └─ No visual markers → Continue
   ↓
IF garbled detected (Stage 1 OR custom threshold)
   → Stage 3: OCR Recovery
```

**Related**:
- [ADR-006](ADR-006-Quality-Pipeline-Architecture.md) - Original pipeline design
- [ADR-007](ADR-007-Phase-2-Integration-Complete.md) - Integration implementation
- Implementation: `lib/rag_processing.py::_analyze_pdf_block()`

---

## ADR Status Definitions

| Status | Meaning | Can Be Changed? |
|--------|---------|-----------------|
| ✅ Accepted | Decision made and implemented | No (supersede with new ADR) |
| 🟡 Proposed | Under discussion | Yes |
| ❌ Rejected | Decision not adopted | No (keep for historical record) |
| 🔄 Superseded | Replaced by newer ADR | No (keep for context) |
| ⚠️ Deprecated | Marked for removal/replacement | No (keep until removed) |

---

## How to Create a New ADR

### 1. Choose the Next Number
Current: ADR-008 (latest)
Next: ADR-009

### 2. Use the Template
```markdown
# ADR-NNN: Title in Title Case

**Status**: Proposed | Accepted | Rejected | Superseded
**Date**: YYYY-MM-DD
**Supersedes**: [ADR-XXX] (if applicable)

## Context
What is the problem we're trying to solve?
What are the forces at play?

## Decision
What did we decide to do and why?

## Consequences
Positive and negative outcomes of this decision:
- ✅ Positive consequence
- ⚠️ Trade-off or concern
- ❌ Negative consequence

## Alternatives Considered
What other options did we evaluate?

## Related
- Links to related ADRs
- Links to implementation files
- Links to specifications
```

### 3. File Naming Convention
`ADR-NNN-Title-In-Kebab-Case.md`

### 4. Update This Index
Add entry to:
- Chronological list
- Topic-based quick reference (if new category)

### 5. Link from Implementation
Add comment in code referencing the ADR:
```python
# Implementation of ADR-006: Quality Pipeline Architecture
def quality_pipeline():
    ...
```

---

## ADR Topics Covered

- [x] Testing Infrastructure (ADR-001)
- [x] Z-Library API Integration (ADR-002, ADR-003)
- [x] Python Bridge (ADR-004)
- [x] RAG Quality Pipeline (ADR-006, ADR-007, ADR-008)
- [ ] Performance Optimization (future)
- [ ] Caching Strategy (future)
- [ ] Error Handling Patterns (future)
- [ ] Deployment Architecture (future)

---

## Investigation Tasks

**ADR-005 Missing**:
- [ ] Search git history for deleted ADR-005
- [ ] Determine if intentionally skipped
- [ ] Document resolution in this index
- [ ] If truly missing, use ADR-009 for next decision (don't reuse ADR-005)

---

## Related Documentation

- Architecture Overview: [docs/architecture/](../architecture/)
- Technical Specifications: [docs/specifications/](../specifications/)
- Implementation Patterns: [.claude/PATTERNS.md](../../.claude/PATTERNS.md)
- Project Context: [.claude/PROJECT_CONTEXT.md](../../.claude/PROJECT_CONTEXT.md)

---

**Metadata**:
- Created: 2025-10-21
- Last Updated: 2025-10-21
- Total ADRs: 7 active + 1 missing (8 total numbers used)
- Next ADR Number: ADR-009
- Maintained by: Project contributors
