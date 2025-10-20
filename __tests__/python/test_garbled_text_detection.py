"""
Comprehensive unit tests for garbled_text_detection module.

Tests all components of the enhanced garbled detection system:
- Entropy calculation
- Configuration validation
- Enhanced detection with multiple heuristics
- Confidence scoring logic
- Edge cases and error handling

Coverage target: >90% of garbled_text_detection.py
"""

import pytest
import sys
from pathlib import Path

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lib'))

from garbled_text_detection import (
    calculate_entropy,
    detect_garbled_text_enhanced,
    detect_garbled_text,
    GarbledDetectionConfig,
    GarbledDetectionResult
)


class TestCalculateEntropy:
    """Test Shannon entropy calculation."""

    def test_entropy_uniform_text(self):
        """All same character should have 0 entropy."""
        text = "aaaaaaaaaa"
        entropy = calculate_entropy(text)
        assert entropy == 0.0

    def test_entropy_empty_string(self):
        """Empty string should have 0 entropy."""
        entropy = calculate_entropy("")
        assert entropy == 0.0

    def test_entropy_single_char(self):
        """Single character should have 0 entropy."""
        entropy = calculate_entropy("a")
        assert entropy == 0.0

    def test_entropy_binary(self):
        """Equal distribution of two chars should have 1.0 entropy."""
        text = "ababababab"
        entropy = calculate_entropy(text)
        assert entropy == pytest.approx(1.0, rel=0.01)

    def test_entropy_normal_english(self):
        """Normal English text should have entropy around 4.0-4.5."""
        text = "This is a sample sentence of normal English text with variety of characters."
        entropy = calculate_entropy(text)
        assert 3.5 <= entropy <= 5.0

    def test_entropy_high_diversity(self):
        """Text with many unique characters should have high entropy."""
        text = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        entropy = calculate_entropy(text)
        assert entropy > 5.0


class TestGarbledDetectionConfig:
    """Test configuration class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = GarbledDetectionConfig()
        assert config.entropy_threshold == 3.2
        assert config.symbol_density_threshold == 0.25
        assert config.repetition_threshold == 0.7
        assert config.min_text_length == 10

    def test_custom_config(self):
        """Test custom configuration values."""
        config = GarbledDetectionConfig(
            entropy_threshold=3.5,
            symbol_density_threshold=0.30,
            repetition_threshold=0.80,
            min_text_length=20
        )
        assert config.entropy_threshold == 3.5
        assert config.symbol_density_threshold == 0.30
        assert config.repetition_threshold == 0.80
        assert config.min_text_length == 20

    def test_strict_config(self):
        """Test strict detection configuration."""
        config = GarbledDetectionConfig(
            entropy_threshold=3.8,
            symbol_density_threshold=0.15,
            repetition_threshold=0.25
        )
        assert config.entropy_threshold == 3.8
        assert config.symbol_density_threshold == 0.15

    def test_lenient_config(self):
        """Test lenient detection configuration."""
        config = GarbledDetectionConfig(
            entropy_threshold=2.5,
            symbol_density_threshold=0.50,
            repetition_threshold=0.85
        )
        assert config.entropy_threshold == 2.5
        assert config.symbol_density_threshold == 0.50


class TestGarbledDetectionResult:
    """Test result dataclass."""

    def test_result_creation(self):
        """Test creating a result object."""
        result = GarbledDetectionResult(
            is_garbled=True,
            confidence=0.85,
            metrics={'entropy': 2.5, 'symbol_density': 0.4},
            flags={'low_entropy', 'high_symbols'}
        )
        assert result.is_garbled is True
        assert result.confidence == 0.85
        assert 'entropy' in result.metrics
        assert 'low_entropy' in result.flags

    def test_result_defaults(self):
        """Test result with default values."""
        result = GarbledDetectionResult(
            is_garbled=False,
            confidence=0.0
        )
        assert result.metrics == {}
        assert result.flags == set()


class TestEnhancedDetection:
    """Test enhanced detection with multiple heuristics."""

    def test_clean_text_not_flagged(self):
        """Normal English text should not be flagged."""
        text = "This is a sample sentence of normal English text."
        result = detect_garbled_text_enhanced(text)

        assert result.is_garbled is False
        assert result.confidence == 0.0
        assert len(result.flags) == 0

    def test_low_entropy_flagged(self):
        """Text with very low entropy should be flagged."""
        text = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        result = detect_garbled_text_enhanced(text)

        assert result.is_garbled is True
        assert result.confidence > 0.6
        assert 'low_entropy' in result.flags
        assert result.metrics['entropy'] < 1.0

    def test_high_symbols_flagged(self):
        """Text with high symbol density should be flagged."""
        text = "!@#$%^&*()_+!@#$%^&*()_+!@#$%^&*()_+"
        result = detect_garbled_text_enhanced(text)

        assert result.is_garbled is True
        assert 'high_symbols' in result.flags
        assert result.metrics['symbol_density'] > 0.25

    def test_high_repetition_flagged(self):
        """Text with high character repetition should be flagged."""
        text = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        result = detect_garbled_text_enhanced(text)

        assert result.is_garbled is True
        assert 'repeated_chars' in result.flags
        assert result.metrics['repetition_ratio'] > 0.7

    def test_multiple_heuristics_high_confidence(self):
        """Multiple triggered heuristics should result in high confidence."""
        text = "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        result = detect_garbled_text_enhanced(text)

        assert result.is_garbled is True
        assert result.confidence > 0.85
        assert len(result.flags) >= 2  # Should trigger multiple flags

    def test_empty_string(self):
        """Empty string should not be flagged."""
        result = detect_garbled_text_enhanced("")
        assert result.is_garbled is False
        assert result.confidence == 0.0

    def test_short_text_skipped(self):
        """Text below min_length should not be analyzed."""
        result = detect_garbled_text_enhanced("short")
        assert result.is_garbled is False
        assert result.confidence == 0.0

    def test_unicode_text_handled(self):
        """Unicode text should be handled correctly."""
        text = "这是一个中文句子，应该被正确处理。"
        result = detect_garbled_text_enhanced(text)
        # Should not crash and should return valid result
        assert isinstance(result.is_garbled, bool)
        assert isinstance(result.confidence, float)

    def test_mixed_unicode_ascii(self):
        """Mixed Unicode and ASCII should work."""
        text = "This is a sentence with Unicode: café, naïve, résumé."
        result = detect_garbled_text_enhanced(text)
        assert result.is_garbled is False  # Should not be flagged as garbled

    def test_math_symbols_moderate(self):
        """Math symbols should not automatically flag as garbled."""
        text = "The equation is: x² + y² = z², where α = β + γ"
        result = detect_garbled_text_enhanced(text)
        # Should have some symbols but not be catastrophically garbled
        assert result.metrics['symbol_density'] < 0.5

    def test_very_long_text(self):
        """Very long text should be processed without issues."""
        text = "Normal text. " * 1000  # 13,000 characters
        result = detect_garbled_text_enhanced(text)
        assert isinstance(result, GarbledDetectionResult)
        # Should complete in reasonable time (tested in performance tests)

    def test_only_spaces(self):
        """Text with only spaces should be handled."""
        text = "          "
        result = detect_garbled_text_enhanced(text)
        assert result.is_garbled is False  # Too short or all spaces


class TestConfidenceScoring:
    """Test confidence scoring logic."""

    def test_no_heuristics_zero_confidence(self):
        """No triggered heuristics should give 0 confidence."""
        text = "This is perfectly normal English text without any issues at all."
        result = detect_garbled_text_enhanced(text)
        assert result.confidence == 0.0

    def test_single_heuristic_medium_confidence(self):
        """Single heuristic should give medium confidence."""
        # Create text that triggers only symbol density
        text = "This text has many symbols!!! But otherwise okay entropy and no repetition pattern."
        result = detect_garbled_text_enhanced(text)

        if result.is_garbled and len(result.flags) == 1:
            assert 0.5 <= result.confidence <= 0.9

    def test_multiple_heuristics_high_confidence(self):
        """Multiple heuristics should give high confidence."""
        text = "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"  # Triggers low entropy, high symbols, high repetition
        result = detect_garbled_text_enhanced(text)

        assert result.is_garbled is True
        assert len(result.flags) >= 2
        assert result.confidence >= 0.85

    def test_confidence_bounded(self):
        """Confidence should always be between 0 and 1."""
        test_texts = [
            "normal text",
            "!!!!!!!!!!!!",
            "aaaaaaaaaaaaa",
            "@#$%^&*()_+",
            "",
            "x"
        ]

        for text in test_texts:
            result = detect_garbled_text_enhanced(text)
            assert 0.0 <= result.confidence <= 1.0


class TestCustomConfiguration:
    """Test detection with custom configurations."""

    def test_strict_config_more_sensitive(self):
        """Strict config should flag more text as garbled."""
        text = "This text is borderline with some symbols! And varied entropy."

        strict_config = GarbledDetectionConfig(
            entropy_threshold=3.8,
            symbol_density_threshold=0.15,
            repetition_threshold=0.25
        )

        lenient_config = GarbledDetectionConfig(
            entropy_threshold=2.5,
            symbol_density_threshold=0.50,
            repetition_threshold=0.85
        )

        strict_result = detect_garbled_text_enhanced(text, strict_config)
        lenient_result = detect_garbled_text_enhanced(text, lenient_config)

        # Strict should be more likely to flag or have higher confidence
        assert strict_result.confidence >= lenient_result.confidence

    def test_custom_min_length(self):
        """Custom min_length should be respected."""
        short_text = "short"

        config = GarbledDetectionConfig(min_text_length=20)
        result = detect_garbled_text_enhanced(short_text, config)

        assert result.is_garbled is False  # Too short with custom length


class TestBackwardCompatibility:
    """Test backward-compatible API."""

    def test_legacy_api_returns_bool(self):
        """Legacy detect_garbled_text should return boolean."""
        text = "Normal text"
        result = detect_garbled_text(text)
        assert isinstance(result, bool)

    def test_legacy_api_detects_garbled(self):
        """Legacy API should detect garbled text."""
        text = "!@#$%^&*()_+!@#$%^&*()_+"
        result = detect_garbled_text(text)
        assert result is True

    def test_legacy_api_clean_text(self):
        """Legacy API should not flag clean text."""
        text = "This is a sample sentence of normal English text."
        result = detect_garbled_text(text)
        assert result is False

    def test_legacy_api_with_custom_params(self):
        """Legacy API should accept custom parameters."""
        text = "test text with some symbols!"
        result = detect_garbled_text(
            text,
            non_alpha_threshold=0.50,
            repetition_threshold=0.90,
            min_length=5
        )
        assert isinstance(result, bool)


class TestMetrics:
    """Test that metrics are correctly populated."""

    def test_metrics_present(self):
        """All expected metrics should be in result."""
        text = "Sample text for metrics testing."
        result = detect_garbled_text_enhanced(text)

        assert 'entropy' in result.metrics
        assert 'symbol_density' in result.metrics
        assert 'repetition_ratio' in result.metrics

    def test_entropy_metric_accuracy(self):
        """Entropy metric should match standalone calculation."""
        text = "Sample text for entropy testing."

        result = detect_garbled_text_enhanced(text)
        standalone_entropy = calculate_entropy(text)

        assert result.metrics['entropy'] == pytest.approx(standalone_entropy, rel=0.001)

    def test_symbol_density_range(self):
        """Symbol density should be between 0 and 1."""
        texts = [
            "Normal text",
            "Text with symbols!",
            "!@#$%^&*()_+",
            "OnlyLetters"
        ]

        for text in texts:
            result = detect_garbled_text_enhanced(text)
            assert 0.0 <= result.metrics['symbol_density'] <= 1.0

    def test_repetition_ratio_range(self):
        """Repetition ratio should be between 0 and 1."""
        texts = [
            "abcdefghij",
            "aaaaaaaaaa",
            "abc abc abc"
        ]

        for text in texts:
            result = detect_garbled_text_enhanced(text)
            assert 0.0 <= result.metrics['repetition_ratio'] <= 1.0


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_none_config_uses_default(self):
        """None config should use defaults without error."""
        text = "Test text"
        result = detect_garbled_text_enhanced(text, None)
        assert isinstance(result, GarbledDetectionResult)

    def test_non_string_input_handled_gracefully(self):
        """Non-string input should be handled (or raise appropriate error)."""
        # This tests whether the function handles type errors gracefully
        # Currently no type checking, relies on Python's duck typing
        # If string methods fail, should catch in exception handler
        try:
            result = detect_garbled_text_enhanced(123)  # type: ignore
            # If it doesn't crash, it should return a safe result
            assert isinstance(result, GarbledDetectionResult)
        except (TypeError, AttributeError):
            # This is also acceptable - failing fast with clear error
            pass
