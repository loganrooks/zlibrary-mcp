# Project Roadmap

**Last Updated**: 2025-10-21
**Current Phase**: Phase 2 - RAG Pipeline Quality & Robustness

---

## Active Sprint (Current Week - Oct 21-27)

### Completed This Week ✅
- [x] Validate sous-rature detection with real PDFs ([5763acf](../commit/5763acf))
- [x] Implement formatting preservation with span grouping ([137fa07](../commit/137fa07))
- [x] Reorganize workspace documentation (kebab-case, hierarchical) ([2880d3d](../commit/2880d3d))
- [x] Clean up root directory - essential entry points only ([3831970](../commit/3831970))

### In Progress 🔄
- [ ] Update ISSUES.md with Phase 2 completion status
- [ ] Implement session state management system (ROADMAP, ARCHITECTURE, Serena integration)

### This Week's Focus
**Primary Goal**: Establish sustainable development workflow with clear visibility

**Current Task**: System-level improvements to prevent workspace disorganization
**Status**: Implementing three-layer visibility (Strategic/Structural/Tactical)

---

## Next 1-2 Weeks (Oct 28 - Nov 10)

### Phase 2 Features (RAG Pipeline)
- [ ] Marginalia integration (Stage 4) - Module exists, needs integration
- [ ] Citation extraction (Stage 5) - Design complete, ready for implementation
- [ ] Footnote linking (Stage 6) - Data model ready, matching logic needed
- [ ] Format application testing - Validate bold/italic/strikethrough with diverse PDFs

### Quality & Performance
- [ ] Performance budget enforcement automation
- [ ] Real PDF test corpus expansion (acquire 3-5 more test PDFs)
- [ ] Regression test suite enhancement

### Development Experience
- [ ] Pre-commit hooks for quality validation
- [ ] Session lifecycle automation (/sc:load, /sc:save)
- [ ] Documentation archival automation (>30 days → archive/)

---

## 2-4 Weeks (Nov 11 - Dec 1)

### Advanced Features
- [ ] ML-based text recovery research (sous-rature under X-marks)
  - Image inpainting model exploration
  - NLP-based word prediction
  - Dataset creation for training

- [ ] Multi-column layout detection
- [ ] Adaptive resolution pipeline (72→150→300 DPI escalation)
- [ ] Selective OCR strategy implementation

### Infrastructure
- [ ] Batch download queue management ([DL-001](../ISSUES.md))
- [ ] Circuit breaker refinement ([ISSUE-005](../ISSUES.md))
- [ ] Advanced search filters ([SRCH-001](../ISSUES.md))
- [ ] Caching layer for search results

---

## Completed Recently (Archive)

### Week of Oct 14-20
- ✅ TDD workflow establishment with ground truth validation
- ✅ Fast X-mark pre-filter (31× speedup on detection)
- ✅ Stage 2 independence correction (architectural fix)
- ✅ Parallel detection with caching (40× combined speedup)

### Week of Oct 7-13
- ✅ Phase 1 completion (enhanced data model)
- ✅ PyMuPDF flag mapping corrections
- ✅ UV migration for Python dependencies (v2.0.0)
- ✅ Code simplification (77% reduction in venv-manager)

---

## Blockers & Dependencies

**Current Blockers**: None

**External Dependencies**:
- Waiting on: None
- Monitoring: Z-Library API stability (ongoing)

---

## Strategic Priorities

1. **Quality First**: TDD with real PDFs before features
2. **Performance Budgets**: Hard constraints, must stay within limits
3. **Documentation**: Keep workspace organized, prevent chaos
4. **Incremental Value**: Ship working features progressively

---

## Notes

- All RAG features require real PDF validation per `.claude/TDD_WORKFLOW.md`
- Performance budgets defined in `test_files/performance_budgets.json` are hard constraints
- Workspace organization standards documented in `CLAUDE.md` - follow strictly
- Session state visibility via this ROADMAP + `.claude/ARCHITECTURE.md` + Serena memory

---

**Quick Links**:
- [Current Issues](../ISSUES.md) - Detailed issue tracking
- [Architecture Overview](ARCHITECTURE.md) - System structure
- [TDD Workflow](TDD_WORKFLOW.md) - Development process
- [Patterns](PATTERNS.md) - Code patterns to follow
