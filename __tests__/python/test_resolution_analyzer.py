"""Tests for adaptive resolution DPI computation and font analysis engine."""

from unittest.mock import MagicMock, patch


class TestComputeOptimalDPI:
    """Test DPI computation from font size."""

    def test_common_12pt_font(self):
        from lib.rag.resolution.analyzer import compute_optimal_dpi

        result = compute_optimal_dpi(12.0)
        assert result.dpi == 150
        assert result.confidence == 1.0
        assert result.font_size_pt == 12.0
        assert result.dpi % 50 == 0

    def test_common_10pt_font(self):
        from lib.rag.resolution.analyzer import compute_optimal_dpi

        result = compute_optimal_dpi(10.0)
        assert result.dpi == 200
        assert result.confidence == 1.0

    def test_small_7pt_font(self):
        from lib.rag.resolution.analyzer import compute_optimal_dpi

        result = compute_optimal_dpi(7.0)
        assert result.dpi == 300
        assert result.confidence == 1.0

    def test_tiny_5pt_font(self):
        from lib.rag.resolution.analyzer import compute_optimal_dpi

        result = compute_optimal_dpi(5.0)
        assert result.dpi == 400
        assert result.confidence == 1.0

    def test_zero_font_size_returns_default(self):
        from lib.rag.resolution.analyzer import compute_optimal_dpi

        result = compute_optimal_dpi(0)
        assert result.dpi == 300
        assert result.confidence == 0.0
        assert result.reason == "invalid_font_size"

    def test_negative_font_size_returns_default(self):
        from lib.rag.resolution.analyzer import compute_optimal_dpi

        result = compute_optimal_dpi(-5.0)
        assert result.dpi == 300
        assert result.confidence == 0.0
        assert result.reason == "invalid_font_size"

    def test_very_small_font_clamped_to_ceiling(self):
        from lib.rag.resolution.analyzer import compute_optimal_dpi

        result = compute_optimal_dpi(1.0)
        assert result.dpi == 600
        assert result.confidence < 1.0

    def test_very_large_font_clamped_to_floor(self):
        from lib.rag.resolution.analyzer import compute_optimal_dpi

        result = compute_optimal_dpi(100.0)
        # 28 * 72 / 100 = 20.16 -> quantized to 0, clamped to DPI_FLOOR=72
        assert result.dpi == 72  # floor clamp overrides quantization

    def test_dpi_always_quantized_to_50(self):
        from lib.rag.resolution.analyzer import compute_optimal_dpi

        for size in [5, 6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20]:
            result = compute_optimal_dpi(float(size))
            assert result.dpi % 50 == 0, (
                f"DPI {result.dpi} not multiple of 50 for {size}pt"
            )

    def test_dpi_within_bounds(self):
        from lib.rag.resolution.analyzer import compute_optimal_dpi

        for size in range(1, 21):
            result = compute_optimal_dpi(float(size))
            assert 50 <= result.dpi <= 600, (
                f"DPI {result.dpi} out of bounds for {size}pt"
            )

    def test_estimated_pixel_height_computed(self):
        from lib.rag.resolution.analyzer import compute_optimal_dpi

        result = compute_optimal_dpi(10.0)
        expected = 10.0 * result.dpi / 72
        assert abs(result.estimated_pixel_height - expected) < 0.01


class TestDPIDecisionModel:
    """Test DPIDecision dataclass."""

    def test_create_dpi_decision(self):
        from lib.rag.resolution.models import DPIDecision

        d = DPIDecision(
            dpi=300,
            confidence=1.0,
            reason="computed",
            font_size_pt=10.0,
            estimated_pixel_height=41.7,
        )
        assert d.dpi == 300
        assert d.confidence == 1.0

    def test_region_dpi_model(self):
        from lib.rag.resolution.models import DPIDecision, RegionDPI

        decision = DPIDecision(
            dpi=400,
            confidence=0.8,
            reason="clamped",
            font_size_pt=5.0,
            estimated_pixel_height=27.8,
        )
        region = RegionDPI(
            bbox=(0.0, 0.0, 100.0, 50.0), dpi_decision=decision, region_type="footnote"
        )
        assert region.region_type == "footnote"
        assert region.dpi_decision.dpi == 400

    def test_page_analysis_model(self):
        from lib.rag.resolution.models import DPIDecision, PageAnalysis

        decision = DPIDecision(
            dpi=200,
            confidence=1.0,
            reason="computed",
            font_size_pt=10.0,
            estimated_pixel_height=27.8,
        )
        pa = PageAnalysis(
            page_num=1,
            dominant_size=10.0,
            min_size=6.0,
            max_size=18.0,
            has_small_text=True,
            page_dpi=decision,
            regions=[],
        )
        assert pa.page_num == 1
        assert pa.has_small_text is True


class TestAnalyzePageFonts:
    """Test page-level font analysis."""

    def _make_mock_page(self, sizes):
        """Create a mock fitz.Page with given font sizes."""
        spans = [{"size": s} for s in sizes]
        lines = [{"spans": spans}]
        blocks = [{"type": 0, "lines": lines}]
        page = MagicMock()
        page.get_text.return_value = {"blocks": blocks}
        return page

    def test_extracts_dominant_size_as_median(self):
        from lib.rag.resolution.analyzer import analyze_page_fonts

        page = self._make_mock_page([8.0, 10.0, 10.0, 10.0, 18.0])
        result = analyze_page_fonts(page)
        assert result.dominant_size == 10.0

    def test_min_max_sizes(self):
        from lib.rag.resolution.analyzer import analyze_page_fonts

        page = self._make_mock_page([6.0, 10.0, 10.0, 18.0])
        result = analyze_page_fonts(page)
        assert result.min_size == 6.0
        assert result.max_size == 18.0

    def test_has_small_text_when_min_below_threshold(self):
        from lib.rag.resolution.analyzer import analyze_page_fonts

        # min=5.0, dominant(median)=10.0, 5 < 10*0.7=7 → True
        page = self._make_mock_page([5.0, 10.0, 10.0, 10.0])
        result = analyze_page_fonts(page)
        assert result.has_small_text is True

    def test_no_small_text_when_min_near_dominant(self):
        from lib.rag.resolution.analyzer import analyze_page_fonts

        page = self._make_mock_page([9.0, 10.0, 10.0, 11.0])
        result = analyze_page_fonts(page)
        assert result.has_small_text is False

    def test_empty_page_returns_fallback(self):
        from lib.rag.resolution.analyzer import analyze_page_fonts

        page = MagicMock()
        page.get_text.return_value = {"blocks": []}
        result = analyze_page_fonts(page)
        assert result.dominant_size == 0
        assert result.page_dpi.dpi == 300
        assert result.page_dpi.confidence == 0.0
        assert result.page_dpi.reason == "no_text_layer"

    def test_image_only_blocks_ignored(self):
        from lib.rag.resolution.analyzer import analyze_page_fonts

        page = MagicMock()
        page.get_text.return_value = {"blocks": [{"type": 1}]}  # image block
        result = analyze_page_fonts(page)
        assert result.dominant_size == 0
        assert result.page_dpi.confidence == 0.0

    def test_page_dpi_computed_from_dominant(self):
        from lib.rag.resolution.analyzer import analyze_page_fonts

        page = self._make_mock_page([10.0, 10.0, 10.0])
        result = analyze_page_fonts(page)
        assert result.page_dpi.dpi == 200  # 28*72/10 = 201.6 → quantized 200


class TestAnalyzeDocumentFonts:
    """Test document-level font analysis."""

    @patch("lib.rag.resolution.analyzer.fitz")
    def test_analyzes_all_pages(self, mock_fitz):
        from lib.rag.resolution.analyzer import analyze_document_fonts

        # Mock a 3-page document
        mock_doc = MagicMock()
        mock_pages = []
        for i in range(3):
            page = MagicMock()
            spans = [{"size": 10.0}]
            lines = [{"spans": spans}]
            blocks = [{"type": 0, "lines": lines}]
            page.get_text.return_value = {"blocks": blocks}
            mock_pages.append(page)
        mock_doc.__len__ = lambda self: 3
        mock_doc.__iter__ = lambda self: iter(mock_pages)
        mock_doc.__getitem__ = lambda self, i: mock_pages[i]
        mock_doc.page_count = 3
        mock_fitz.open.return_value.__enter__ = lambda s: mock_doc
        mock_fitz.open.return_value.__exit__ = lambda s, *a: None

        result = analyze_document_fonts("/fake/path.pdf")
        assert len(result) == 3
        assert all(isinstance(v.page_dpi.dpi, int) for v in result.values())

    @patch("lib.rag.resolution.analyzer.fitz")
    def test_page_range_subset(self, mock_fitz):
        from lib.rag.resolution.analyzer import analyze_document_fonts

        mock_doc = MagicMock()
        mock_pages = []
        for i in range(5):
            page = MagicMock()
            spans = [{"size": 10.0}]
            lines = [{"spans": spans}]
            blocks = [{"type": 0, "lines": lines}]
            page.get_text.return_value = {"blocks": blocks}
            mock_pages.append(page)
        mock_doc.__len__ = lambda self: 5
        mock_doc.__getitem__ = lambda self, i: mock_pages[i]
        mock_doc.page_count = 5
        mock_fitz.open.return_value.__enter__ = lambda s: mock_doc
        mock_fitz.open.return_value.__exit__ = lambda s, *a: None

        result = analyze_document_fonts("/fake/path.pdf", page_range=(1, 3))
        assert len(result) == 3
        assert set(result.keys()) == {1, 2, 3}
