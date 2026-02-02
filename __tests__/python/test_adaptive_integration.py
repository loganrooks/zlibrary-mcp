"""Integration tests for adaptive DPI pipeline (Phase 10-03)."""

import logging
import fitz
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from lib.rag.resolution.analyzer import analyze_document_fonts
from lib.rag.resolution.models import DPIDecision, PageAnalysis


@pytest.fixture
def text_pdf(tmp_path):
    """Create a minimal text-layer PDF with 12pt body text."""
    pdf_path = tmp_path / "text_body.pdf"
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        # 12pt body text
        writer = fitz.TextWriter(page.rect)
        writer.append((72, 100), f"Page {i+1} body text in twelve point font size for testing.", fontsize=12)
        # 8pt footnote
        writer.append((72, 700), f"1. This is a footnote in small text.", fontsize=8)
        writer.write_text(page)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def scanned_pdf(tmp_path):
    """Create a PDF with no text layer (simulates scanned)."""
    pdf_path = tmp_path / "scanned.pdf"
    doc = fitz.open()
    # Create page with only an image (no text layer)
    page = doc.new_page()
    # Draw a rectangle instead of text to simulate image-only
    shape = page.new_shape()
    shape.draw_rect(fitz.Rect(50, 50, 200, 200))
    shape.finish(color=(0, 0, 0))
    shape.commit()
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


class TestAdaptiveDPIAnalysis:
    """Test that font analysis produces adaptive DPI decisions."""

    def test_text_pdf_gets_adaptive_dpi(self, text_pdf):
        """Text-layer PDF should get per-page DPI decisions (not all 300)."""
        results = analyze_document_fonts(str(text_pdf))
        assert len(results) == 3, "Should analyze all 3 pages"

        for page_num, analysis in results.items():
            assert isinstance(analysis, PageAnalysis)
            assert isinstance(analysis.page_dpi, DPIDecision)
            assert analysis.page_dpi.dpi > 0
            assert analysis.page_dpi.confidence > 0

    def test_12pt_text_gets_lower_dpi(self, text_pdf):
        """12pt body text should get DPI below 300 (optimized for Tesseract)."""
        results = analyze_document_fonts(str(text_pdf))
        # 12pt text: optimal DPI = 28 * 72 / 12 = 168, quantized to 150 or 200
        for analysis in results.values():
            assert analysis.page_dpi.dpi <= 250, (
                f"12pt text should not need 300 DPI, got {analysis.page_dpi.dpi}"
            )

    def test_scanned_pdf_no_text_analysis(self, scanned_pdf):
        """PDF with no text layer should produce fallback DPI decisions."""
        results = analyze_document_fonts(str(scanned_pdf))
        for analysis in results.values():
            # No text layer -> fallback to DPI_DEFAULT=300
            assert analysis.page_dpi.dpi == 300
            assert analysis.page_dpi.confidence == 0.0
            assert analysis.page_dpi.reason == "no_text_layer"


class TestOCRRecoveryAdaptiveDPI:
    """Test that OCR recovery accepts and uses adaptive DPI."""

    def test_run_ocr_accepts_page_dpi_map(self):
        """run_ocr_on_pdf should accept page_dpi_map parameter."""
        from lib.rag.ocr.recovery import run_ocr_on_pdf
        import inspect
        sig = inspect.signature(run_ocr_on_pdf)
        assert "page_dpi_map" in sig.parameters
        assert sig.parameters["page_dpi_map"].default is None

    def test_ocr_stage_accepts_page_dpi_map(self):
        """_stage_3_ocr_recovery should accept page_dpi_map parameter."""
        from lib.rag.quality.ocr_stage import _stage_3_ocr_recovery
        import inspect
        sig = inspect.signature(_stage_3_ocr_recovery)
        assert "page_dpi_map" in sig.parameters
        assert sig.parameters["page_dpi_map"].default is None


class TestOrchestratorAdaptiveIntegration:
    """Test that the orchestrator wires adaptive DPI end-to-end."""

    def test_orchestrator_imports_resolution(self):
        """orchestrator_pdf should import adaptive resolution modules."""
        import lib.rag.orchestrator_pdf as orc
        # Verify the imports exist at module level
        assert hasattr(orc, 'analyze_document_fonts')
        assert hasattr(orc, 'DPIDecision')

    def test_adaptive_dpi_in_processing(self, text_pdf, caplog):
        """Processing a text PDF should trigger adaptive DPI analysis."""
        with caplog.at_level(logging.INFO):
            # Mock heavy dependencies to avoid full pipeline
            with patch("lib.rag.orchestrator_pdf._get_facade") as mock_facade:
                facade = MagicMock()
                facade.fitz = fitz
                facade.OCR_AVAILABLE = False
                facade.PYMUPDF_AVAILABLE = True
                facade.XMARK_AVAILABLE = False
                facade.detect_pdf_quality = lambda p: {
                    "quality_category": "DIGITAL_NATIVE",
                    "ocr_recommended": False,
                }
                facade.assess_pdf_ocr_quality = lambda p: {
                    "score": 0.9,
                    "has_text_layer": True,
                    "issues": [],
                    "recommendation": "use_existing",
                }
                facade._identify_and_remove_front_matter = lambda lines: (lines, "Test")
                facade._extract_and_format_toc = lambda lines, fmt: (lines, "")
                facade._format_pdf_markdown = lambda page, **kw: page.get_text()
                mock_facade.return_value = facade

                from lib.rag.orchestrator_pdf import process_pdf
                result = process_pdf(text_pdf, output_format="markdown")

            # Check that adaptive DPI analysis was logged
            assert any("Adaptive DPI" in msg for msg in caplog.messages), (
                f"Expected 'Adaptive DPI' log message, got: {caplog.messages}"
            )


class TestResolutionExports:
    """Test that resolution package exports all public symbols."""

    def test_all_exports_available(self):
        """All public symbols should be importable from resolution package."""
        from lib.rag.resolution import (
            compute_optimal_dpi,
            analyze_page_fonts,
            analyze_document_fonts,
            render_page_adaptive,
            render_region,
            DPIDecision,
            PageAnalysis,
            RegionDPI,
            AdaptiveRenderResult,
        )
        # Just verify they're all importable
        assert DPIDecision is not None
        assert PageAnalysis is not None
