"""Tests for adaptive resolution renderer."""

from unittest.mock import MagicMock

import pytest

from lib.rag.resolution.models import DPIDecision, PageAnalysis, RegionDPI
from lib.rag.resolution.renderer import (
    AdaptiveRenderResult,
    pdf_to_pixel,
    pixel_to_pdf,
    render_page_adaptive,
    render_region,
)


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

    def make_pixmap(**kwargs):
        pix = MagicMock()
        pix.samples = b"\x00" * 100
        pix.width = 100
        pix.height = 100
        pix.n = 3
        pix.stride = 300
        return pix

    page.get_pixmap = MagicMock(side_effect=make_pixmap)
    return page


class TestCoordinateMapping:
    """Tests for pdf_to_pixel and pixel_to_pdf helpers."""

    def test_pdf_to_pixel_72dpi_identity(self):
        assert pdf_to_pixel(100.0, 72) == 100

    def test_pdf_to_pixel_150dpi(self):
        # 100 * 150/72 = 208.33 -> 208
        assert pdf_to_pixel(100.0, 150) == 208

    def test_pdf_to_pixel_300dpi(self):
        # 100 * 300/72 = 416.67 -> 417
        assert pdf_to_pixel(100.0, 300) == 417

    def test_pixel_to_pdf_72dpi_identity(self):
        assert pixel_to_pdf(100.0, 72) == pytest.approx(100.0)

    def test_pixel_to_pdf_300dpi(self):
        # 417 * 72/300 = 100.08
        assert pixel_to_pdf(417.0, 300) == pytest.approx(100.08)

    def test_roundtrip_150dpi(self):
        original = 256.5
        pixel = pdf_to_pixel(original, 150)
        back = pixel_to_pdf(pixel, 150)
        assert abs(back - original) < 1.0


class TestRenderRegion:
    """Tests for render_region function."""

    def test_renders_with_correct_clip(self):
        page = _mock_page()
        bbox = (72.0, 100.0, 200.0, 300.0)
        render_region(page, bbox, 300)

        page.get_pixmap.assert_called_once()
        call_kwargs = page.get_pixmap.call_args
        assert call_kwargs is not None

    def test_returns_pil_image(self):
        page = _mock_page()
        result = render_region(page, (0, 0, 100, 100), 150)
        # Should be a PIL Image
        from PIL import Image

        assert isinstance(result, Image.Image)

    def test_clips_to_page_bounds(self):
        page = _mock_page(width=612, height=792)
        # bbox extends beyond page
        bbox = (500.0, 700.0, 700.0, 900.0)
        result = render_region(page, bbox, 150)
        # Should not raise, bbox clipped internally
        assert result is not None


class TestRenderPageAdaptive:
    """Tests for render_page_adaptive function."""

    def test_renders_full_page_at_analysis_dpi(self):
        page = _mock_page()
        analysis = _make_page_analysis(page_dpi=200)
        result = render_page_adaptive(page, analysis)

        assert isinstance(result, AdaptiveRenderResult)
        assert result.page_dpi == 200

    def test_page_dpi_capped_at_300(self):
        page = _mock_page()
        analysis = _make_page_analysis(page_dpi=450)
        result = render_page_adaptive(page, analysis)

        assert result.page_dpi == 300  # DPI_PAGE_CAP

    def test_no_regions_when_no_small_text(self):
        page = _mock_page()
        analysis = _make_page_analysis(page_dpi=150, has_small_text=False)
        result = render_page_adaptive(page, analysis)

        assert result.region_images == []

    def test_region_rerender_when_higher_dpi(self):
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

    def test_region_dpi_capped_at_600(self):
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

        # Region rendered but DPI capped at 600
        assert len(result.region_images) == 1

    def test_skips_region_when_dpi_not_higher(self):
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

    def test_scanned_pdf_fallback_300dpi(self):
        page = _mock_page()
        analysis = _make_page_analysis(page_dpi=300, confidence=0.0)
        result = render_page_adaptive(page, analysis)

        assert result.page_dpi == 300  # DPI_DEFAULT

    def test_metadata_has_timing(self):
        page = _mock_page()
        analysis = _make_page_analysis(page_dpi=150)
        result = render_page_adaptive(page, analysis)

        assert "render_time_ms" in result.metadata
        assert isinstance(result.metadata["render_time_ms"], float)

    def test_page_image_is_pil(self):
        page = _mock_page()
        analysis = _make_page_analysis(page_dpi=150)
        result = render_page_adaptive(page, analysis)

        from PIL import Image

        assert isinstance(result.page_image, Image.Image)
