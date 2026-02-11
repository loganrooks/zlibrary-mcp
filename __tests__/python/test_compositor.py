"""Tests for the compositor conflict resolution logic."""

import pytest

from lib.rag.pipeline.models import (
    BlockClassification,
    ContentType,
    DetectionResult,
)
from lib.rag.pipeline.compositor import (
    classify_page_blocks,
    compute_bbox_overlap,
    resolve_conflicts,
)

pytestmark = pytest.mark.unit


class TestComputeBboxOverlap:
    """Tests for bbox overlap calculation."""

    def test_identical_bboxes_full_overlap(self):
        assert compute_bbox_overlap((0, 0, 100, 100), (0, 0, 100, 100)) == 1.0

    def test_no_overlap(self):
        assert compute_bbox_overlap((0, 0, 50, 50), (200, 200, 300, 300)) == 0.0

    def test_partial_overlap(self):
        # 50x50 overlap, smaller box is 100x100 = 10000
        overlap = compute_bbox_overlap((0, 0, 100, 100), (50, 50, 150, 150))
        assert 0.2 < overlap < 0.3  # 2500/10000 = 0.25

    def test_bbox_overlap_detection_threshold(self):
        """Bboxes overlapping >50% should be considered same block."""
        # Large overlap: 80x80 intersection, smaller box 100x100
        overlap = compute_bbox_overlap((0, 0, 100, 100), (20, 20, 120, 120))
        assert overlap > 0.5

    def test_zero_area_bbox(self):
        assert compute_bbox_overlap((0, 0, 0, 0), (0, 0, 100, 100)) == 0.0


class TestClassifyPageBlocks:
    """Tests for page-level block classification."""

    def test_body_default_when_no_claims(self):
        """Blocks with no detector claim default to BODY."""
        page_blocks = [(72, 100, 500, 120), (72, 130, 500, 150)]
        detection_results = []
        classified = classify_page_blocks(page_blocks, detection_results)
        assert len(classified) == 2
        assert all(c.content_type == ContentType.BODY for c in classified)
        assert all(c.confidence == 1.0 for c in classified)

    def test_higher_confidence_wins(self):
        """When two detectors claim same bbox, higher confidence wins."""
        page_blocks = [(72, 100, 500, 120)]
        bbox = (72, 100, 500, 120)
        results = [
            DetectionResult(
                detector_name="detector_a",
                classifications=[
                    BlockClassification(
                        bbox=bbox,
                        content_type=ContentType.FOOTNOTE,
                        text="note",
                        confidence=0.9,
                        detector_name="detector_a",
                    )
                ],
            ),
            DetectionResult(
                detector_name="detector_b",
                classifications=[
                    BlockClassification(
                        bbox=bbox,
                        content_type=ContentType.MARGIN,
                        text="note",
                        confidence=0.7,
                        detector_name="detector_b",
                    )
                ],
            ),
        ]
        classified = classify_page_blocks(page_blocks, results)
        assert len(classified) == 1
        assert classified[0].content_type == ContentType.FOOTNOTE
        assert classified[0].confidence == 0.9

    def test_footnote_wins_on_overlap_tie(self):
        """At equal confidence, footnote beats margin (type priority)."""
        page_blocks = [(72, 100, 500, 120)]
        bbox = (72, 100, 500, 120)
        results = [
            DetectionResult(
                detector_name="margin_det",
                classifications=[
                    BlockClassification(
                        bbox=bbox,
                        content_type=ContentType.MARGIN,
                        text="text",
                        confidence=0.8,
                        detector_name="margin_det",
                    )
                ],
            ),
            DetectionResult(
                detector_name="footnote_det",
                classifications=[
                    BlockClassification(
                        bbox=bbox,
                        content_type=ContentType.FOOTNOTE,
                        text="text",
                        confidence=0.8,
                        detector_name="footnote_det",
                    )
                ],
            ),
        ]
        classified = classify_page_blocks(page_blocks, results)
        assert classified[0].content_type == ContentType.FOOTNOTE

    def test_low_confidence_stays_body(self):
        """Detector claim below confidence floor (0.6) → BODY."""
        page_blocks = [(72, 100, 500, 120)]
        results = [
            DetectionResult(
                detector_name="det",
                classifications=[
                    BlockClassification(
                        bbox=(72, 100, 500, 120),
                        content_type=ContentType.FOOTNOTE,
                        text="maybe note",
                        confidence=0.4,
                        detector_name="det",
                    )
                ],
            ),
        ]
        classified = classify_page_blocks(page_blocks, results)
        assert classified[0].content_type == ContentType.BODY

    def test_non_overlapping_blocks_independent(self):
        """Different blocks get independent classifications."""
        page_blocks = [(72, 100, 500, 120), (72, 700, 500, 720)]
        results = [
            DetectionResult(
                detector_name="det_a",
                classifications=[
                    BlockClassification(
                        bbox=(72, 100, 500, 120),
                        content_type=ContentType.HEADER,
                        text="Chapter 1",
                        confidence=0.9,
                        detector_name="det_a",
                    )
                ],
            ),
            DetectionResult(
                detector_name="det_b",
                classifications=[
                    BlockClassification(
                        bbox=(72, 700, 500, 720),
                        content_type=ContentType.FOOTER,
                        text="Page 1",
                        confidence=0.85,
                        detector_name="det_b",
                    )
                ],
            ),
        ]
        classified = classify_page_blocks(page_blocks, results)
        assert len(classified) == 2
        types = {c.content_type for c in classified}
        assert types == {ContentType.HEADER, ContentType.FOOTER}

    def test_recall_bias_ambiguous_block(self):
        """Ambiguous block (two low-confidence detectors) → BODY."""
        page_blocks = [(72, 100, 500, 120)]
        bbox = (72, 100, 500, 120)
        results = [
            DetectionResult(
                detector_name="det_a",
                classifications=[
                    BlockClassification(
                        bbox=bbox,
                        content_type=ContentType.MARGIN,
                        text="text",
                        confidence=0.5,
                        detector_name="det_a",
                    )
                ],
            ),
            DetectionResult(
                detector_name="det_b",
                classifications=[
                    BlockClassification(
                        bbox=bbox,
                        content_type=ContentType.FOOTNOTE,
                        text="text",
                        confidence=0.55,
                        detector_name="det_b",
                    )
                ],
            ),
        ]
        classified = classify_page_blocks(page_blocks, results)
        assert classified[0].content_type == ContentType.BODY


class TestResolveConflicts:
    """Tests for document-level conflict resolution."""

    def test_resolve_conflicts_multi_page(self):
        """resolve_conflicts returns complete mapping for all pages."""
        page_blocks_by_page = {
            1: [(72, 100, 500, 120)],
            2: [(72, 100, 500, 120), (72, 700, 500, 720)],
        }
        results = [
            DetectionResult(
                detector_name="det",
                page_num=2,
                classifications=[
                    BlockClassification(
                        bbox=(72, 700, 500, 720),
                        content_type=ContentType.PAGE_NUMBER,
                        text="2",
                        confidence=0.95,
                        detector_name="det",
                        page_num=2,
                    )
                ],
            ),
        ]
        output = resolve_conflicts(results, page_blocks_by_page)
        assert 1 in output
        assert 2 in output
        # Page 1: no claims → BODY
        assert output[1][0].content_type == ContentType.BODY
        # Page 2: one claimed, one not
        page2_types = {c.content_type for c in output[2]}
        assert ContentType.PAGE_NUMBER in page2_types
        assert ContentType.BODY in page2_types
