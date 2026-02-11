"""Tests for adaptive resolution renderer."""

from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from lib.rag.resolution.models import DPIDecision, PageAnalysis, RegionDPI
from lib.rag.resolution.renderer import (
    AdaptiveRenderResult,
    pdf_to_pixel,
    pixel_to_pdf,
    render_page_adaptive,
    render_region,
)

pytestmark = pytest.mark.unit

# Shared fake PIL image for mocked pixmap conversions
_FAKE_IMAGE = Image.new("RGB", (100, 100))


def _make_page_analysis(
    page_dpi=150,
    confidence=0.8,
    has_small_text=False,
    regions=None,
    min_size=10.0,
):
    """Helper to create a PageAnalysis with sensible defaults."""
    return PageAnalysis(
        page_num=0,
        dominant_size=12.0,
        min_size=min_size,
        max_size=24.0,
        has_small_text=has_small_text,
        page_dpi=DPIDecision(
            dpi=page_dpi,
            confidence=confidence,
            reason="test",
            font_size_pt=12.0,
            estimated_pixel_height=20.0,
        ),
        regions=regions or [],
    )


def _mock_page(width=612, height=792):
    """Create a mock fitz.Page that returns a mock pixmap from get_pixmap."""
    page = MagicMock()
    page.rect = MagicMock()
    page.rect.x0 = 0
    page.rect.y0 = 0
    page.rect.x1 = width
    page.rect.y1 = height
    page.rect.width = width
    page.rect.height = height
    page.get_pixmap = MagicMock(return_value=MagicMock())
    return page


class TestCoordinateMapping:
    """Tests for pdf_to_pixel and pixel_to_pdf helpers."""

    def test_pdf_to_pixel_72dpi_identity(self):
        assert pdf_to_pixel(100.0, 72) == 100

    def test_pdf_to_pixel_150dpi(self):
        assert pdf_to_pixel(100.0, 150) == 208

    def test_pdf_to_pixel_300dpi(self):
        assert pdf_to_pixel(100.0, 300) == 417

    def test_pixel_to_pdf_72dpi_identity(self):
        assert pixel_to_pdf(100.0, 72) == pytest.approx(100.0)

    def test_pixel_to_pdf_300dpi(self):
        assert pixel_to_pdf(417.0, 300) == pytest.approx(100.08)

    def test_roundtrip_150dpi(self):
        original = 256.5
        pixel = pdf_to_pixel(original, 150)
        back = pixel_to_pdf(pixel, 150)
        assert abs(back - original) < 1.0


@patch("lib.rag.resolution.renderer._pixmap_to_pil", return_value=_FAKE_IMAGE)
class TestRenderRegion:
    """Tests for render_region function."""

    def test_renders_with_correct_clip(self, mock_pil):
        page = _mock_page()
        bbox = (72.0, 100.0, 200.0, 300.0)
        render_region(page, bbox, 300)
        page.get_pixmap.assert_called_once()

    def test_returns_pil_image(self, mock_pil):
        page = _mock_page()
        result = render_region(page, (0, 0, 100, 100), 150)
        assert isinstance(result, Image.Image)

    def test_clips_to_page_bounds(self, mock_pil):
        page = _mock_page(width=612, height=792)
        bbox = (500.0, 700.0, 700.0, 900.0)
        result = render_region(page, bbox, 150)
        assert result is not None

    def test_matrix_uses_correct_dpi(self, mock_pil):
        page = _mock_page()
        with patch("lib.rag.resolution.renderer.fitz") as mock_fitz:
            mock_fitz.Matrix.return_value = MagicMock()
            mock_fitz.Rect.return_value = MagicMock()
            render_region(page, (0, 0, 100, 100), 150)
            mock_fitz.Matrix.assert_called_once_with(150 / 72, 150 / 72)


@patch("lib.rag.resolution.renderer._pixmap_to_pil", return_value=_FAKE_IMAGE)
class TestRenderPageAdaptive:
    """Tests for render_page_adaptive function."""

    def test_renders_full_page_at_analysis_dpi(self, mock_pil):
        page = _mock_page()
        analysis = _make_page_analysis(page_dpi=200)
        result = render_page_adaptive(page, analysis)
        assert isinstance(result, AdaptiveRenderResult)
        assert result.page_dpi == 200

    def test_page_dpi_capped_at_300(self, mock_pil):
        page = _mock_page()
        analysis = _make_page_analysis(page_dpi=450)
        result = render_page_adaptive(page, analysis)
        assert result.page_dpi == 300

    def test_no_regions_when_no_small_text(self, mock_pil):
        page = _mock_page()
        analysis = _make_page_analysis(page_dpi=150, has_small_text=False)
        result = render_page_adaptive(page, analysis)
        assert result.region_images == []

    def test_region_rerender_when_higher_dpi(self, mock_pil):
        region = RegionDPI(
            bbox=(50.0, 600.0, 200.0, 700.0),
            dpi_decision=DPIDecision(
                dpi=500,
                confidence=0.9,
                reason="small text",
                font_size_pt=6.0,
                estimated_pixel_height=8.0,
            ),
            region_type="footnote",
        )
        page = _mock_page()
        analysis = _make_page_analysis(
            page_dpi=150, has_small_text=True, regions=[region]
        )
        result = render_page_adaptive(page, analysis)
        assert len(result.region_images) == 1
        assert result.region_images[0][0] is region

    def test_region_dpi_capped_at_600(self, mock_pil):
        region = RegionDPI(
            bbox=(50.0, 600.0, 200.0, 700.0),
            dpi_decision=DPIDecision(
                dpi=800,
                confidence=0.9,
                reason="tiny text",
                font_size_pt=4.0,
                estimated_pixel_height=5.0,
            ),
            region_type="footnote",
        )
        page = _mock_page()
        analysis = _make_page_analysis(
            page_dpi=150, has_small_text=True, regions=[region]
        )
        result = render_page_adaptive(page, analysis)
        assert len(result.region_images) == 1

    def test_skips_region_when_dpi_not_higher(self, mock_pil):
        region = RegionDPI(
            bbox=(50.0, 600.0, 200.0, 700.0),
            dpi_decision=DPIDecision(
                dpi=100,
                confidence=0.9,
                reason="normal text",
                font_size_pt=12.0,
                estimated_pixel_height=20.0,
            ),
            region_type="body",
        )
        page = _mock_page()
        analysis = _make_page_analysis(
            page_dpi=150, has_small_text=True, regions=[region]
        )
        result = render_page_adaptive(page, analysis)
        assert result.region_images == []

    def test_scanned_pdf_fallback_300dpi(self, mock_pil):
        page = _mock_page()
        analysis = _make_page_analysis(page_dpi=300, confidence=0.0)
        result = render_page_adaptive(page, analysis)
        assert result.page_dpi == 300

    def test_metadata_has_timing(self, mock_pil):
        page = _mock_page()
        analysis = _make_page_analysis(page_dpi=150)
        result = render_page_adaptive(page, analysis)
        assert "render_time_ms" in result.metadata
        assert isinstance(result.metadata["render_time_ms"], float)

    def test_page_image_is_pil(self, mock_pil):
        page = _mock_page()
        analysis = _make_page_analysis(page_dpi=150)
        result = render_page_adaptive(page, analysis)
        assert isinstance(result.page_image, Image.Image)
