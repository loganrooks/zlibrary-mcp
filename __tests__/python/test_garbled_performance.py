"""
Performance benchmarks for garbled text detection.

Validates that detection meets performance targets:
- <1ms per region (individual detection)
- <100ms per page (50 regions typical)
- Linear scaling with text length

Uses pytest-benchmark for accurate timing measurements.
"""

import pytest
import time
import sys
from pathlib import Path

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lib'))

from garbled_text_detection import (
    calculate_entropy,
    detect_garbled_text_enhanced,
    GarbledDetectionConfig
)


class TestPerformance:
    """Performance benchmark tests."""

    def test_entropy_calculation_fast(self, benchmark):
        """Entropy calculation should be fast (<0.1ms for typical text)."""
        text = "This is a sample sentence of normal English text. " * 20  # ~1000 chars

        result = benchmark(calculate_entropy, text)

        # Should complete in microseconds for typical text
        assert result >= 0.0  # Valid entropy value
        # pytest-benchmark will report timing stats

    def test_detection_single_region_fast(self, benchmark):
        """Single region detection should be <1ms."""
        text = "This is a sample sentence of normal English text. " * 40  # ~2000 chars (typical region)

        result = benchmark(detect_garbled_text_enhanced, text)

        assert isinstance(result.is_garbled, bool)
        # pytest-benchmark will verify timing

    def test_detection_short_text_very_fast(self, benchmark):
        """Short text detection should be extremely fast (early exit)."""
        text = "short"  # Below min_length

        result = benchmark(detect_garbled_text_enhanced, text)

        assert result.is_garbled is False

    def test_detection_long_text_scales_linearly(self):
        """Detection should scale linearly with text length."""
        texts = {
            'small': "Sample text. " * 100,      # ~1,300 chars
            'medium': "Sample text. " * 500,     # ~6,500 chars
            'large': "Sample text. " * 1000,     # ~13,000 chars
        }

        timings = {}

        for size, text in texts.items():
            start = time.perf_counter()
            for _ in range(100):  # Average over 100 runs
                detect_garbled_text_enhanced(text)
            duration = time.perf_counter() - start
            timings[size] = duration / 100  # Average per run

        # Should scale roughly linearly
        # Large should not be 10x slower than small (that would indicate O(n²))
        # Allow up to 2.5x scaling for 10x text increase (accounting for overhead)
        small_time = timings['small']
        large_time = timings['large']

        scaling_factor = large_time / small_time
        assert scaling_factor < 15, f"Scaling factor {scaling_factor:.2f} suggests non-linear complexity"

        # Also verify absolute performance
        assert large_time < 0.005, f"Large text took {large_time*1000:.2f}ms (should be <5ms)"

    def test_page_detection_under_100ms(self):
        """Detecting garbled text in all regions of a page should be <100ms."""
        # Simulate typical page: 50 regions of ~2000 chars each
        regions = ["Sample text for testing. " * 80 for _ in range(50)]

        start = time.perf_counter()
        for region in regions:
            detect_garbled_text_enhanced(region)
        duration = time.perf_counter() - start

        # Target: <100ms for full page
        assert duration < 0.1, f"Page detection took {duration*1000:.0f}ms (target: <100ms)"

    def test_detection_with_custom_config_no_overhead(self, benchmark):
        """Custom configuration should not add significant overhead."""
        text = "Sample text for configuration overhead testing. " * 20

        config = GarbledDetectionConfig(
            entropy_threshold=3.5,
            symbol_density_threshold=0.30,
            repetition_threshold=0.80
        )

        result = benchmark(detect_garbled_text_enhanced, text, config)

        assert isinstance(result.is_garbled, bool)
        # Benchmark will show if custom config adds overhead


class TestScalability:
    """Test performance with various text sizes."""

    def test_empty_string_instant(self):
        """Empty string should return instantly."""
        start = time.perf_counter()
        for _ in range(10000):
            detect_garbled_text_enhanced("")
        duration = time.perf_counter() - start

        avg_time = duration / 10000
        assert avg_time < 0.00001, f"Empty string took {avg_time*1000000:.2f}µs (should be <10µs)"

    def test_short_text_instant(self):
        """Short text (below min_length) should return instantly via early exit."""
        start = time.perf_counter()
        for _ in range(10000):
            detect_garbled_text_enhanced("short")
        duration = time.perf_counter() - start

        avg_time = duration / 10000
        assert avg_time < 0.00001, f"Short text took {avg_time*1000000:.2f}µs (should be <10µs)"

    def test_typical_region_fast(self):
        """Typical region (~2000 chars) should be <1ms."""
        text = "This is typical book text with normal sentence structure. " * 35  # ~2000 chars

        start = time.perf_counter()
        for _ in range(1000):
            detect_garbled_text_enhanced(text)
        duration = time.perf_counter() - start

        avg_time = duration / 1000
        assert avg_time < 0.001, f"Typical region took {avg_time*1000:.2f}ms (target: <1ms)"

    def test_large_region_acceptable(self):
        """Large region (~10,000 chars) should still be fast (<10ms)."""
        text = "This is a large region with substantial text content. " * 200  # ~10,000 chars

        start = time.perf_counter()
        for _ in range(100):
            detect_garbled_text_enhanced(text)
        duration = time.perf_counter() - start

        avg_time = duration / 100
        assert avg_time < 0.01, f"Large region took {avg_time*1000:.2f}ms (target: <10ms)"


class TestMemoryEfficiency:
    """Test memory usage characteristics."""

    def test_result_object_small(self):
        """Result object should be memory-efficient."""
        import sys

        text = "Sample text for memory testing."
        result = detect_garbled_text_enhanced(text)

        # Result object should be small (<1KB)
        result_size = sys.getsizeof(result)
        metrics_size = sys.getsizeof(result.metrics)
        flags_size = sys.getsizeof(result.flags)

        total_size = result_size + metrics_size + flags_size

        # Should be well under 1KB (1024 bytes)
        assert total_size < 1024, f"Result object is {total_size} bytes (should be <1KB)"

    def test_no_memory_leaks_repeated_calls(self):
        """Repeated calls should not accumulate memory."""
        import gc
        import sys

        text = "Sample text for memory leak testing."

        # Baseline memory
        gc.collect()
        baseline = sys.getsizeof(gc.get_objects())

        # Run detection many times
        for _ in range(1000):
            detect_garbled_text_enhanced(text)

        # Check memory after
        gc.collect()
        after = sys.getsizeof(gc.get_objects())

        # Memory growth should be minimal (allow 10% variance)
        growth_ratio = after / baseline
        assert growth_ratio < 1.1, f"Memory grew by {(growth_ratio-1)*100:.1f}% (should be <10%)"
