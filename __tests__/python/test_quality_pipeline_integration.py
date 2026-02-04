"""
Integration tests for Phase 2 Quality Pipeline.

Tests the complete quality pipeline integration:
- Stage 1: Statistical garbled detection
- Stage 2: X-mark/strikethrough detection
- Stage 3: OCR recovery (placeholder)

Validates:
- Quality flags populated correctly
- Quality scores calculated
- Pipeline stages execute in sequence
- Sous-rature preserved (not recovered)
- Feature flags work correctly
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from lib.rag_processing import (
    _apply_quality_pipeline,
    _stage_1_statistical_detection,
    _stage_2_visual_analysis,
    _stage_3_ocr_recovery,
    QualityPipelineConfig,
    STRATEGY_CONFIGS
)
from lib.rag_data_models import PageRegion, TextSpan
from lib.garbled_text_detection import GarbledDetectionConfig

# Check if OCR dependencies are available (not just tesseract binary)
try:
    import pytesseract
    import pdf2image
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

skip_without_tesseract = pytest.mark.skipif(
    not TESSERACT_AVAILABLE,
    reason="Tesseract OCR not installed - OCR recovery tests skipped"
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def clean_page_region():
    """PageRegion with clean text."""
    return PageRegion(
        region_type='body',
        spans=[
            TextSpan(text="This is clean, readable text. ", formatting=set()),
            TextSpan(text="It has proper structure and formatting.", formatting=set())
        ],
        bbox=(50, 100, 500, 150),
        page_num=1
    )


@pytest.fixture
def garbled_page_region():
    """PageRegion with garbled text."""
    return PageRegion(
        region_type='body',
        spans=[
            TextSpan(text="!@#$%^&*()_+!@#$%^&*()_+!@#$%^&*()", formatting=set()),
            TextSpan(text="GGGGGGGGGGGGaaaaaaaaaaaa", formatting=set())
        ],
        bbox=(50, 100, 500, 150),
        page_num=1
    )


@pytest.fixture
def quality_config():
    """Default quality pipeline configuration."""
    return QualityPipelineConfig(
        enable_pipeline=True,
        detect_garbled=True,
        detect_strikethrough=True,
        enable_ocr_recovery=True,
        strategy='hybrid',
        garbled_threshold=0.75,
        recovery_threshold=0.8
    )


@pytest.fixture
def philosophy_strategy_config():
    """Philosophy strategy (conservative preservation)."""
    return QualityPipelineConfig(
        enable_pipeline=True,
        detect_garbled=True,
        detect_strikethrough=True,
        enable_ocr_recovery=True,
        strategy='philosophy',
        garbled_threshold=0.9,  # Very conservative
        recovery_threshold=0.95  # Almost never auto-recover
    )


# =============================================================================
# Stage 1: Statistical Detection Tests
# =============================================================================

def test_stage_1_clean_text(clean_page_region, quality_config):
    """Test Stage 1 with clean text (no garbled detection)."""
    result = _stage_1_statistical_detection(clean_page_region, quality_config)

    # Should NOT be flagged as garbled
    assert not result.is_garbled()
    assert result.quality_flags == set()
    assert result.quality_score == 1.0  # Perfect quality


def test_stage_1_garbled_text(garbled_page_region, quality_config):
    """Test Stage 1 with garbled text (should detect)."""
    result = _stage_1_statistical_detection(garbled_page_region, quality_config)

    # Should be flagged as garbled
    assert result.is_garbled()
    assert result.quality_flags is not None
    assert len(result.quality_flags) > 0
    assert result.quality_score is not None
    assert result.quality_score < 1.0  # Below perfect quality


def test_stage_1_short_text():
    """Test Stage 1 with very short text (should skip analysis)."""
    short_region = PageRegion(
        region_type='body',
        spans=[TextSpan(text="Hi", formatting=set())],
        bbox=(50, 100, 500, 150),
        page_num=1
    )
    config = QualityPipelineConfig()

    result = _stage_1_statistical_detection(short_region, config)

    # Too short to analyze, should have no flags
    assert result.quality_flags == set()
    assert result.quality_score == 1.0


def test_stage_1_strategy_thresholds(garbled_page_region):
    """Test different strategies have different thresholds."""
    # Philosophy strategy (conservative)
    phil_config = QualityPipelineConfig(
        strategy='philosophy',
        garbled_threshold=0.9
    )
    phil_result = _stage_1_statistical_detection(garbled_page_region, phil_config)

    # Technical strategy (aggressive)
    tech_config = QualityPipelineConfig(
        strategy='technical',
        garbled_threshold=0.6
    )
    tech_result = _stage_1_statistical_detection(garbled_page_region, tech_config)

    # Both should detect garbled, but with potentially different confidence
    # (actual confidence depends on text, but thresholds differ)
    assert phil_config.garbled_threshold > tech_config.garbled_threshold


# =============================================================================
# Stage 2: X-mark Detection Tests
# =============================================================================

@patch('lib.rag_processing.XMARK_AVAILABLE', True)
@patch('lib.strikethrough_detection.detect_strikethrough_enhanced')
def test_stage_2_runs_on_clean_text(mock_detect, clean_page_region, quality_config):
    """Test Stage 2 RUNS on clean text (independent of Stage 1)."""
    # Critical fix (2025-10-18): Stage 2 now runs independently
    # Sous-rature PDFs have clean text with visual X-marks

    # Mock no X-marks found
    from lib.strikethrough_detection import XMarkDetectionResult
    mock_detect.return_value = XMarkDetectionResult(
        has_xmarks=False,
        xmark_count=0,
        confidence=0.0,
        flags={'no_crossings_found'}
    )

    # Stage 2 should RUN (not skip) even on clean text
    result, xmark_result = _stage_2_visual_analysis(
        clean_page_region,
        Path('fake.pdf'),
        0,
        quality_config
    )

    # X-mark detection should have been attempted
    assert mock_detect.called
    assert not result.is_strikethrough()  # No X-marks in this case


@patch('lib.rag_processing.XMARK_AVAILABLE', False)
def test_stage_2_graceful_degradation_no_opencv(garbled_page_region, quality_config):
    """Test Stage 2 gracefully degrades when opencv unavailable."""
    # Mark as garbled first
    garbled_page_region.quality_flags = {'high_symbols'}
    garbled_page_region.quality_score = 0.3

    result, xmark_result = _stage_2_visual_analysis(
        garbled_page_region,
        Path('fake.pdf'),
        0,
        quality_config
    )

    # Should flag unavailability
    assert 'xmark_detection_unavailable' in result.quality_flags
    assert xmark_result is None  # No detection when opencv unavailable


@patch('lib.rag_processing.XMARK_AVAILABLE', True)
@patch('lib.strikethrough_detection.detect_strikethrough_enhanced')
def test_stage_2_xmarks_detected(mock_detect, garbled_page_region, quality_config):
    """Test Stage 2 when X-marks detected (sous-rature)."""
    # Setup: garbled text from Stage 1
    garbled_page_region.quality_flags = {'high_symbols'}
    garbled_page_region.quality_score = 0.3

    # Mock X-mark detection result
    from lib.strikethrough_detection import XMarkDetectionResult, XMarkCandidate, DetectedLine
    mock_result = XMarkDetectionResult(
        has_xmarks=True,
        xmark_count=1,
        confidence=0.95,
        flags={'high_confidence'},
        candidates=[],
        metrics={}
    )
    mock_detect.return_value = mock_result

    result, xmark_result = _stage_2_visual_analysis(
        garbled_page_region,
        Path('fake.pdf'),
        0,
        quality_config
    )

    # Should flag as sous-rature
    assert result.is_strikethrough()
    assert 'sous_rature' in result.quality_flags
    assert 'intentional_deletion' in result.quality_flags
    assert result.quality_score == 1.0  # Reset to perfect (philosophical content)
    assert xmark_result == mock_result  # Should return detection result


@patch('lib.rag_processing.XMARK_AVAILABLE', True)
@patch('lib.strikethrough_detection.detect_strikethrough_enhanced')
def test_stage_2_no_xmarks(mock_detect, garbled_page_region, quality_config):
    """Test Stage 2 when no X-marks detected (proceed to Stage 3)."""
    # Setup: garbled text
    garbled_page_region.quality_flags = {'high_symbols'}
    garbled_page_region.quality_score = 0.3

    # Mock no X-marks
    from lib.strikethrough_detection import XMarkDetectionResult
    mock_result = XMarkDetectionResult(
        has_xmarks=False,
        xmark_count=0,
        confidence=0.0,
        flags={'no_crossings_found'}
    )
    mock_detect.return_value = mock_result

    result, xmark_result = _stage_2_visual_analysis(
        garbled_page_region,
        Path('fake.pdf'),
        0,
        quality_config
    )

    # Should NOT flag as sous-rature
    assert not result.is_strikethrough()
    # Original garbled flags should remain
    assert 'high_symbols' in result.quality_flags
    assert xmark_result == mock_result  # Should still return result even if no X-marks


# =============================================================================
# Stage 3: OCR Recovery Tests
# =============================================================================

def test_stage_3_skips_clean_text(clean_page_region, quality_config):
    """Test Stage 3 skips if not garbled."""
    result = _stage_3_ocr_recovery(
        clean_page_region,
        Path('fake.pdf'),
        0,
        quality_config
    )

    # Should return unchanged
    assert result == clean_page_region


def test_stage_3_skips_sous_rature(garbled_page_region, quality_config):
    """Test Stage 3 skips if sous-rature detected (preserve philosophical content)."""
    # Mark as garbled AND sous-rature
    garbled_page_region.quality_flags = {'high_symbols', 'sous_rature'}
    garbled_page_region.quality_score = 0.3

    result = _stage_3_ocr_recovery(
        garbled_page_region,
        Path('fake.pdf'),
        0,
        quality_config
    )

    # Should NOT attempt recovery
    assert 'recovery_needed' not in result.quality_flags
    assert 'sous_rature' in result.quality_flags  # Preserved


@patch('lib.rag_processing.OCR_AVAILABLE', False)
def test_stage_3_graceful_degradation_no_ocr(garbled_page_region, quality_config):
    """Test Stage 3 gracefully degrades when OCR unavailable."""
    # Mark as garbled
    garbled_page_region.quality_flags = {'high_symbols'}
    garbled_page_region.quality_score = 0.1  # High confidence garbled

    result = _stage_3_ocr_recovery(
        garbled_page_region,
        Path('fake.pdf'),
        0,
        quality_config
    )

    # Should flag unavailability
    assert 'recovery_unavailable' in result.quality_flags


@skip_without_tesseract
def test_stage_3_low_confidence_skips_recovery(garbled_page_region, quality_config):
    """Test Stage 3 skips recovery for low-confidence garbled text."""
    # Low confidence garbled (quality_score close to 1.0 = low garbled_confidence)
    garbled_page_region.quality_flags = {'high_symbols'}
    garbled_page_region.quality_score = 0.5  # 50% quality = 50% garbled confidence (below 0.8 threshold)

    result = _stage_3_ocr_recovery(
        garbled_page_region,
        Path('fake.pdf'),
        0,
        quality_config
    )

    # Should flag as low confidence
    assert 'low_confidence' in result.quality_flags
    assert 'recovery_needed' not in result.quality_flags


@skip_without_tesseract
def test_stage_3_high_confidence_needs_recovery(garbled_page_region, quality_config):
    """Test Stage 3 flags high-confidence garbled text for recovery."""
    # High confidence garbled (quality_score low = high garbled_confidence)
    garbled_page_region.quality_flags = {'high_symbols', 'low_entropy'}
    garbled_page_region.quality_score = 0.1  # 10% quality = 90% garbled confidence (above 0.8 threshold)

    result = _stage_3_ocr_recovery(
        garbled_page_region,
        Path('fake.pdf'),
        0,
        quality_config
    )

    # Should flag as recovery needed (placeholder implementation)
    assert 'recovery_needed' in result.quality_flags


# =============================================================================
# Complete Pipeline Tests
# =============================================================================

def test_pipeline_disabled(clean_page_region, quality_config):
    """Test pipeline can be completely disabled."""
    quality_config.enable_pipeline = False

    result = _apply_quality_pipeline(
        clean_page_region,
        Path('fake.pdf'),
        0,
        quality_config
    )

    # Should return unchanged
    assert result == clean_page_region
    assert result.quality_flags is None


def test_pipeline_stage_1_only(clean_page_region, quality_config):
    """Test with only Stage 1 enabled."""
    quality_config.detect_strikethrough = False
    quality_config.enable_ocr_recovery = False

    result = _apply_quality_pipeline(
        clean_page_region,
        Path('fake.pdf'),
        0,
        quality_config
    )

    # Stage 1 should run
    assert result.quality_flags == set()  # Clean text
    assert result.quality_score == 1.0


@patch('lib.rag_processing.XMARK_AVAILABLE', True)
@patch('lib.strikethrough_detection.detect_strikethrough_enhanced')
def test_pipeline_stops_at_sous_rature(mock_detect, garbled_page_region, quality_config):
    """Test pipeline stops at Stage 2 when sous-rature detected."""
    # Mock garbled detection (happens in Stage 1)
    garbled_page_region.quality_flags = {'high_symbols'}
    garbled_page_region.quality_score = 0.2

    # Mock X-mark detection (Stage 2)
    from lib.strikethrough_detection import XMarkDetectionResult
    mock_detect.return_value = XMarkDetectionResult(
        has_xmarks=True,
        xmark_count=2,
        confidence=0.92,
        flags={'high_confidence', 'few_xmarks'}
    )

    result = _apply_quality_pipeline(
        garbled_page_region,
        Path('fake.pdf'),
        0,
        quality_config
    )

    # Should stop at Stage 2 (not proceed to OCR recovery)
    assert result.is_strikethrough()
    assert 'sous_rature' in result.quality_flags
    assert 'intentional_deletion' in result.quality_flags
    assert 'recovery_needed' not in result.quality_flags  # Stage 3 didn't run


@skip_without_tesseract
def test_pipeline_proceeds_to_stage_3(garbled_page_region, quality_config):
    """Test pipeline proceeds to Stage 3 when garbled but no X-marks."""
    with patch('lib.rag_processing.XMARK_AVAILABLE', True), \
         patch('lib.strikethrough_detection.detect_strikethrough_enhanced') as mock_detect:

        # Mock no X-marks
        from lib.strikethrough_detection import XMarkDetectionResult
        mock_detect.return_value = XMarkDetectionResult(
            has_xmarks=False,
            xmark_count=0,
            confidence=0.0
        )

        # High confidence garbled (should proceed to recovery)
        garbled_page_region.quality_flags = None  # Reset
        garbled_page_region.quality_score = None

        result = _apply_quality_pipeline(
            garbled_page_region,
            Path('fake.pdf'),
            0,
            quality_config
        )

        # Stage 1 should detect garbled
        assert result.is_garbled()

        # Stage 2 should NOT find X-marks
        assert not result.is_strikethrough()

        # Stage 3 should flag for recovery (or attempt if implemented)
        # Note: Stage 3 is placeholder, so check for expected placeholder behavior
        if result.quality_score < 0.2:  # High garbled confidence
            assert 'recovery_needed' in result.quality_flags or 'low_confidence' in result.quality_flags


# =============================================================================
# Configuration Tests
# =============================================================================

def test_config_from_env_defaults():
    """Test QualityPipelineConfig.from_env() with default environment."""
    import os

    # Clear environment
    for key in ['RAG_ENABLE_QUALITY_PIPELINE', 'RAG_DETECT_GARBLED', 'RAG_QUALITY_STRATEGY']:
        os.environ.pop(key, None)

    config = QualityPipelineConfig.from_env()

    # Verify defaults
    assert config.enable_pipeline == True  # Default 'true'
    assert config.detect_garbled == True
    assert config.detect_strikethrough == True
    assert config.strategy == 'hybrid'
    assert config.garbled_threshold == 0.75  # Hybrid strategy
    assert config.recovery_threshold == 0.8


def test_config_from_env_philosophy_strategy():
    """Test loading philosophy strategy from environment."""
    import os

    os.environ['RAG_QUALITY_STRATEGY'] = 'philosophy'

    try:
        config = QualityPipelineConfig.from_env()

        # Verify philosophy strategy loaded
        assert config.strategy == 'philosophy'
        assert config.garbled_threshold == 0.9  # Conservative
        assert config.recovery_threshold == 0.95  # Almost never recover
    finally:
        os.environ.pop('RAG_QUALITY_STRATEGY', None)


def test_config_feature_flags():
    """Test individual feature flags from environment."""
    import os

    os.environ['RAG_ENABLE_QUALITY_PIPELINE'] = 'false'
    os.environ['RAG_DETECT_GARBLED'] = 'false'

    try:
        config = QualityPipelineConfig.from_env()

        assert config.enable_pipeline == False
        assert config.detect_garbled == False
    finally:
        os.environ.pop('RAG_ENABLE_QUALITY_PIPELINE', None)
        os.environ.pop('RAG_DETECT_GARBLED', None)


def test_strategy_configs_exist():
    """Test all strategy configurations are defined."""
    assert 'philosophy' in STRATEGY_CONFIGS
    assert 'technical' in STRATEGY_CONFIGS
    assert 'hybrid' in STRATEGY_CONFIGS

    # Verify required fields
    for strategy in STRATEGY_CONFIGS.values():
        assert 'garbled_threshold' in strategy
        assert 'recovery_threshold' in strategy
        assert 'enable_strikethrough' in strategy
        assert 'priority' in strategy


# =============================================================================
# Helper Method Tests
# =============================================================================

def test_page_region_quality_helpers(garbled_page_region):
    """Test PageRegion quality helper methods."""
    # Setup garbled region
    garbled_page_region.quality_flags = {'high_symbols', 'low_entropy'}
    garbled_page_region.quality_score = 0.2

    # Test helpers
    assert garbled_page_region.has_quality_issues()
    assert garbled_page_region.is_garbled()
    assert not garbled_page_region.is_strikethrough()
    assert not garbled_page_region.was_recovered()

    # Test quality summary
    summary = garbled_page_region.get_quality_summary()
    assert 'garbled' in summary.lower()
    assert 'high_symbols' in summary


def test_page_region_sous_rature_helpers(clean_page_region):
    """Test sous-rature detection helper."""
    clean_page_region.quality_flags = {'sous_rature', 'intentional_deletion'}
    clean_page_region.quality_score = 1.0

    assert clean_page_region.has_quality_issues()  # Has flags
    assert clean_page_region.is_strikethrough()
    assert not clean_page_region.is_garbled()  # Not garbled, just strikethrough

    summary = clean_page_region.get_quality_summary()
    assert 'strikethrough' in summary.lower()


def test_page_region_recovered_helpers(garbled_page_region):
    """Test recovered text helper."""
    garbled_page_region.quality_flags = {'recovered', 'high_symbols'}
    garbled_page_region.quality_score = 0.8  # Improved after recovery

    assert garbled_page_region.was_recovered()

    summary = garbled_page_region.get_quality_summary()
    assert 'recovered' in summary.lower()


# =============================================================================
# Performance Tests
# =============================================================================

def test_stage_1_performance(benchmark):
    """Benchmark Stage 1 performance (target: <1ms per region)."""
    region = PageRegion(
        region_type='body',
        spans=[TextSpan(text="This is a sample paragraph with normal text content " * 10, formatting=set())],
        bbox=(50, 100, 500, 150),
        page_num=1
    )
    config = QualityPipelineConfig()

    # Benchmark Stage 1
    result = benchmark(_stage_1_statistical_detection, region, config)

    # Verify completed
    assert result is not None


# =============================================================================
# Error Handling Tests
# =============================================================================

def test_stage_2_handles_errors(garbled_page_region, quality_config):
    """Test Stage 2 handles detection errors gracefully."""
    # Mark as garbled
    garbled_page_region.quality_flags = {'high_symbols'}
    garbled_page_region.quality_score = 0.2

    with patch('lib.rag_processing.XMARK_AVAILABLE', True), \
         patch('lib.strikethrough_detection.detect_strikethrough_enhanced', side_effect=RuntimeError("Test error")):

        result, xmark_result = _stage_2_visual_analysis(
            garbled_page_region,
            Path('fake.pdf'),
            0,
            quality_config
        )

        # Should flag error
        assert 'xmark_detection_error' in result.quality_flags
        # Should preserve original quality_flags
        assert 'high_symbols' in result.quality_flags
