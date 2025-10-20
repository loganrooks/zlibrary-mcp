# ADR-006: Quality Pipeline Architecture for RAG Processing

**Status**: Accepted
**Date**: 2025-10-17
**Context**: Phase 2.2-2.5 - Garbled text detection, strikethrough identification, OCR recovery

---

## Context

The RAG pipeline processes scholarly philosophy texts (particularly Derrida, Heidegger) that may contain:
1. **Intentional deletions** (sous-rature/strikethrough) - philosophical content
2. **OCR failures** - technical corruption requiring recovery
3. **Mixed scenarios** - both in same document

**Challenge**: How to distinguish intentional philosophical markup from technical failures?

**Critical Requirement**: Must preserve sous-rature (philosophical content) while recovering OCR errors.

---

## Decision

### Sequential Waterfall Quality Pipeline

Implement a three-stage analysis pipeline that prioritizes visual markers over statistical detection:

```
Stage 1: Statistical Detection (Task 2.2)
   ↓ if garbled
Stage 2: Visual Analysis (Task 2.3)
   ├─ X-marks found → Flag 'sous_rature' → PRESERVE (stop)
   └─ No X-marks → Continue to Stage 3
   ↓
Stage 3: OCR Recovery (Task 2.4)
   ├─ High confidence (>0.8) → Attempt Tesseract recovery
   ├─ Success → Flag 'recovered', replace text
   ├─ Failure → Flag 'unrecoverable', keep original
   └─ Low confidence (<0.8) → Flag 'low_confidence', keep original
```

### Decision Logic

**When garbled text is detected**:
1. **Check for visual markers FIRST** (X-marks, strikethrough formatting)
   - If found → This is philosophical content (sous-rature)
   - Action: Preserve as-is, flag appropriately
   - Rationale: Visual markers indicate intentional deletion

2. **If no visual markers** → Analyze severity
   - Catastrophic (confidence >0.8) → Likely OCR failure → Attempt recovery
   - Moderate (confidence <0.8) → Ambiguous → Preserve original

3. **Conservative bias**: When uncertain, preserve original
   - Rationale: Better to have garbled text than destroy meaning
   - Philosophy: Sous-rature without X-marks is possible

---

## Rationale

### Why Sequential Waterfall (not parallel)?

**Performance**:
- Statistical detection: ~0.5ms (fast)
- X-mark detection: ~5ms (fast)
- Tesseract recovery: ~300ms (expensive!)

**Cost Analysis**:
```
Parallel approach:
  Both X-mark + Tesseract run → Always pay 300ms
  Savings: ~5ms in worst case
  Cost: 100x more expensive for strikethrough cases

Waterfall approach:
  X-mark → STOP if found → Typical: ~5.5ms
  Tesseract only if no markers → Worst: ~305ms
  Savings: 300ms for every strikethrough case
```

**Conclusion**: Waterfall saves ~300ms × (strikethrough frequency) in typical philosophy corpus.

### Why Visual Markers Trump Statistics?

**Philosophical accuracy** (primary concern):
- Sous-rature is intentional content, not corruption
- Attempting "recovery" would destroy philosophical meaning
- Example: Derrida's crossed-out "différance" is the content itself

**False positive cost**:
- Treating sous-rature as OCR error → Destroys content (catastrophic)
- Treating OCR error as sous-rature → Preserves garbled text (acceptable)

**Risk asymmetry**: Err on side of preservation.

### Why Not Document-Level Only?

**Localized failures**:
- 100-page PDF may have 1 damaged page
- Document-level check may pass (99% good)
- Per-region analysis catches localized issues

**Semantic granularity**:
- Need region-level quality metadata for RAG
- LLM can use quality scores for confidence
- Enables fine-grained quality filtering

---

## Consequences

### Positive

✅ **Preserves philosophical content** (sous-rature)
✅ **Recovers OCR failures** (when appropriate)
✅ **Performance optimized** (waterfall avoids expensive ops)
✅ **Explainable** (confidence scores, detailed flags)
✅ **Configurable** (strategies for different corpora)
✅ **Testable** (each stage isolated)

### Negative

⚠️ **Complexity**: Three-stage pipeline
⚠️ **Maintenance**: Multiple modules to maintain
⚠️ **False negatives**: Sous-rature without markers may trigger recovery
⚠️ **Tuning required**: Thresholds may need corpus-specific adjustment

### Mitigations

- **Complexity**: Clear interfaces, comprehensive documentation
- **Maintenance**: High test coverage (>90%), clear module boundaries
- **False negatives**: Conservative recovery (high threshold), comparison checks
- **Tuning**: Configuration profiles (philosophy/technical/hybrid)

---

## Implementation

### Modules Created

1. **`lib/garbled_text_detection.py`** (Stage 1)
   - Statistical analysis (entropy, symbol density, repetition)
   - Configuration system
   - Backward-compatible API

2. **`lib/strikethrough_detection.py`** (Stage 2) - Upcoming Task 2.3
   - X-mark pattern matching
   - Visual line detection
   - PyMuPDF formatting analysis

3. **`lib/ocr_recovery.py`** (Stage 3) - Upcoming Task 2.4
   - Tesseract region recovery
   - Quality comparison
   - Fallback handling

### Data Model Enhancements

**PageRegion** (lib/rag_data_models.py):
```python
quality_flags: Optional[Set[str]] = None  # Detection/classification/remediation flags
quality_score: Optional[float] = None     # 0.0-1.0 quality metric

# Helper methods
def has_quality_issues() -> bool
def is_garbled() -> bool
def is_strikethrough() -> bool
def was_recovered() -> bool
def get_quality_summary() -> str
```

### Configuration

```python
# Feature flags (environment variables)
RAG_DETECT_GARBLED = 'true'          # Enable statistical detection
RAG_DETECT_STRIKETHROUGH = 'true'    # Enable X-mark detection
RAG_ENABLE_OCR_RECOVERY = 'true'     # Enable Tesseract recovery

# Strategy selection
RAG_QUALITY_STRATEGY = 'hybrid'      # 'philosophy' | 'technical' | 'hybrid'
```

**Strategies**:
- `philosophy`: Prioritize preservation, high recovery threshold (0.9)
- `technical`: Prioritize recovery, lower threshold (0.6)
- `hybrid` (default): Balanced approach (0.75)

---

## Testing

### Test Coverage

- Unit tests: 40 tests (garbled detection)
- Integration tests: 12 tests (Phase 2.1)
- Performance tests: 12 tests (benchmarks)
- Backward compatibility: 6 tests
- Total: **70+ tests** for quality pipeline

### Performance Validation

- ✅ Single region: 0.455ms (target: <1ms) - **54% under target**
- ✅ Full page: <23ms (target: <100ms) - **77% under target**
- ✅ Linear scaling confirmed
- ✅ Memory efficient (<1KB per result)

---

## Alternatives Considered

### Alternative 1: Parallel X-mark + Tesseract

**Rejected because**:
- Only saves ~5ms in worst case
- 100x more expensive for strikethrough cases (wasted CPU)
- No significant benefit

### Alternative 2: Always Attempt Recovery

**Rejected because**:
- Would destroy sous-rature content
- False positives catastrophic for philosophy texts
- No way to distinguish intentional from accidental

### Alternative 3: LLM-Based Classification

**Rejected because**:
- Too expensive (API costs)
- Too slow (hundreds of ms per region)
- Less reliable than visual markers
- Overkill for this problem

### Alternative 4: Document-Level Only

**Rejected because**:
- Misses localized failures
- No region-level quality metadata for RAG
- Can't handle mixed scenarios (good + damaged pages)

---

## References

- Phase 1.5-1.7 Validation: 86-93% F1 score for statistical detection
- X-mark Detection: 100% recall on 4 ground truth instances
- Tesseract Recovery: 100% accuracy on corruption samples

---

## Future Enhancements

1. **Machine Learning Classification**
   - Train classifier: strikethrough vs OCR error
   - Features: visual patterns, text characteristics, context
   - Would require labeled training data

2. **Confidence Calibration**
   - Validate confidence scores against ground truth
   - Adjust scoring formulas based on empirical data
   - Track precision/recall by confidence band

3. **Adaptive Thresholds**
   - Learn optimal thresholds per corpus
   - Auto-tune based on feedback
   - Per-author or per-book customization

4. **Quality Prediction**
   - Predict quality before extraction
   - Skip low-quality regions
   - Prioritize high-quality content for RAG

---

## Review and Updates

- **2025-10-17**: Initial decision (Phase 2.2 completion)
- **Next review**: After Phase 2.5 completion (full integration)
