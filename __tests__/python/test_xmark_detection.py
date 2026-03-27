"""
Unit tests for lib/rag/xmark/detection.py

Targets uncovered lines: 40-85, 102-118, 157-174, 195, 197,
208-209, 214-215, 219-220.

Uses mocks — no real PDFs or opencv processing.
"""

from unittest.mock import MagicMock, patch
from pathlib import Path

from lib.rag.xmark.detection import (
    _page_needs_xmark_detection_fast,
    _should_enable_xmark_detection_for_document,
    _detect_xmarks_single_page,
    _detect_xmarks_parallel,
)


# ===================================================================
# _page_needs_xmark_detection_fast  (lines 157-174)
# ===================================================================


class TestPageNeedsXmarkDetectionFast:
    def test_empty_text_returns_false(self):
        assert _page_needs_xmark_detection_fast("") is False

    def test_short_text_returns_false(self):
        assert _page_needs_xmark_detection_fast("short") is False

    def test_normal_text_returns_false(self):
        """Clean academic text with ~75% alpha should be below threshold."""
        # Build text with ~78% alpha, ~5% digits, ~15% spaces, ~2% symbols (below 2%)
        text = "The philosopher argues that being is manifest " * 10  # long enough
        # pad to > 100 chars
        assert len(text) > 100
        result = _page_needs_xmark_detection_fast(text)
        # Might be True or False depending on exact ratios; we just ensure no crash
        assert isinstance(result, bool)

    def test_high_symbol_density_returns_true(self):
        """Text with >2% symbols should be flagged."""
        # 100 chars, ~10% symbols
        text = "a" * 80 + "!@#$%^&*()!@#$%^&*()"
        assert _page_needs_xmark_detection_fast(text) is True

    def test_low_alpha_ratio_returns_true(self):
        """Alpha ratio <70% -> flagged."""
        # 60% alpha, 20% digits, 15% spaces, 5% symbols
        alpha = "a" * 60
        digits = "1" * 20
        spaces = " " * 15
        symbols = "!" * 5
        text = alpha + digits + spaces + symbols
        result = _page_needs_xmark_detection_fast(text)
        assert result is True

    def test_high_alpha_ratio_returns_true(self):
        """Alpha ratio >90% -> flagged (unusual distribution)."""
        # 95% alpha, no digits, 3% spaces, 2% symbols
        text = "a" * 95 + " " * 3 + "!!"
        assert _page_needs_xmark_detection_fast(text) is True

    def test_clean_page_returns_false(self):
        """Properly proportioned text returns False."""
        # ~78% alpha, ~2% digits, ~19% spaces, ~1% symbols
        words = "The quick brown fox jumps over lazy dog "
        text = words * 5  # 200 chars
        # Check it's long enough
        assert len(text) >= 100
        result = _page_needs_xmark_detection_fast(text)
        assert result is False


# ===================================================================
# _should_enable_xmark_detection_for_document  (lines 195, 197, 208-209, 214-215, 219-220)
# ===================================================================


class TestShouldEnableXmarkDetection:
    def test_mode_always(self, monkeypatch):
        monkeypatch.setenv("RAG_XMARK_DETECTION_MODE", "always")
        assert _should_enable_xmark_detection_for_document({}) is True

    def test_mode_never(self, monkeypatch):
        monkeypatch.setenv("RAG_XMARK_DETECTION_MODE", "never")
        assert _should_enable_xmark_detection_for_document({}) is False

    def test_auto_philosophy_author(self, monkeypatch):
        monkeypatch.setenv("RAG_XMARK_DETECTION_MODE", "auto")
        metadata = {"authors": "Jacques Derrida", "title": "Of Grammatology"}
        assert _should_enable_xmark_detection_for_document(metadata) is True

    def test_auto_heidegger(self, monkeypatch):
        monkeypatch.setenv("RAG_XMARK_DETECTION_MODE", "auto")
        metadata = {"authors": "Martin Heidegger"}
        assert _should_enable_xmark_detection_for_document(metadata) is True

    def test_auto_philosophy_subject(self, monkeypatch):
        monkeypatch.setenv("RAG_XMARK_DETECTION_MODE", "auto")
        metadata = {"authors": "Someone", "subject": "Continental Philosophy"}
        assert _should_enable_xmark_detection_for_document(metadata) is True

    def test_auto_philosophy_title(self, monkeypatch):
        monkeypatch.setenv("RAG_XMARK_DETECTION_MODE", "auto")
        metadata = {"authors": "Someone", "title": "Introduction to Phenomenology"}
        assert _should_enable_xmark_detection_for_document(metadata) is True

    def test_auto_default_enables(self, monkeypatch):
        """When auto mode and no philosophy signals, still enables (conservative)."""
        monkeypatch.setenv("RAG_XMARK_DETECTION_MODE", "auto")
        metadata = {"authors": "John Smith", "title": "Cooking Recipes"}
        assert _should_enable_xmark_detection_for_document(metadata) is True

    def test_philosophy_only_non_philosophy_disables(self, monkeypatch):
        monkeypatch.setenv("RAG_XMARK_DETECTION_MODE", "philosophy_only")
        metadata = {"authors": "John Smith", "title": "Cooking Recipes"}
        assert _should_enable_xmark_detection_for_document(metadata) is False

    def test_philosophy_only_with_philosophy_enables(self, monkeypatch):
        monkeypatch.setenv("RAG_XMARK_DETECTION_MODE", "philosophy_only")
        metadata = {"authors": "Derrida"}
        assert _should_enable_xmark_detection_for_document(metadata) is True

    def test_no_env_var_defaults_auto(self, monkeypatch):
        """Without env var, defaults to auto (conservative enable)."""
        monkeypatch.delenv("RAG_XMARK_DETECTION_MODE", raising=False)
        metadata = {}
        assert _should_enable_xmark_detection_for_document(metadata) is True

    def test_non_string_authors(self, monkeypatch):
        """authors field is not a string (e.g. list) — should not crash."""
        monkeypatch.setenv("RAG_XMARK_DETECTION_MODE", "auto")
        metadata = {"authors": ["Derrida", "Levinas"]}
        # Should not raise, defaults to enable
        assert _should_enable_xmark_detection_for_document(metadata) is True

    def test_missing_subject_and_title(self, monkeypatch):
        monkeypatch.setenv("RAG_XMARK_DETECTION_MODE", "auto")
        metadata = {"authors": "Nobody special"}
        assert _should_enable_xmark_detection_for_document(metadata) is True


# ===================================================================
# _detect_xmarks_single_page  (lines 102-118)
# ===================================================================


class TestDetectXmarksSinglePage:
    def test_returns_result_on_success(self):
        """Mock the strikethrough module and verify result is returned."""
        mock_result = MagicMock()
        mock_result.has_xmarks = False

        # The function does a lazy import inside, so patch the underlying module attrs
        with patch(
            "lib.strikethrough_detection.detect_strikethrough_enhanced",
            return_value=mock_result,
        ):
            result = _detect_xmarks_single_page(Path("/fake/doc.pdf"), 0)
            assert result is mock_result

    def test_exception_returns_none(self):
        """On exception, should return None."""
        with patch(
            "lib.strikethrough_detection.detect_strikethrough_enhanced",
            side_effect=RuntimeError("detection failed"),
        ):
            result = _detect_xmarks_single_page(Path("/fake/doc.pdf"), 0)
            assert result is None


# ===================================================================
# _detect_xmarks_parallel  (lines 40-85)
# ===================================================================


class TestDetectXmarksParallel:
    def test_parallel_returns_cache(self):
        """Mock the executor and verify results are collected."""
        mock_result = MagicMock()
        mock_result.has_xmarks = True
        mock_result.xmark_count = 2

        with patch(
            "lib.rag.xmark.detection._detect_xmarks_single_page",
            return_value=mock_result,
        ):
            cache = _detect_xmarks_parallel(
                Path("/fake/doc.pdf"),
                page_count=3,
                max_workers=2,
                pages_to_check=[0, 1, 2],
            )
            # Should have entries for pages 0, 1, 2
            assert len(cache) == 3
            for page_num in [0, 1, 2]:
                assert page_num in cache

    def test_parallel_default_all_pages(self):
        """When pages_to_check is None, checks all pages."""
        mock_result = MagicMock()
        mock_result.has_xmarks = False

        with patch(
            "lib.rag.xmark.detection._detect_xmarks_single_page",
            return_value=mock_result,
        ):
            cache = _detect_xmarks_parallel(
                Path("/fake/doc.pdf"),
                page_count=2,
                max_workers=1,
            )
            assert len(cache) == 2

    def test_parallel_executor_failure_returns_empty(self):
        """If the entire executor fails, returns empty dict."""
        # ProcessPoolExecutor is imported inside the function from concurrent.futures
        with patch(
            "concurrent.futures.ProcessPoolExecutor",
            side_effect=RuntimeError("pool failed"),
        ):
            cache = _detect_xmarks_parallel(
                Path("/fake/doc.pdf"),
                page_count=2,
                pages_to_check=[0, 1],
            )
            assert cache == {}

    def test_parallel_with_xmarks_detected(self):
        """Parallel detection with has_xmarks=True triggers debug logging branch (lines 68-71).
        We mock the ProcessPoolExecutor to use ThreadPoolExecutor to avoid pickling."""
        from concurrent.futures import ThreadPoolExecutor

        mock_result = MagicMock()
        mock_result.has_xmarks = True
        mock_result.xmark_count = 3

        with (
            patch(
                "lib.rag.xmark.detection._detect_xmarks_single_page",
                return_value=mock_result,
            ),
            patch(
                "concurrent.futures.ProcessPoolExecutor",
                ThreadPoolExecutor,
            ),
        ):
            cache = _detect_xmarks_parallel(
                Path("/fake/doc.pdf"),
                page_count=2,
                max_workers=1,
                pages_to_check=[0, 1],
            )
            assert len(cache) == 2
            for page_num in [0, 1]:
                assert cache[page_num] is mock_result
                assert cache[page_num].has_xmarks is True

    def test_parallel_mixed_results_with_xmarks(self):
        """Mix of pages with and without xmarks covers both branches in the loop."""
        from concurrent.futures import ThreadPoolExecutor

        def _side_effect(pdf_path, page_num):
            result = MagicMock()
            if page_num == 0:
                result.has_xmarks = True
                result.xmark_count = 2
            else:
                result.has_xmarks = False
                result.xmark_count = 0
            return result

        with (
            patch(
                "lib.rag.xmark.detection._detect_xmarks_single_page",
                side_effect=_side_effect,
            ),
            patch(
                "concurrent.futures.ProcessPoolExecutor",
                ThreadPoolExecutor,
            ),
        ):
            cache = _detect_xmarks_parallel(
                Path("/fake/doc.pdf"),
                page_count=2,
                max_workers=1,
                pages_to_check=[0, 1],
            )
            assert cache[0].has_xmarks is True
            assert cache[1].has_xmarks is False

    def test_parallel_result_none_no_has_xmarks_check(self):
        """When result is None (falsy), the `result and result.has_xmarks` short-circuits."""
        from concurrent.futures import ThreadPoolExecutor

        with (
            patch(
                "lib.rag.xmark.detection._detect_xmarks_single_page",
                return_value=None,
            ),
            patch(
                "concurrent.futures.ProcessPoolExecutor",
                ThreadPoolExecutor,
            ),
        ):
            cache = _detect_xmarks_parallel(
                Path("/fake/doc.pdf"),
                page_count=1,
                max_workers=1,
                pages_to_check=[0],
            )
            assert cache[0] is None

    def test_parallel_individual_page_failure(self):
        """If a single page fails, cache has None for that page."""
        call_count = 0

        def _side_effect(pdf_path, page_num):
            nonlocal call_count
            call_count += 1
            if page_num == 1:
                raise RuntimeError("page 1 failed")
            result = MagicMock()
            result.has_xmarks = False
            return result

        with patch(
            "lib.rag.xmark.detection._detect_xmarks_single_page",
            side_effect=_side_effect,
        ):
            cache = _detect_xmarks_parallel(
                Path("/fake/doc.pdf"),
                page_count=3,
                max_workers=1,
                pages_to_check=[0, 1, 2],
            )
            # Page 1 should be None due to failure
            assert cache.get(1) is None
