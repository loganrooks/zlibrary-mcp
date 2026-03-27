"""
Unit tests for lib/strikethrough_detection.py

Targets uncovered lines: 45-48, 54-56, 84-92, 107, 111, 147,
177-200, 215-234, 255-279, 298-343, 384-484, 510-519, 528, 530.

Uses mocks — no real PDFs, opencv, or numpy.
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


# ===================================================================
# XMarkDetectionConfig  (lines 84-92 — validation)
# ===================================================================

from lib.strikethrough_detection import (
    XMarkDetectionConfig,
    DetectedLine,
    XMarkCandidate,
    XMarkDetectionResult,
    _filter_diagonal_lines,
    _find_crossing_pairs,
)


class TestXMarkDetectionConfig:
    def test_defaults(self):
        cfg = XMarkDetectionConfig()
        assert cfg.min_line_length == 10.0
        assert cfg.render_dpi == 300

    def test_invalid_min_line_length(self):
        with pytest.raises(ValueError, match="min_line_length"):
            XMarkDetectionConfig(min_line_length=-1)
        with pytest.raises(ValueError, match="min_line_length"):
            XMarkDetectionConfig(min_line_length=1001)

    def test_invalid_diagonal_tolerance(self):
        with pytest.raises(ValueError, match="diagonal_tolerance"):
            XMarkDetectionConfig(diagonal_tolerance=0)
        with pytest.raises(ValueError, match="diagonal_tolerance"):
            XMarkDetectionConfig(diagonal_tolerance=91)

    def test_invalid_proximity_threshold(self):
        with pytest.raises(ValueError, match="proximity_threshold"):
            XMarkDetectionConfig(proximity_threshold=-5)

    def test_invalid_confidence_threshold(self):
        with pytest.raises(ValueError, match="confidence_threshold"):
            XMarkDetectionConfig(confidence_threshold=1.5)
        with pytest.raises(ValueError, match="confidence_threshold"):
            XMarkDetectionConfig(confidence_threshold=-0.1)

    def test_invalid_render_dpi(self):
        with pytest.raises(ValueError, match="render_dpi"):
            XMarkDetectionConfig(render_dpi=50)
        with pytest.raises(ValueError, match="render_dpi"):
            XMarkDetectionConfig(render_dpi=700)


# ===================================================================
# DetectedLine properties  (lines 107, 111)
# ===================================================================


class TestDetectedLine:
    def test_center_properties(self):
        line = DetectedLine(x1=0, y1=0, x2=10, y2=20, angle=45.0, length=22.36)
        assert line.x_center == 5.0
        assert line.y_center == 10.0


# ===================================================================
# XMarkDetectionResult.to_dict  (line 147)
# ===================================================================


class TestXMarkDetectionResult:
    def test_to_dict(self):
        result = XMarkDetectionResult(
            has_xmarks=True,
            xmark_count=2,
            confidence=0.85,
            flags={"high_confidence", "few_xmarks"},
            candidates=[MagicMock(), MagicMock()],
            metrics={"total_lines": 50},
        )
        d = result.to_dict()
        assert d["has_xmarks"] is True
        assert d["xmark_count"] == 2
        assert d["confidence"] == 0.85
        assert set(d["flags"]) == {"high_confidence", "few_xmarks"}
        assert d["candidate_count"] == 2
        assert d["metrics"]["total_lines"] == 50

    def test_to_dict_empty(self):
        result = XMarkDetectionResult(has_xmarks=False, xmark_count=0, confidence=0.0)
        d = result.to_dict()
        assert d["has_xmarks"] is False
        assert d["flags"] == []


# ===================================================================
# _filter_diagonal_lines  (lines 255-279)
# ===================================================================


class TestFilterDiagonalLines:
    def _line(self, angle: float, length: float = 20.0) -> DetectedLine:
        return DetectedLine(x1=0, y1=0, x2=10, y2=10, angle=angle, length=length)

    def test_positive_diagonal(self):
        """Line at ~45 degrees goes to positive group."""
        pos, neg = _filter_diagonal_lines([self._line(45.0)], angle_tolerance=15.0)
        assert len(pos) == 1
        assert len(neg) == 0

    def test_negative_diagonal(self):
        """Line at ~-45 degrees goes to negative group."""
        pos, neg = _filter_diagonal_lines([self._line(-45.0)], angle_tolerance=15.0)
        assert len(pos) == 0
        assert len(neg) == 1

    def test_135_degree_is_negative(self):
        """Line at 135 degrees also negative diagonal."""
        pos, neg = _filter_diagonal_lines([self._line(135.0)], angle_tolerance=15.0)
        assert len(neg) == 1

    def test_horizontal_excluded(self):
        pos, neg = _filter_diagonal_lines([self._line(0.0)], angle_tolerance=15.0)
        assert len(pos) == 0 and len(neg) == 0

    def test_vertical_excluded(self):
        pos, neg = _filter_diagonal_lines([self._line(90.0)], angle_tolerance=15.0)
        assert len(pos) == 0 and len(neg) == 0

    def test_short_lines_excluded(self):
        short = self._line(45.0, length=5.0)
        pos, neg = _filter_diagonal_lines([short], min_length=10.0)
        assert len(pos) == 0

    def test_mixed_lines(self):
        lines = [self._line(45.0), self._line(-45.0), self._line(0.0)]
        pos, neg = _filter_diagonal_lines(lines, angle_tolerance=15.0)
        assert len(pos) == 1
        assert len(neg) == 1

    def test_angle_wrapping(self):
        """Angle > 180 should wrap correctly."""
        line = self._line(315.0)  # 315 = -45 after wrapping
        pos, neg = _filter_diagonal_lines([line], angle_tolerance=15.0)
        assert len(neg) == 1


# ===================================================================
# _find_crossing_pairs  (lines 298-343)
# ===================================================================


class TestFindCrossingPairs:
    def test_crossing_pair_found(self):
        """Two crossing lines should produce a candidate."""
        pos = DetectedLine(x1=0, y1=0, x2=20, y2=20, angle=45.0, length=28.0)
        neg = DetectedLine(x1=20, y1=0, x2=0, y2=20, angle=-45.0, length=28.0)
        candidates = _find_crossing_pairs([pos], [neg], max_distance=30.0)
        assert len(candidates) == 1
        c = candidates[0]
        assert c.confidence > 0.0
        assert c.bbox is not None

    def test_distant_lines_no_crossing(self):
        """Lines far apart should not cross."""
        pos = DetectedLine(x1=0, y1=0, x2=20, y2=20, angle=45.0, length=28.0)
        neg = DetectedLine(x1=200, y1=200, x2=220, y2=220, angle=-45.0, length=28.0)
        candidates = _find_crossing_pairs([pos], [neg], max_distance=20.0)
        assert len(candidates) == 0

    def test_multiple_crossings_sorted_by_confidence(self):
        """Multiple candidates should be sorted by confidence descending."""
        pos1 = DetectedLine(x1=0, y1=0, x2=20, y2=20, angle=45.0, length=28.0)
        pos2 = DetectedLine(x1=50, y1=50, x2=70, y2=70, angle=45.0, length=28.0)
        neg1 = DetectedLine(x1=20, y1=0, x2=0, y2=20, angle=-45.0, length=28.0)
        neg2 = DetectedLine(x1=70, y1=50, x2=50, y2=70, angle=-45.0, length=28.0)
        candidates = _find_crossing_pairs([pos1, pos2], [neg1, neg2], max_distance=30.0)
        assert len(candidates) >= 2
        # sorted descending
        for i in range(len(candidates) - 1):
            assert candidates[i].confidence >= candidates[i + 1].confidence

    def test_confidence_components(self):
        """Confidence uses center_score, length_ratio, angle_score."""
        # Perfect X: same center, same length, 90 degree angle difference
        pos = DetectedLine(x1=0, y1=0, x2=20, y2=20, angle=45.0, length=28.0)
        neg = DetectedLine(x1=20, y1=0, x2=0, y2=20, angle=-45.0, length=28.0)
        candidates = _find_crossing_pairs([pos], [neg], max_distance=30.0)
        assert len(candidates) == 1
        # Should have high confidence
        assert candidates[0].confidence > 0.5


# ===================================================================
# detect_strikethrough_enhanced  (lines 384-484)
# ===================================================================


class TestDetectStrikethroughEnhanced:
    """Test the main enhanced detection function with mocked dependencies."""

    def test_opencv_not_available(self):
        """Should raise ImportError if opencv not available."""
        with patch("lib.strikethrough_detection.OPENCV_AVAILABLE", False):
            from lib.strikethrough_detection import detect_strikethrough_enhanced

            with pytest.raises(ImportError, match="opencv"):
                detect_strikethrough_enhanced(Path("/fake.pdf"), 0)

    def test_pymupdf_not_available(self):
        """Should raise ImportError if PyMuPDF not available."""
        with (
            patch("lib.strikethrough_detection.OPENCV_AVAILABLE", True),
            patch("lib.strikethrough_detection.PYMUPDF_AVAILABLE", False),
        ):
            from lib.strikethrough_detection import detect_strikethrough_enhanced

            with pytest.raises(ImportError, match="PyMuPDF"):
                detect_strikethrough_enhanced(Path("/fake.pdf"), 0)

    def test_no_lines_detected(self):
        """No lines -> no xmarks."""
        import numpy as np

        mock_img = np.zeros((100, 100, 3), dtype=np.uint8)

        with (
            patch("lib.strikethrough_detection.OPENCV_AVAILABLE", True),
            patch("lib.strikethrough_detection.PYMUPDF_AVAILABLE", True),
            patch(
                "lib.strikethrough_detection._render_page_to_image",
                return_value=mock_img,
            ),
            patch("lib.strikethrough_detection._detect_lines_lsd", return_value=[]),
        ):
            from lib.strikethrough_detection import detect_strikethrough_enhanced

            result = detect_strikethrough_enhanced(Path("/fake.pdf"), 0)
            assert result.has_xmarks is False
            assert result.xmark_count == 0

    def test_missing_diagonal_pair(self):
        """Only positive diagonals, no negative -> missing_diagonal_pair flag."""
        import numpy as np

        mock_img = np.zeros((100, 100, 3), dtype=np.uint8)
        pos_line = DetectedLine(x1=0, y1=0, x2=20, y2=20, angle=45.0, length=28.0)

        with (
            patch("lib.strikethrough_detection.OPENCV_AVAILABLE", True),
            patch("lib.strikethrough_detection.PYMUPDF_AVAILABLE", True),
            patch(
                "lib.strikethrough_detection._render_page_to_image",
                return_value=mock_img,
            ),
            patch(
                "lib.strikethrough_detection._detect_lines_lsd", return_value=[pos_line]
            ),
            patch(
                "lib.strikethrough_detection._filter_diagonal_lines",
                return_value=([pos_line], []),
            ),
        ):
            from lib.strikethrough_detection import detect_strikethrough_enhanced

            result = detect_strikethrough_enhanced(Path("/fake.pdf"), 0)
            assert "missing_diagonal_pair" in result.flags

    def test_no_crossings_found(self):
        """Diagonals exist but don't cross."""
        import numpy as np

        mock_img = np.zeros((100, 100, 3), dtype=np.uint8)
        pos_line = DetectedLine(x1=0, y1=0, x2=20, y2=20, angle=45.0, length=28.0)
        neg_line = DetectedLine(
            x1=200, y1=200, x2=220, y2=180, angle=-45.0, length=28.0
        )

        with (
            patch("lib.strikethrough_detection.OPENCV_AVAILABLE", True),
            patch("lib.strikethrough_detection.PYMUPDF_AVAILABLE", True),
            patch(
                "lib.strikethrough_detection._render_page_to_image",
                return_value=mock_img,
            ),
            patch(
                "lib.strikethrough_detection._detect_lines_lsd",
                return_value=[pos_line, neg_line],
            ),
            patch(
                "lib.strikethrough_detection._filter_diagonal_lines",
                return_value=([pos_line], [neg_line]),
            ),
            patch("lib.strikethrough_detection._find_crossing_pairs", return_value=[]),
        ):
            from lib.strikethrough_detection import detect_strikethrough_enhanced

            result = detect_strikethrough_enhanced(Path("/fake.pdf"), 0)
            assert "no_crossings_found" in result.flags

    def test_low_confidence_candidates(self):
        """Candidates below threshold -> low_confidence_candidates flag."""
        import numpy as np

        mock_img = np.zeros((100, 100, 3), dtype=np.uint8)
        pos_line = DetectedLine(x1=0, y1=0, x2=20, y2=20, angle=45.0, length=28.0)
        neg_line = DetectedLine(x1=20, y1=0, x2=0, y2=20, angle=-45.0, length=28.0)
        low_candidate = XMarkCandidate(
            line1=pos_line,
            line2=neg_line,
            center_x=10,
            center_y=10,
            confidence=0.2,
            bbox=(0, 0, 20, 20),
        )

        with (
            patch("lib.strikethrough_detection.OPENCV_AVAILABLE", True),
            patch("lib.strikethrough_detection.PYMUPDF_AVAILABLE", True),
            patch(
                "lib.strikethrough_detection._render_page_to_image",
                return_value=mock_img,
            ),
            patch(
                "lib.strikethrough_detection._detect_lines_lsd",
                return_value=[pos_line, neg_line],
            ),
            patch(
                "lib.strikethrough_detection._filter_diagonal_lines",
                return_value=([pos_line], [neg_line]),
            ),
            patch(
                "lib.strikethrough_detection._find_crossing_pairs",
                return_value=[low_candidate],
            ),
        ):
            from lib.strikethrough_detection import detect_strikethrough_enhanced

            result = detect_strikethrough_enhanced(Path("/fake.pdf"), 0)
            assert "low_confidence_candidates" in result.flags
            assert result.has_xmarks is False

    def test_high_confidence_single_xmark(self):
        """Single high-confidence candidate -> detected."""
        import numpy as np

        mock_img = np.zeros((100, 100, 3), dtype=np.uint8)
        pos_line = DetectedLine(x1=0, y1=0, x2=20, y2=20, angle=45.0, length=28.0)
        neg_line = DetectedLine(x1=20, y1=0, x2=0, y2=20, angle=-45.0, length=28.0)
        candidate = XMarkCandidate(
            line1=pos_line,
            line2=neg_line,
            center_x=10,
            center_y=10,
            confidence=0.85,
            bbox=(0, 0, 20, 20),
        )

        with (
            patch("lib.strikethrough_detection.OPENCV_AVAILABLE", True),
            patch("lib.strikethrough_detection.PYMUPDF_AVAILABLE", True),
            patch(
                "lib.strikethrough_detection._render_page_to_image",
                return_value=mock_img,
            ),
            patch(
                "lib.strikethrough_detection._detect_lines_lsd",
                return_value=[pos_line, neg_line],
            ),
            patch(
                "lib.strikethrough_detection._filter_diagonal_lines",
                return_value=([pos_line], [neg_line]),
            ),
            patch(
                "lib.strikethrough_detection._find_crossing_pairs",
                return_value=[candidate],
            ),
        ):
            from lib.strikethrough_detection import detect_strikethrough_enhanced

            result = detect_strikethrough_enhanced(Path("/fake.pdf"), 0)
            assert result.has_xmarks is True
            assert result.xmark_count == 1
            assert "high_confidence" in result.flags
            assert "single_xmark" in result.flags

    def test_medium_confidence_few_xmarks(self):
        """Two medium-confidence candidates."""
        import numpy as np

        mock_img = np.zeros((100, 100, 3), dtype=np.uint8)
        pos_line = DetectedLine(x1=0, y1=0, x2=20, y2=20, angle=45.0, length=28.0)
        neg_line = DetectedLine(x1=20, y1=0, x2=0, y2=20, angle=-45.0, length=28.0)
        c1 = XMarkCandidate(
            line1=pos_line,
            line2=neg_line,
            center_x=10,
            center_y=10,
            confidence=0.7,
            bbox=(0, 0, 20, 20),
        )
        c2 = XMarkCandidate(
            line1=pos_line,
            line2=neg_line,
            center_x=30,
            center_y=30,
            confidence=0.65,
            bbox=(20, 20, 40, 40),
        )

        with (
            patch("lib.strikethrough_detection.OPENCV_AVAILABLE", True),
            patch("lib.strikethrough_detection.PYMUPDF_AVAILABLE", True),
            patch(
                "lib.strikethrough_detection._render_page_to_image",
                return_value=mock_img,
            ),
            patch(
                "lib.strikethrough_detection._detect_lines_lsd",
                return_value=[pos_line, neg_line],
            ),
            patch(
                "lib.strikethrough_detection._filter_diagonal_lines",
                return_value=([pos_line], [neg_line]),
            ),
            patch(
                "lib.strikethrough_detection._find_crossing_pairs",
                return_value=[c1, c2],
            ),
        ):
            from lib.strikethrough_detection import detect_strikethrough_enhanced

            result = detect_strikethrough_enhanced(Path("/fake.pdf"), 0)
            assert result.has_xmarks is True
            assert result.xmark_count == 2
            assert "medium_confidence" in result.flags
            assert "few_xmarks" in result.flags

    def test_multiple_xmarks_flag(self):
        """More than 3 candidates -> multiple_xmarks flag."""
        import numpy as np

        mock_img = np.zeros((100, 100, 3), dtype=np.uint8)
        pos_line = DetectedLine(x1=0, y1=0, x2=20, y2=20, angle=45.0, length=28.0)
        neg_line = DetectedLine(x1=20, y1=0, x2=0, y2=20, angle=-45.0, length=28.0)
        candidates = [
            XMarkCandidate(
                line1=pos_line,
                line2=neg_line,
                center_x=i * 30,
                center_y=i * 30,
                confidence=0.9,
                bbox=(0, 0, 20, 20),
            )
            for i in range(5)
        ]

        with (
            patch("lib.strikethrough_detection.OPENCV_AVAILABLE", True),
            patch("lib.strikethrough_detection.PYMUPDF_AVAILABLE", True),
            patch(
                "lib.strikethrough_detection._render_page_to_image",
                return_value=mock_img,
            ),
            patch(
                "lib.strikethrough_detection._detect_lines_lsd",
                return_value=[pos_line, neg_line],
            ),
            patch(
                "lib.strikethrough_detection._filter_diagonal_lines",
                return_value=([pos_line], [neg_line]),
            ),
            patch(
                "lib.strikethrough_detection._find_crossing_pairs",
                return_value=candidates,
            ),
        ):
            from lib.strikethrough_detection import detect_strikethrough_enhanced

            result = detect_strikethrough_enhanced(Path("/fake.pdf"), 0)
            assert "multiple_xmarks" in result.flags
            assert result.xmark_count == 5

    def test_low_confidence_flag(self):
        """Candidate with confidence between 0.5 and 0.6."""
        import numpy as np

        mock_img = np.zeros((100, 100, 3), dtype=np.uint8)
        pos_line = DetectedLine(x1=0, y1=0, x2=20, y2=20, angle=45.0, length=28.0)
        neg_line = DetectedLine(x1=20, y1=0, x2=0, y2=20, angle=-45.0, length=28.0)
        candidate = XMarkCandidate(
            line1=pos_line,
            line2=neg_line,
            center_x=10,
            center_y=10,
            confidence=0.55,
            bbox=(0, 0, 20, 20),
        )

        with (
            patch("lib.strikethrough_detection.OPENCV_AVAILABLE", True),
            patch("lib.strikethrough_detection.PYMUPDF_AVAILABLE", True),
            patch(
                "lib.strikethrough_detection._render_page_to_image",
                return_value=mock_img,
            ),
            patch(
                "lib.strikethrough_detection._detect_lines_lsd",
                return_value=[pos_line, neg_line],
            ),
            patch(
                "lib.strikethrough_detection._filter_diagonal_lines",
                return_value=([pos_line], [neg_line]),
            ),
            patch(
                "lib.strikethrough_detection._find_crossing_pairs",
                return_value=[candidate],
            ),
        ):
            from lib.strikethrough_detection import detect_strikethrough_enhanced

            result = detect_strikethrough_enhanced(Path("/fake.pdf"), 0)
            assert "low_confidence" in result.flags


# ===================================================================
# detect_strikethrough (legacy)  (lines 510-519)
# ===================================================================


class TestDetectStrikethroughLegacy:
    def test_returns_bool_true(self):
        mock_result = XMarkDetectionResult(
            has_xmarks=True, xmark_count=1, confidence=0.9
        )
        with (
            patch(
                "lib.strikethrough_detection.detect_strikethrough_enhanced",
                return_value=mock_result,
            ),
            patch("lib.strikethrough_detection.OPENCV_AVAILABLE", True),
            patch("lib.strikethrough_detection.PYMUPDF_AVAILABLE", True),
        ):
            from lib.strikethrough_detection import detect_strikethrough

            assert detect_strikethrough(Path("/fake.pdf"), 0) is True

    def test_returns_false_on_no_xmarks(self):
        mock_result = XMarkDetectionResult(
            has_xmarks=False, xmark_count=0, confidence=0.0
        )
        with (
            patch(
                "lib.strikethrough_detection.detect_strikethrough_enhanced",
                return_value=mock_result,
            ),
            patch("lib.strikethrough_detection.OPENCV_AVAILABLE", True),
            patch("lib.strikethrough_detection.PYMUPDF_AVAILABLE", True),
        ):
            from lib.strikethrough_detection import detect_strikethrough

            assert detect_strikethrough(Path("/fake.pdf"), 0) is False

    def test_import_error_returns_false(self):
        with patch(
            "lib.strikethrough_detection.detect_strikethrough_enhanced",
            side_effect=ImportError("no opencv"),
        ):
            from lib.strikethrough_detection import detect_strikethrough

            assert detect_strikethrough(Path("/fake.pdf"), 0) is False

    def test_runtime_error_returns_false(self):
        with patch(
            "lib.strikethrough_detection.detect_strikethrough_enhanced",
            side_effect=RuntimeError("boom"),
        ):
            from lib.strikethrough_detection import detect_strikethrough

            assert detect_strikethrough(Path("/fake.pdf"), 0) is False


# ===================================================================
# _render_page_to_image  (lines 177-200)
# ===================================================================


class TestRenderPageToImage:
    def test_pymupdf_not_available(self):
        with patch("lib.strikethrough_detection.PYMUPDF_AVAILABLE", False):
            from lib.strikethrough_detection import _render_page_to_image

            with pytest.raises(ImportError):
                _render_page_to_image(Path("/fake.pdf"), 0)

    def test_invalid_page_number(self):
        """Page number out of range raises ValueError via RuntimeError wrapping."""
        mock_doc = MagicMock()
        mock_doc.__len__ = lambda self: 5
        # Page access with bad index triggers check in the function
        with (
            patch("lib.strikethrough_detection.PYMUPDF_AVAILABLE", True),
            patch("lib.strikethrough_detection.fitz") as mock_fitz,
        ):
            mock_fitz.open.return_value = mock_doc
            mock_fitz.Matrix.return_value = MagicMock()
            from lib.strikethrough_detection import _render_page_to_image

            with pytest.raises((ValueError, RuntimeError)):
                _render_page_to_image(Path("/fake.pdf"), 10)


# ===================================================================
# _detect_lines_lsd  (lines 215-234)
# ===================================================================


class TestDetectLinesLsd:
    def test_opencv_not_available(self):
        with patch("lib.strikethrough_detection.OPENCV_AVAILABLE", False):
            from lib.strikethrough_detection import _detect_lines_lsd

            with pytest.raises(ImportError):
                _detect_lines_lsd(MagicMock())

    def test_detect_lines_success(self):
        """Exercise the full _detect_lines_lsd path with mocked opencv (lines 218-234)."""
        import numpy as np

        mock_img = np.zeros((100, 100, 3), dtype=np.uint8)

        mock_lsd = MagicMock()
        # Simulate LSD returning two lines: [[x1, y1, x2, y2]]
        mock_lsd.detect.return_value = (
            np.array([[[0.0, 0.0, 10.0, 10.0]], [[20.0, 20.0, 30.0, 30.0]]]),
        )

        with (
            patch("lib.strikethrough_detection.OPENCV_AVAILABLE", True),
            patch("lib.strikethrough_detection.cv2") as mock_cv2,
        ):
            mock_cv2.cvtColor.return_value = np.zeros((100, 100), dtype=np.uint8)
            mock_cv2.createLineSegmentDetector.return_value = mock_lsd
            from lib.strikethrough_detection import _detect_lines_lsd

            lines = _detect_lines_lsd(mock_img)
            assert len(lines) == 2
            assert lines[0].x1 == 0.0
            assert lines[0].y1 == 0.0
            assert lines[1].x1 == 20.0

    def test_detect_lines_no_lines(self):
        """LSD returns None for lines -> empty list."""
        import numpy as np

        mock_img = np.zeros((100, 100, 3), dtype=np.uint8)

        mock_lsd = MagicMock()
        mock_lsd.detect.return_value = (None,)

        with (
            patch("lib.strikethrough_detection.OPENCV_AVAILABLE", True),
            patch("lib.strikethrough_detection.cv2") as mock_cv2,
        ):
            mock_cv2.cvtColor.return_value = np.zeros((100, 100), dtype=np.uint8)
            mock_cv2.createLineSegmentDetector.return_value = mock_lsd
            from lib.strikethrough_detection import _detect_lines_lsd

            lines = _detect_lines_lsd(mock_img)
            assert lines == []


# ===================================================================
# _render_page_to_image success path (lines 185-197)
# ===================================================================


class TestRenderPageToImageSuccess:
    def test_render_rgb_success(self):
        """Full success path: open doc, render page, convert to numpy (n=3, RGB)."""

        mock_pix = MagicMock()
        mock_pix.samples = bytes(100 * 100 * 3)
        mock_pix.height = 100
        mock_pix.width = 100
        mock_pix.n = 3  # RGB, not RGBA

        mock_page = MagicMock()
        mock_page.get_pixmap.return_value = mock_pix

        mock_doc = MagicMock()
        mock_doc.__len__ = lambda self: 5
        mock_doc.__getitem__ = lambda self, idx: mock_page

        with (
            patch("lib.strikethrough_detection.PYMUPDF_AVAILABLE", True),
            patch("lib.strikethrough_detection.fitz") as mock_fitz,
        ):
            mock_fitz.open.return_value = mock_doc
            mock_fitz.Matrix.return_value = MagicMock()
            from lib.strikethrough_detection import _render_page_to_image

            # np is the real numpy module, so frombuffer will work on real bytes
            img = _render_page_to_image(Path("/fake.pdf"), 0, dpi=150)
            assert img.shape == (100, 100, 3)
            mock_doc.close.assert_called_once()

    def test_render_rgba_to_bgr(self):
        """RGBA (n=4) conversion path through cv2.cvtColor (lines 193-194)."""
        import numpy as np

        mock_pix = MagicMock()
        mock_pix.samples = bytes(100 * 100 * 4)
        mock_pix.height = 100
        mock_pix.width = 100
        mock_pix.n = 4  # RGBA

        mock_page = MagicMock()
        mock_page.get_pixmap.return_value = mock_pix

        mock_doc = MagicMock()
        mock_doc.__len__ = lambda self: 5
        mock_doc.__getitem__ = lambda self, idx: mock_page

        mock_bgr_img = np.zeros((100, 100, 3), dtype=np.uint8)

        with (
            patch("lib.strikethrough_detection.PYMUPDF_AVAILABLE", True),
            patch("lib.strikethrough_detection.fitz") as mock_fitz,
            patch("lib.strikethrough_detection.cv2") as mock_cv2,
        ):
            mock_fitz.open.return_value = mock_doc
            mock_fitz.Matrix.return_value = MagicMock()
            mock_cv2.COLOR_RGBA2BGR = 4  # constant
            mock_cv2.cvtColor.return_value = mock_bgr_img
            from lib.strikethrough_detection import _render_page_to_image

            img = _render_page_to_image(Path("/fake.pdf"), 0)
            mock_cv2.cvtColor.assert_called_once()
            assert img.shape == (100, 100, 3)

    def test_render_generic_exception_wraps_in_runtime_error(self):
        """Any exception during rendering wraps in RuntimeError (lines 199-200)."""
        mock_doc = MagicMock()
        mock_doc.__len__ = lambda self: 5
        mock_doc.__getitem__ = MagicMock(side_effect=Exception("corrupt page data"))

        with (
            patch("lib.strikethrough_detection.PYMUPDF_AVAILABLE", True),
            patch("lib.strikethrough_detection.fitz") as mock_fitz,
        ):
            mock_fitz.open.return_value = mock_doc
            mock_fitz.Matrix.return_value = MagicMock()
            from lib.strikethrough_detection import _render_page_to_image

            with pytest.raises(RuntimeError, match="Failed to render PDF page"):
                _render_page_to_image(Path("/fake.pdf"), 0)


# ===================================================================
# detect_strikethrough_enhanced exception re-raise (lines 482-484)
# ===================================================================


class TestDetectStrikethroughEnhancedException:
    def test_exception_during_detection_re_raised(self):
        """Internal exception is re-raised after logging (lines 482-484)."""
        with (
            patch("lib.strikethrough_detection.OPENCV_AVAILABLE", True),
            patch("lib.strikethrough_detection.PYMUPDF_AVAILABLE", True),
            patch(
                "lib.strikethrough_detection._render_page_to_image",
                side_effect=RuntimeError("render failed"),
            ),
        ):
            from lib.strikethrough_detection import detect_strikethrough_enhanced

            with pytest.raises(RuntimeError, match="render failed"):
                detect_strikethrough_enhanced(Path("/fake.pdf"), 0)
