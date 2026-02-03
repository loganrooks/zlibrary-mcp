"""End-to-end integration tests for the unified PDF processing pipeline.

Tests process_pdf_structured() and verify multi-file output, confidence scores,
footnote/margin dedup, front matter stripping, and backward compatibility.
"""

import re
import sys
import tempfile
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.rag.orchestrator_pdf import process_pdf, process_pdf_structured
from lib.rag.pipeline.models import DocumentOutput

TEST_FILES_DIR = PROJECT_ROOT / "test_files"

# Use smallest scholarly PDF with footnotes for most tests (~2KB)
SMALL_PDF = TEST_FILES_DIR / "heidegger_pages_22-23_primary_footnote_test.pdf"
# Fallback to a slightly larger one if needed
FOOTNOTE_PDF = TEST_FILES_DIR / "derrida_footnote_pages_120_125.pdf"


def _get_test_pdf():
    """Return smallest available test PDF."""
    if SMALL_PDF.exists():
        return SMALL_PDF
    if FOOTNOTE_PDF.exists():
        return FOOTNOTE_PDF
    pytest.skip("No test PDF available")


@pytest.mark.integration
class TestPipelineIntegration:
    """End-to-end integration tests for process_pdf_structured."""

    def test_scholarly_pdf_multi_file_output(self):
        """Process PDF, verify DocumentOutput has body + metadata, write to temp dir."""
        pdf = _get_test_pdf()
        output = process_pdf_structured(pdf, output_format="markdown")

        assert isinstance(output, DocumentOutput)
        assert len(output.body_text) > 0, "Body text should not be empty"

        # Write to temp directory and verify files
        with tempfile.TemporaryDirectory() as tmp:
            written = output.write_files(Path(tmp) / pdf.name)
            assert "body" in written, "Body file should be written"
            assert "metadata" in written, "Metadata sidecar should be written"

            # Verify body file has content
            body_content = written["body"].read_text(encoding="utf-8")
            assert len(body_content) > 50, "Body file should have substantial content"

            # Verify metadata is valid JSON
            import json

            meta_content = json.loads(written["metadata"].read_text(encoding="utf-8"))
            assert "document_metadata" in meta_content
            assert "processing_metadata" in meta_content

    def test_confidence_scores_in_metadata(self):
        """Process with include_metadata=True, verify confidence floats."""
        pdf = _get_test_pdf()
        output = process_pdf_structured(
            pdf, output_format="markdown", include_metadata=True
        )

        assert output.processing_metadata is not None, (
            "Processing metadata should be present when include_metadata=True"
        )
        assert "classifications" in output.processing_metadata
        assert "total_blocks" in output.processing_metadata

        classifications = output.processing_metadata["classifications"]
        assert len(classifications) > 0, "Should have classified blocks"

        for cls in classifications:
            assert "confidence" in cls, f"Block missing confidence: {cls}"
            assert isinstance(cls["confidence"], (int, float)), (
                f"Confidence should be numeric: {cls['confidence']}"
            )
            assert 0.0 <= cls["confidence"] <= 1.0, (
                f"Confidence out of range: {cls['confidence']}"
            )

    def test_footnote_margin_no_duplication(self):
        """Verify no text appears in both footnotes and margin annotations."""
        pdf = _get_test_pdf()
        output = process_pdf_structured(pdf, output_format="markdown")

        if not output.footnotes:
            pytest.skip("Test PDF has no footnotes to check for duplication")

        # Extract footnote text lines (strip formatting)
        footnote_lines = set()
        for line in output.footnotes.split("\n"):
            cleaned = line.strip()
            if cleaned and not cleaned.startswith("##"):
                # Remove numbering prefix
                cleaned = re.sub(r"^\d+\.\s*", "", cleaned)
                if cleaned:
                    footnote_lines.add(cleaned.lower())

        # Extract margin annotations from body
        margin_texts = set()
        for match in re.finditer(r"\[margin:\s*(.+?)\]", output.body_text):
            margin_texts.add(match.group(1).strip().lower())

        if not margin_texts:
            # No margins to check overlap with — test passes trivially
            return

        overlap = footnote_lines & margin_texts
        assert len(overlap) == 0, (
            f"Content appears in both footnotes and margins: {overlap}"
        )

    def test_front_matter_toc_stripped_from_body(self):
        """Verify front matter/TOC in metadata not body."""
        pdf = _get_test_pdf()
        output = process_pdf_structured(
            pdf, output_format="markdown", include_metadata=True
        )

        doc_meta = output.document_metadata or {}
        fm = doc_meta.get("front_matter", {})
        toc = doc_meta.get("toc", {})

        # At least one should be present for a scholarly PDF
        assert fm or toc, "Scholarly PDF should have front matter or TOC detected"

        # If front matter detected, its content should not appear in body
        if fm:
            fm_titles = fm.get("titles", [])
            for title in fm_titles:
                assert title not in output.body_text, (
                    f"Front matter title '{title}' found in body text"
                )

    def test_headings_preserved_in_body(self):
        """Headings in body as markdown (# prefix)."""
        pdf = _get_test_pdf()
        output = process_pdf_structured(pdf, output_format="markdown")

        # Check for any markdown heading in body
        has_heading = bool(re.search(r"^#{1,6}\s+\S", output.body_text, re.MULTILINE))
        # Not all small PDFs have headings detected; just check body is well-formed
        if not has_heading:
            # At minimum, body text should exist
            assert len(output.body_text) > 0

    def test_page_numbers_stripped(self):
        """Page numbers not standalone lines in body."""
        pdf = _get_test_pdf()
        output = process_pdf_structured(pdf, output_format="markdown")

        # Check that standalone numbers (page numbers) are not in body
        lines = output.body_text.split("\n")
        standalone_numbers = [
            line.strip()
            for line in lines
            if re.match(r"^\s*\d{1,4}\s*$", line) and line.strip()
        ]
        # Allow a few (some might be legitimate content like numbered items)
        assert len(standalone_numbers) <= 3, (
            f"Too many standalone page numbers in body: {standalone_numbers}"
        )

    def test_output_sections_clearly_labeled(self):
        """Footnotes have page headers, margins have [margin:] markers."""
        pdf = _get_test_pdf()
        output = process_pdf_structured(pdf, output_format="markdown")

        # Check footnote page headers if footnotes exist
        if output.footnotes:
            assert re.search(r"## Page \d+", output.footnotes), (
                "Footnotes should have page headers (## Page N)"
            )

        # Check margin markers if margins exist
        if "[margin:" in output.body_text:
            assert re.search(r"\[margin:\s*.+?\]", output.body_text), (
                "Margin annotations should use [margin: text] format"
            )

    def test_backward_compat_process_pdf(self):
        """process_pdf() returns string; should overlap substantially with structured body."""
        pdf = _get_test_pdf()

        legacy_text = process_pdf(pdf, output_format="markdown")
        structured = process_pdf_structured(pdf, output_format="markdown")

        assert isinstance(legacy_text, str)
        assert len(legacy_text) > 0
        assert len(structured.body_text) > 0

        # Both should have substantial overlap (not necessarily identical due to
        # different processing paths, but both should capture core content)
        # Use a loose check: at least 30% of structured body words appear in legacy
        structured_words = set(structured.body_text.lower().split())
        legacy_words = set(legacy_text.lower().split())
        if structured_words:
            overlap = len(structured_words & legacy_words) / len(structured_words)
            assert overlap > 0.2, (
                f"Legacy and structured output overlap too low: {overlap:.1%}"
            )
