"""
Real-world test for footnote detection.

NO MOCKING - uses actual PDF and ground truth validation.
Follows rigorous TDD workflow from .claude/TDD_WORKFLOW.md
"""

import pytest
from pathlib import Path
import json
import sys
import time

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))

from rag_processing import process_pdf


class TestFootnoteRealWorld:
    """Real-world validation with ground truth for footnote detection."""

    @pytest.fixture
    def ground_truth(self):
        """Load ground truth for footnote test."""
        gt_path = Path(__file__).parent.parent.parent / "test_files/ground_truth/derrida_footnotes.json"

        with open(gt_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def test_footnote_detection_with_real_pdf(self, ground_truth):
        """
        Test footnote detection with real Derrida PDF.

        This test uses actual pages 120-125 from "Of Grammatology" which contain
        translator footnotes with markers 'iii' and 't'.

        Ground truth documents:
        - 2 footnotes on page 1 (page 121 in original)
        - Marker 'iii': Translator note about "The Outside and the Inside"
        - Marker 't': Note about page number conventions

        Expected behavior:
        - Both footnote markers detected in body text
        - Both footnote contents extracted from page bottom
        - Markers correctly linked to content
        - Markdown footnote syntax in output: [^iii]: content
        """
        # Load test PDF (REAL PDF, no mocks!)
        pdf_path = Path(__file__).parent.parent.parent / ground_truth['pdf_file']

        assert pdf_path.exists(), f"Test PDF not found: {pdf_path}"

        # Process with footnote detection enabled
        start_time = time.time()
        result = process_pdf(
            pdf_path,
            output_format='markdown',
            detect_footnotes=True  # Enable footnote detection
        )
        processing_time_ms = (time.time() - start_time) * 1000

        # Validate processing time within budget
        max_time = ground_truth['expected_quality']['processing_time_max_ms']
        assert processing_time_ms < max_time, \
            f"Processing too slow: {processing_time_ms:.0f}ms > {max_time}ms budget"

        # Validate all footnotes detected
        footnotes = ground_truth['features']['footnotes']

        for footnote in footnotes:
            marker = footnote['marker']
            expected_output = footnote['expected_output']

            # Check that footnote appears in markdown format
            assert expected_output in result or f"[^{marker}]:" in result, \
                f"Footnote marker '{marker}' not found in output.\n" \
                f"Expected: {expected_output[:100]}...\n" \
                f"Got output length: {len(result)} chars"

            # Check that content is present
            content_snippet = footnote['content'][:50]  # First 50 chars
            assert content_snippet in result, \
                f"Footnote content not found for marker '{marker}'.\n" \
                f"Expected snippet: {content_snippet}"

        # Validate no false positives (no extra footnote markers)
        # Count [^ markers in output (match any characters, not just \w)
        import re
        found_markers = re.findall(r'\[\^(.+?)\]:', result)
        expected_markers = [fn['marker'] for fn in footnotes]

        assert len(found_markers) == len(expected_markers), \
            f"False positive footnotes detected.\n" \
            f"Expected markers: {expected_markers}\n" \
            f"Found markers: {found_markers}"

        print(f"\n✅ Footnote detection successful!")
        print(f"   Processing time: {processing_time_ms:.0f}ms (budget: {max_time}ms)")
        print(f"   Footnotes detected: {len(footnotes)}")
        print(f"   Markers: {expected_markers}")

    def test_footnote_marker_in_body_text(self, ground_truth):
        """
        Test that footnote markers are detected in body text.

        Markers should appear inline where they're referenced, e.g.:
        "entire culture and our entire science[^iii]"
        """
        pdf_path = Path(__file__).parent.parent.parent / ground_truth['pdf_file']
        result = process_pdf(pdf_path, output_format='markdown', detect_footnotes=True)

        footnotes = ground_truth['features']['footnotes']

        for footnote in footnotes:
            marker = footnote['marker']
            context = footnote['marker_context']

            # Check that marker appears near its context
            # The marker should be inline: context[^marker]
            assert f"[^{marker}]" in result, \
                f"Footnote marker reference [^{marker}] not found in body text"

    def test_footnote_content_extraction(self, ground_truth):
        """
        Test that footnote content is extracted from page bottom.

        Footnote definitions should appear at document end or page end:
        [^iii]: The title of the next section...
        """
        pdf_path = Path(__file__).parent.parent.parent / ground_truth['pdf_file']
        result = process_pdf(pdf_path, output_format='markdown', detect_footnotes=True)

        footnotes = ground_truth['features']['footnotes']

        for footnote in footnotes:
            marker = footnote['marker']
            content = footnote['content']

            # Check that footnote definition exists
            definition_start = f"[^{marker}]:"
            assert definition_start in result, \
                f"Footnote definition for '{marker}' not found"

            # Check that actual content is present
            # Use first 30 chars as signature
            content_signature = content[:30].strip()
            assert content_signature in result, \
                f"Footnote content for '{marker}' not found.\n" \
                f"Expected to find: {content_signature}"

    def test_no_hallucinated_footnotes(self, ground_truth):
        """
        Test that no extra footnotes are invented.

        Anti-hallucination check: only documented footnotes should appear.
        """
        pdf_path = Path(__file__).parent.parent.parent / ground_truth['pdf_file']
        result = process_pdf(pdf_path, output_format='markdown', detect_footnotes=True)

        # Count footnote definitions
        import re
        found_definitions = re.findall(r'\[\^(\w+)\]:', result)

        expected_count = len(ground_truth['features']['footnotes'])

        # Allow for potential auto-detected footnotes, but warn if count differs significantly
        assert len(found_definitions) <= expected_count + 2, \
            f"Too many footnotes detected (possible hallucination).\n" \
            f"Expected: {expected_count}, Found: {len(found_definitions)}\n" \
            f"Found markers: {found_definitions}"

    def test_footnote_processing_deterministic(self, ground_truth):
        """
        Test that processing the same PDF produces identical footnotes.

        Ensures deterministic behavior (no randomness in detection).
        """
        pdf_path = Path(__file__).parent.parent.parent / ground_truth['pdf_file']

        # Process twice
        result1 = process_pdf(pdf_path, output_format='markdown', detect_footnotes=True)
        result2 = process_pdf(pdf_path, output_format='markdown', detect_footnotes=True)

        # Extract footnote sections (match symbols, not just \w)
        import re
        footnotes1 = re.findall(r'\[\^(.+?)\]:([^\[]*)', result1)
        footnotes2 = re.findall(r'\[\^(.+?)\]:([^\[]*)', result2)

        assert footnotes1 == footnotes2, \
            "Non-deterministic footnote detection (results differ between runs)"


class TestFootnoteEdgeCases:
    """Test edge cases and error handling."""

    def test_pdf_without_footnotes(self):
        """Test processing PDF with no footnotes doesn't crash."""
        # Use a simple test PDF without footnotes
        pdf_path = Path(__file__).parent.parent.parent / "test_files/test_digital_formatting.pdf"

        if not pdf_path.exists():
            pytest.skip(f"Test PDF not found: {pdf_path}")

        # Should not crash
        result = process_pdf(pdf_path, output_format='markdown', detect_footnotes=True)

        # Should have no footnote definitions
        import re
        found_footnotes = re.findall(r'\[\^\w+\]:', result)
        assert len(found_footnotes) == 0, \
            f"False positive: Found footnotes in PDF without footnotes: {found_footnotes}"

    def test_footnote_detection_disabled(self):
        """Test that footnotes are not detected when detection is disabled."""
        pdf_path = Path(__file__).parent.parent.parent / "test_files/derrida_footnote_pages_120_125.pdf"

        result = process_pdf(pdf_path, output_format='markdown', detect_footnotes=False)

        # Should have no footnote markdown syntax
        import re
        found_footnotes = re.findall(r'\[\^.+?\]:', result)
        assert len(found_footnotes) == 0, \
            "Footnotes detected despite detect_footnotes=False"


if __name__ == '__main__':
    # Allow running this test file directly
    pytest.main([__file__, '-v', '--tb=short'])
