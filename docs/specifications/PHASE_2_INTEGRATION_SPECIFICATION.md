# Phase 2 Quality Pipeline Integration Specification

**Version**: 1.0
**Date**: 2025-10-18
**Status**: Draft
**Related**: ADR-006, PHASE_1_2_STATUS_REPORT_2025_10_18.md

---

## Overview

This specification defines how the three-stage sequential waterfall quality pipeline integrates into the existing RAG processing workflow in `lib/rag_processing.py`.

**Pipeline Stages**:
1. **Statistical Detection** (Phase 2.2) - Detect garbled text via entropy/symbol analysis
2. **Visual Analysis** (Phase 2.3) - Detect X-marks/strikethrough via opencv/LSD
3. **OCR Recovery** (Phase 2.4) - Selective Tesseract recovery for corrupted regions

**Integration Point**: `process_pdf()` function at page-level processing

---

## Architecture

### High-Level Flow

```
process_pdf(file_path) entry
  ↓
Open PDF with PyMuPDF
  ↓
FOR EACH PAGE:
  ├─ Extract text blocks with page.get_text("dict")
  ├─ FOR EACH BLOCK:
  │    ├─ Analyze structure with _analyze_pdf_block()
  │    ├─ Returns PageRegion object (if return_structured=True)
  │    ├─ **NEW: Apply Quality Pipeline** ← INTEGRATION POINT
  │    │    ├─ Stage 1: Statistical Detection
  │    │    ├─ Stage 2: Visual Analysis (if Stage 1 flagged)
  │    │    └─ Stage 3: OCR Recovery (if Stages 1-2 flagged)
  │    └─ Append processed PageRegion to results
  └─ Aggregate page content
  ↓
Format output (text/markdown)
  ↓
Return processed content
```

### Integration Architecture

```python
# NEW FUNCTION: Apply quality pipeline to PageRegion
def _apply_quality_pipeline(
    page_region: PageRegion,
    pdf_path: Path,
    page_num: int,
    config: QualityPipelineConfig
) -> PageRegion:
    """
    Apply sequential waterfall quality pipeline to a PageRegion.

    Stages:
    1. Statistical Detection - Analyze text for garbled patterns
    2. Visual Analysis - Check for X-marks/strikethrough (if garbled)
    3. OCR Recovery - Attempt Tesseract recovery (if garbled + no X-marks)

    Args:
        page_region: PageRegion object from _analyze_pdf_block()
        pdf_path: Path to PDF file for visual/OCR analysis
        page_num: Page number (0-indexed)
        config: Pipeline configuration (feature flags, thresholds)

    Returns:
        PageRegion with populated quality_flags and quality_score
    """
```

---

## Feature Flags

### Environment Variables

```python
# Feature toggle for entire quality pipeline
RAG_ENABLE_QUALITY_PIPELINE = os.getenv('RAG_ENABLE_QUALITY_PIPELINE', 'true').lower() == 'true'

# Individual stage toggles (allow partial pipeline for debugging/performance)
RAG_DETECT_GARBLED = os.getenv('RAG_DETECT_GARBLED', 'true').lower() == 'true'
RAG_DETECT_STRIKETHROUGH = os.getenv('RAG_DETECT_STRIKETHROUGH', 'true').lower() == 'true'
RAG_ENABLE_OCR_RECOVERY = os.getenv('RAG_ENABLE_OCR_RECOVERY', 'true').lower() == 'true'

# Strategy selection (philosophy/technical/hybrid)
RAG_QUALITY_STRATEGY = os.getenv('RAG_QUALITY_STRATEGY', 'hybrid')  # Default: balanced

# Performance tuning
RAG_QUALITY_BATCH_SIZE = int(os.getenv('RAG_QUALITY_BATCH_SIZE', '10'))  # Process N pages before applying pipeline
```

### Strategy Profiles

```python
STRATEGY_CONFIGS = {
    'philosophy': {
        'garbled_threshold': 0.9,        # Very conservative (preserve ambiguous text)
        'recovery_threshold': 0.95,       # Almost never auto-recover
        'enable_strikethrough': True,     # Always check for sous-rature
        'priority': 'preservation'        # Err on side of keeping original
    },
    'technical': {
        'garbled_threshold': 0.6,        # Aggressive detection
        'recovery_threshold': 0.7,       # More likely to recover
        'enable_strikethrough': False,   # Technical docs rarely have strikethrough
        'priority': 'quality'            # Err on side of recovery
    },
    'hybrid': {  # DEFAULT
        'garbled_threshold': 0.75,       # Balanced
        'recovery_threshold': 0.8,       # Moderate confidence required
        'enable_strikethrough': True,    # Check for visual markers
        'priority': 'balanced'           # Case-by-case decisions
    }
}
```

---

## Data Flow

### Stage 1: Statistical Detection

**When**: Always enabled if `RAG_DETECT_GARBLED=true`
**Input**: `page_region.get_full_text()` (concatenated span text)
**Processing**:

```python
from lib.garbled_text_detection import detect_garbled_text_enhanced, GarbledDetectionConfig

# Get strategy config
strategy = STRATEGY_CONFIGS.get(RAG_QUALITY_STRATEGY, STRATEGY_CONFIGS['hybrid'])

# Create detection config
garbled_config = GarbledDetectionConfig(
    symbol_density_threshold=0.25,
    repetition_threshold=0.7,
    entropy_threshold=strategy['garbled_threshold'],
    min_text_length=10
)

# Detect garbled text
full_text = page_region.get_full_text()
garbled_result = detect_garbled_text_enhanced(full_text, garbled_config)

# Populate quality metadata
if garbled_result.is_garbled:
    page_region.quality_flags = garbled_result.flags.copy()  # {'high_symbol_density', 'high_repetition'}
    page_region.quality_score = 1.0 - garbled_result.confidence  # Convert to quality score (1.0 = perfect)

    # Proceed to Stage 2
else:
    page_region.quality_flags = set()
    page_region.quality_score = 1.0  # Perfect quality
    # Skip Stages 2 and 3
```

**Output**: `page_region.quality_flags`, `page_region.quality_score` populated

---

### Stage 2: Visual Analysis (X-mark Detection)

**When**: Only if Stage 1 flagged as garbled AND `RAG_DETECT_STRIKETHROUGH=true`
**Input**: `pdf_path`, `page_num`, `page_region.bbox`
**Processing**:

```python
from lib.strikethrough_detection import detect_strikethrough, XMarkDetectionConfig

# Only run if garbled detected
if not page_region.is_garbled():
    return page_region  # Skip Stage 2

# Check if opencv available
if not XMARK_AVAILABLE:
    logging.warning("X-mark detection requested but opencv not available")
    return page_region  # Skip to Stage 3

# Configure X-mark detection
xmark_config = XMarkDetectionConfig(
    min_line_length=10,
    diagonal_tolerance=15,  # degrees from 45°
    proximity_threshold=5    # pixels
)

# Detect X-marks in page region
xmark_result = detect_strikethrough(pdf_path, page_num, page_region.bbox, xmark_config)

# If X-marks found, this is sous-rature (preserve!)
if xmark_result.has_xmarks:
    page_region.quality_flags.add('sous_rature')
    page_region.quality_flags.add('intentional_deletion')
    page_region.quality_score = 1.0  # Perfect quality (philosophical content)

    # STOP: Do not proceed to OCR recovery
    logging.info(f"Page {page_num} region {page_region.bbox}: Sous-rature detected, preserving")
    return page_region

# No X-marks found, proceed to Stage 3
```

**Output**: If X-marks found, add `'sous_rature'` flag and STOP. Otherwise, continue to Stage 3.

---

### Stage 3: OCR Recovery (Selective Tesseract)

**When**: Only if garbled (Stage 1) AND no X-marks (Stage 2) AND `RAG_ENABLE_OCR_RECOVERY=true`
**Input**: `pdf_path`, `page_num`, `page_region.bbox`, `garbled_result.confidence`
**Processing**:

```python
from lib.ocr_recovery import recover_page_region, OCRRecoveryConfig

# Only run if garbled + no X-marks
if not page_region.is_garbled() or page_region.is_strikethrough():
    return page_region  # Skip Stage 3

# Check if OCR available
if not OCR_AVAILABLE:
    logging.warning("OCR recovery requested but dependencies not available")
    page_region.quality_flags.add('recovery_unavailable')
    return page_region

# Check confidence threshold (only recover high-confidence garbled text)
strategy = STRATEGY_CONFIGS.get(RAG_QUALITY_STRATEGY, STRATEGY_CONFIGS['hybrid'])
recovery_threshold = strategy['recovery_threshold']

if garbled_result.confidence < recovery_threshold:
    # Confidence too low, preserve original
    page_region.quality_flags.add('low_confidence')
    logging.info(f"Page {page_num}: Confidence {garbled_result.confidence:.2f} below threshold {recovery_threshold}, preserving")
    return page_region

# Attempt OCR recovery
ocr_config = OCRRecoveryConfig(
    dpi=300,
    lang='eng',
    timeout=10  # seconds
)

try:
    recovery_result = recover_page_region(pdf_path, page_num, page_region.bbox, ocr_config)

    if recovery_result.success:
        # Replace spans with recovered text
        page_region.spans = recovery_result.text_spans
        page_region.quality_flags.add('recovered')
        page_region.quality_score = recovery_result.confidence

        logging.info(f"Page {page_num}: OCR recovery successful (confidence: {recovery_result.confidence:.2f})")
    else:
        page_region.quality_flags.add('recovery_failed')
        logging.warning(f"Page {page_num}: OCR recovery failed, preserving original")

except Exception as e:
    page_region.quality_flags.add('recovery_error')
    logging.error(f"Page {page_num}: OCR recovery error: {e}", exc_info=True)

return page_region
```

**Output**: Updated `page_region` with recovered text (if successful) or appropriate quality flags

---

## Code Integration Points

### 1. Add Configuration Class

**File**: `lib/rag_processing.py` (top-level)

```python
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class QualityPipelineConfig:
    """Configuration for the quality pipeline stages."""

    # Feature toggles
    enable_pipeline: bool = True
    detect_garbled: bool = True
    detect_strikethrough: bool = True
    enable_ocr_recovery: bool = True

    # Strategy
    strategy: str = 'hybrid'  # 'philosophy' | 'technical' | 'hybrid'

    # Thresholds (from strategy)
    garbled_threshold: float = 0.75
    recovery_threshold: float = 0.8

    # Performance
    batch_size: int = 10

    @classmethod
    def from_env(cls) -> 'QualityPipelineConfig':
        """Load configuration from environment variables."""
        strategy_name = os.getenv('RAG_QUALITY_STRATEGY', 'hybrid')
        strategy = STRATEGY_CONFIGS.get(strategy_name, STRATEGY_CONFIGS['hybrid'])

        return cls(
            enable_pipeline=os.getenv('RAG_ENABLE_QUALITY_PIPELINE', 'true').lower() == 'true',
            detect_garbled=os.getenv('RAG_DETECT_GARBLED', 'true').lower() == 'true',
            detect_strikethrough=os.getenv('RAG_DETECT_STRIKETHROUGH', 'true').lower() == 'true',
            enable_ocr_recovery=os.getenv('RAG_ENABLE_OCR_RECOVERY', 'true').lower() == 'true',
            strategy=strategy_name,
            garbled_threshold=strategy['garbled_threshold'],
            recovery_threshold=strategy['recovery_threshold'],
            batch_size=int(os.getenv('RAG_QUALITY_BATCH_SIZE', '10'))
        )
```

### 2. Add Feature Detection Flags

**File**: `lib/rag_processing.py` (near top, with other feature flags)

```python
# X-mark detection (opencv)
try:
    import cv2
    import numpy as np
    XMARK_AVAILABLE = True
except ImportError:
    XMARK_AVAILABLE = False
    cv2 = None
    np = None
```

### 3. Implement _apply_quality_pipeline()

**File**: `lib/rag_processing.py` (before process_pdf)

```python
def _apply_quality_pipeline(
    page_region: PageRegion,
    pdf_path: Path,
    page_num: int,
    config: QualityPipelineConfig
) -> PageRegion:
    """
    Apply sequential waterfall quality pipeline to a PageRegion.

    See PHASE_2_INTEGRATION_SPECIFICATION.md for complete flow.
    """

    if not config.enable_pipeline:
        return page_region

    # Stage 1: Statistical Detection
    if config.detect_garbled:
        page_region = _stage_1_statistical_detection(page_region, config)

    # Stage 2: Visual Analysis (only if garbled)
    if page_region.is_garbled() and config.detect_strikethrough:
        page_region = _stage_2_visual_analysis(page_region, pdf_path, page_num, config)

        # If sous-rature detected, stop here
        if page_region.is_strikethrough():
            return page_region

    # Stage 3: OCR Recovery (only if garbled + no X-marks)
    if page_region.is_garbled() and not page_region.is_strikethrough() and config.enable_ocr_recovery:
        page_region = _stage_3_ocr_recovery(page_region, pdf_path, page_num, config)

    return page_region


def _stage_1_statistical_detection(page_region: PageRegion, config: QualityPipelineConfig) -> PageRegion:
    """Stage 1: Detect garbled text via statistical analysis."""
    # Implementation as shown in Data Flow section above
    pass


def _stage_2_visual_analysis(
    page_region: PageRegion,
    pdf_path: Path,
    page_num: int,
    config: QualityPipelineConfig
) -> PageRegion:
    """Stage 2: Detect X-marks/strikethrough via opencv."""
    # Implementation as shown in Data Flow section above
    pass


def _stage_3_ocr_recovery(
    page_region: PageRegion,
    pdf_path: Path,
    page_num: int,
    config: QualityPipelineConfig
) -> PageRegion:
    """Stage 3: Selective Tesseract recovery for corrupted regions."""
    # Implementation as shown in Data Flow section above
    pass
```

### 4. Modify process_pdf()

**File**: `lib/rag_processing.py`, in process_pdf() function

**Location**: After `_analyze_pdf_block()` call, before appending to results

```python
def process_pdf(file_path: Path, output_format: str = "txt", preserve_linebreaks: bool = False) -> str:
    # ... existing code ...

    # Load quality pipeline config once
    quality_config = QualityPipelineConfig.from_env()

    # ... existing code ...

    for page_num, page in enumerate(doc):
        for block in page.get_text("dict").get("blocks", []):
            # Existing analysis
            block_analysis = _analyze_pdf_block(
                block,
                preserve_linebreaks=preserve_linebreaks,
                detect_headings=detect_headings,
                return_structured=True  # Get PageRegion object
            )

            # NEW: Apply quality pipeline
            if isinstance(block_analysis, PageRegion) and quality_config.enable_pipeline:
                block_analysis = _apply_quality_pipeline(
                    block_analysis,
                    file_path,
                    page_num,
                    quality_config
                )

            # Continue with existing aggregation logic
            # ...
```

---

## Error Handling

### Graceful Degradation

```python
# Stage 2: If opencv unavailable, skip to Stage 3
if not XMARK_AVAILABLE:
    logging.warning("X-mark detection unavailable (opencv not installed)")
    # Continue to Stage 3

# Stage 3: If OCR unavailable, preserve original
if not OCR_AVAILABLE:
    logging.warning("OCR recovery unavailable (pytesseract not installed)")
    page_region.quality_flags.add('recovery_unavailable')
    return page_region
```

### Circuit Breaker

```python
# Track consecutive OCR failures
ocr_failure_count = 0
OCR_CIRCUIT_BREAKER_THRESHOLD = 5

def _stage_3_ocr_recovery(...):
    global ocr_failure_count

    if ocr_failure_count >= OCR_CIRCUIT_BREAKER_THRESHOLD:
        logging.error(f"OCR circuit breaker open ({ocr_failure_count} consecutive failures)")
        page_region.quality_flags.add('ocr_circuit_open')
        return page_region

    try:
        recovery_result = recover_page_region(...)
        ocr_failure_count = 0  # Reset on success
    except Exception as e:
        ocr_failure_count += 1
        raise
```

---

## Testing Strategy

### Unit Tests

**File**: `__tests__/python/test_quality_pipeline_integration.py`

```python
def test_stage_1_garbled_detection():
    """Test Stage 1 populates quality_flags correctly."""

def test_stage_2_xmark_detection_preserves():
    """Test Stage 2 stops pipeline when X-marks found."""

def test_stage_3_ocr_recovery():
    """Test Stage 3 recovers garbled text."""

def test_pipeline_feature_flags():
    """Test individual stage toggles work."""

def test_strategy_profiles():
    """Test philosophy/technical/hybrid strategies."""
```

### Integration Tests

**File**: `__tests__/python/test_phase_2_complete_integration.py`

```python
def test_end_to_end_philosophy_pdf():
    """Test complete pipeline with Derrida sous-rature PDF."""
    # Use test_files/derrida_pages_110_135.pdf
    # Verify X-marks detected, text preserved

def test_end_to_end_corrupted_pdf():
    """Test complete pipeline with OCR-corrupted PDF."""
    # Verify garbled detection → no X-marks → OCR recovery

def test_end_to_end_clean_pdf():
    """Test pipeline has minimal overhead on clean PDFs."""
    # Verify Stage 1 passes, Stages 2-3 skipped
```

---

## Performance Requirements

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Stage 1 (Statistical) | <1ms per region | Per-region timing |
| Stage 2 (X-mark) | <5ms per region | Per-region timing |
| Stage 3 (OCR) | <300ms per region | Per-region timing |
| Full page (clean) | <10ms overhead | Total page time |
| Full page (corrupted) | <350ms total | Total page time |

---

## Migration Path

### Phase 1: Stage 1 Only (Week 1)
- Implement `_stage_1_statistical_detection()`
- Integrate into `process_pdf()`
- Test with clean and garbled PDFs
- Verify quality_flags populated

### Phase 2: Stage 2 Addition (Week 2)
- Create `lib/strikethrough_detection.py`
- Implement `_stage_2_visual_analysis()`
- Test with Derrida sous-rature PDFs
- Verify preservation behavior

### Phase 3: Stage 3 Addition (Week 3)
- Create `lib/ocr_recovery.py`
- Implement `_stage_3_ocr_recovery()`
- Test with OCR-corrupted PDFs
- Verify recovery behavior

### Phase 4: Complete Integration (Week 4)
- End-to-end testing
- Performance validation
- Documentation updates
- Release

---

## Rollback Strategy

### Feature Flag Disable

```bash
# Disable entire pipeline (use old quality system)
export RAG_ENABLE_QUALITY_PIPELINE=false

# Disable individual stages
export RAG_DETECT_GARBLED=false
export RAG_DETECT_STRIKETHROUGH=false
export RAG_ENABLE_OCR_RECOVERY=false
```

### Code Rollback

```python
# In process_pdf(), simple conditional disables new pipeline
if quality_config.enable_pipeline:
    block_analysis = _apply_quality_pipeline(...)
else:
    # Use old quality system (assess_pdf_ocr_quality)
    pass
```

---

## Open Questions

1. **Batch Processing**: Should quality pipeline run on batches of regions for performance?
2. **Caching**: Should we cache garbled detection results per-page to avoid re-analysis?
3. **Parallel Processing**: Should Stages 1-3 run in parallel for different regions?
4. **Quality Metadata Serialization**: Should quality_flags persist to output files?

---

## References

- **ADR-006**: Quality Pipeline Architecture
- **Phase 2.2 Report**: PHASE_2_QUALITY_IMPROVEMENT_REPORT.md
- **Status Report**: PHASE_1_2_STATUS_REPORT_2025_10_18.md
- **Data Models**: lib/rag_data_models.py
- **Garbled Detection**: lib/garbled_text_detection.py

---

**Document Status**: Draft - Awaiting review and implementation
**Next Review**: After Phase 2.2 integration complete
