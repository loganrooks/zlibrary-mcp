"""
Strikethrough/X-Mark Detection Module

Detects X-marks and strikethrough patterns in PDF pages using computer vision.
Designed for scholarly philosophy texts (Derrida sous-rature, Heidegger crossings).

Usage:
    >>> from lib.strikethrough_detection import detect_strikethrough
    >>>
    >>> # Simple usage (returns boolean)
    >>> has_strikethrough = detect_strikethrough(pdf_path, page_num)
    >>>
    >>> # Enhanced usage (returns detailed result)
    >>> from lib.strikethrough_detection import detect_strikethrough_enhanced, XMarkDetectionConfig
    >>> config = XMarkDetectionConfig(min_line_length=10, diagonal_tolerance=15)
    >>> result = detect_strikethrough_enhanced(pdf_path, page_num, bbox=None, config=config)
    >>> if result.has_xmarks:
    >>>     print(f"Found {result.xmark_count} X-marks with confidence {result.confidence:.2f}")
    >>>     print(f"Flags: {result.flags}")

Performance:
    - Target: <5ms per page (clean pages)
    - Target: <50ms per page (pages with X-marks)
    - Uses opencv LSD for accurate line detection

Architecture:
    - Stage 1: Render PDF page to image (PyMuPDF)
    - Stage 2: Detect all lines with LSD
    - Stage 3: Filter diagonal lines (/ and \\)
    - Stage 4: Find crossing pairs (X-marks)
    - Stage 5: Confidence scoring and validation
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Optional, Set
import math

# Conditional opencv import (graceful degradation)
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    cv2 = None
    np = None

# PyMuPDF is required for PDF rendering
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None


# ============================================================================
# Configuration and Result Classes
# ============================================================================

@dataclass
class XMarkDetectionConfig:
    """
    Configuration for X-mark detection algorithm.

    Attributes:
        min_line_length: Minimum line length in pixels (filter noise)
        diagonal_tolerance: Angle tolerance for diagonal lines (degrees from 45°)
        proximity_threshold: Max distance between line centers to be considered crossing (pixels)
        confidence_threshold: Minimum confidence score to report X-mark (0.0-1.0)
        render_dpi: DPI for PDF rendering (higher = more accurate but slower)
    """
    min_line_length: float = 10.0
    diagonal_tolerance: float = 15.0  # ±15° from 45° and -45°
    proximity_threshold: float = 20.0
    confidence_threshold: float = 0.5
    render_dpi: int = 300

    def __post_init__(self):
        """Validate configuration values."""
        if not (0 < self.min_line_length < 1000):
            raise ValueError(f"min_line_length must be 0-1000, got {self.min_line_length}")
        if not (0 < self.diagonal_tolerance < 90):
            raise ValueError(f"diagonal_tolerance must be 0-90, got {self.diagonal_tolerance}")
        if not (0 < self.proximity_threshold < 1000):
            raise ValueError(f"proximity_threshold must be 0-1000, got {self.proximity_threshold}")
        if not (0.0 <= self.confidence_threshold <= 1.0):
            raise ValueError(f"confidence_threshold must be 0.0-1.0, got {self.confidence_threshold}")
        if not (72 <= self.render_dpi <= 600):
            raise ValueError(f"render_dpi must be 72-600, got {self.render_dpi}")


@dataclass
class DetectedLine:
    """Detected line segment with metadata."""
    x1: float
    y1: float
    x2: float
    y2: float
    angle: float
    length: float

    @property
    def x_center(self) -> float:
        return (self.x1 + self.x2) / 2

    @property
    def y_center(self) -> float:
        return (self.y1 + self.y2) / 2


@dataclass
class XMarkCandidate:
    """Potential X-mark from crossing diagonal line pairs."""
    line1: DetectedLine
    line2: DetectedLine
    center_x: float
    center_y: float
    confidence: float
    bbox: Tuple[float, float, float, float]


@dataclass
class XMarkDetectionResult:
    """
    Result from X-mark detection with detailed metrics.

    Attributes:
        has_xmarks: True if X-marks detected above confidence threshold
        xmark_count: Number of X-marks detected
        confidence: Highest confidence score (0.0-1.0)
        flags: Set of detection flags (e.g., {'high_confidence', 'multiple_xmarks'})
        candidates: List of XMarkCandidate objects (detailed detection data)
        metrics: Dictionary of detection metrics
    """
    has_xmarks: bool
    xmark_count: int
    confidence: float
    flags: Set[str] = field(default_factory=set)
    candidates: List[XMarkCandidate] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert result to dictionary (for serialization)."""
        return {
            'has_xmarks': self.has_xmarks,
            'xmark_count': self.xmark_count,
            'confidence': self.confidence,
            'flags': list(self.flags),
            'candidate_count': len(self.candidates),
            'metrics': self.metrics
        }


# ============================================================================
# Core Detection Functions
# ============================================================================

def _render_page_to_image(pdf_path: Path, page_num: int, dpi: int = 300) -> 'np.ndarray':
    """
    Render PDF page to numpy image array.

    Args:
        pdf_path: Path to PDF file
        page_num: Page number (0-indexed)
        dpi: Rendering DPI (higher = better quality but slower)

    Returns:
        numpy array (H, W, 3) BGR image

    Raises:
        ImportError: If PyMuPDF not available
        RuntimeError: If PDF rendering fails
    """
    if not PYMUPDF_AVAILABLE:
        raise ImportError("PyMuPDF (fitz) is required for PDF rendering")

    try:
        doc = fitz.open(str(pdf_path))
        if page_num < 0 or page_num >= len(doc):
            raise ValueError(f"Invalid page number {page_num}, PDF has {len(doc)} pages")

        page = doc[page_num]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)

        # Convert pixmap to numpy array
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)

        # Convert RGBA to BGR if needed
        if pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)

        doc.close()
        return img

    except Exception as e:
        raise RuntimeError(f"Failed to render PDF page {page_num}: {e}") from e


def _detect_lines_lsd(img: 'np.ndarray') -> List[DetectedLine]:
    """
    Detect all line segments in image using LSD (Line Segment Detector).

    LSD is more accurate than Hough transform for this use case.

    Args:
        img: BGR image (H, W, 3)

    Returns:
        List of DetectedLine objects
    """
    if not OPENCV_AVAILABLE:
        raise ImportError("opencv-python is required for line detection")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    lsd = cv2.createLineSegmentDetector(0)
    lines = lsd.detect(gray)[0]

    detected = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
            length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

            detected.append(DetectedLine(
                x1=x1, y1=y1, x2=x2, y2=y2,
                angle=angle, length=length
            ))

    return detected


def _filter_diagonal_lines(
    lines: List[DetectedLine],
    angle_tolerance: float = 15.0,
    min_length: float = 10.0
) -> Tuple[List[DetectedLine], List[DetectedLine]]:
    """
    Filter lines into two diagonal groups: / and \\.

    Args:
        lines: List of all detected lines
        angle_tolerance: Tolerance in degrees from 45° and -45°
        min_length: Minimum line length to consider

    Returns:
        (positive_diagonals, negative_diagonals)
        - positive_diagonals: / lines (around 45°)
        - negative_diagonals: \\ lines (around -45° or 135°)
    """
    positive_diagonal = []  # / lines
    negative_diagonal = []  # \ lines

    for line in lines:
        if line.length < min_length:
            continue

        # Normalize angle to -180 to 180
        angle = line.angle % 360
        if angle > 180:
            angle -= 360

        # Positive diagonal: 45° ± tolerance
        target_45 = 45
        if abs(angle - target_45) <= angle_tolerance:
            positive_diagonal.append(line)

        # Negative diagonal: -45° ± tolerance OR 135° ± tolerance
        target_neg_45 = -45
        target_135 = 135
        if (abs(angle - target_neg_45) <= angle_tolerance or
            abs(angle - target_135) <= angle_tolerance):
            negative_diagonal.append(line)

    return positive_diagonal, negative_diagonal


def _find_crossing_pairs(
    pos_lines: List[DetectedLine],
    neg_lines: List[DetectedLine],
    max_distance: float = 20.0
) -> List[XMarkCandidate]:
    """
    Find pairs of diagonal lines that cross to form X-marks.

    Args:
        pos_lines: Positive diagonal lines (/)
        neg_lines: Negative diagonal lines (\\)
        max_distance: Maximum distance between line centers (pixels)

    Returns:
        List of XMarkCandidate objects, sorted by confidence (descending)
    """
    candidates = []

    for pos in pos_lines:
        for neg in neg_lines:
            # Check if line centers are close enough
            center_dist = math.sqrt(
                (pos.x_center - neg.x_center)**2 +
                (pos.y_center - neg.y_center)**2
            )

            if center_dist < max_distance:
                # Calculate crossing point
                cross_x = (pos.x_center + neg.x_center) / 2
                cross_y = (pos.y_center + neg.y_center) / 2

                # Bounding box around the X
                min_x = min(pos.x1, pos.x2, neg.x1, neg.x2)
                max_x = max(pos.x1, pos.x2, neg.x1, neg.x2)
                min_y = min(pos.y1, pos.y2, neg.y1, neg.y2)
                max_y = max(pos.y1, pos.y2, neg.y1, neg.y2)

                # Confidence scoring (3 factors, weighted average)
                # 1. Center proximity (closer = better)
                center_score = 1.0 - (center_dist / max_distance)

                # 2. Length similarity (more similar = better)
                length_ratio = min(pos.length, neg.length) / max(pos.length, neg.length)

                # 3. Angle perpendicularity (closer to 90° = better)
                angle_diff = abs(abs(pos.angle - neg.angle) - 90)
                angle_score = 1.0 - (angle_diff / 45)  # Ideal: 90°, worst: 45° off

                confidence = (center_score + length_ratio + angle_score) / 3.0

                candidates.append(XMarkCandidate(
                    line1=pos,
                    line2=neg,
                    center_x=cross_x,
                    center_y=cross_y,
                    confidence=confidence,
                    bbox=(min_x, min_y, max_x, max_y)
                ))

    # Sort by confidence (highest first)
    candidates.sort(key=lambda x: x.confidence, reverse=True)
    return candidates


# ============================================================================
# Public API
# ============================================================================

def detect_strikethrough_enhanced(
    pdf_path: Path,
    page_num: int,
    bbox: Optional[Tuple[float, float, float, float]] = None,
    config: Optional[XMarkDetectionConfig] = None
) -> XMarkDetectionResult:
    """
    Detect X-marks/strikethrough in a PDF page with detailed results.

    This is the primary API for strikethrough detection with full configurability
    and detailed result information.

    Args:
        pdf_path: Path to PDF file
        page_num: Page number (0-indexed)
        bbox: Optional bounding box to restrict search (x0, y0, x1, y1) in PDF coordinates
        config: Detection configuration (uses defaults if None)

    Returns:
        XMarkDetectionResult with detection status, confidence, flags, and metrics

    Raises:
        ImportError: If opencv or PyMuPDF not available
        ValueError: If invalid parameters
        RuntimeError: If detection fails

    Example:
        >>> result = detect_strikethrough_enhanced(pdf_path, 0)
        >>> if result.has_xmarks:
        >>>     print(f"Detected {result.xmark_count} X-marks")
        >>>     print(f"Confidence: {result.confidence:.2f}")
        >>>     print(f"Flags: {result.flags}")
    """
    # Validate dependencies
    if not OPENCV_AVAILABLE:
        raise ImportError("opencv-python is required for X-mark detection")
    if not PYMUPDF_AVAILABLE:
        raise ImportError("PyMuPDF (fitz) is required for PDF rendering")

    # Use default config if not provided
    if config is None:
        config = XMarkDetectionConfig()

    # Initialize result
    result = XMarkDetectionResult(
        has_xmarks=False,
        xmark_count=0,
        confidence=0.0,
        flags=set(),
        candidates=[],
        metrics={}
    )

    try:
        # Stage 1: Render PDF page to image
        img = _render_page_to_image(pdf_path, page_num, dpi=config.render_dpi)
        result.metrics['image_height'] = img.shape[0]
        result.metrics['image_width'] = img.shape[1]

        # Stage 2: Detect all lines with LSD
        all_lines = _detect_lines_lsd(img)
        result.metrics['total_lines'] = len(all_lines)

        if not all_lines:
            # No lines detected, definitely no X-marks
            return result

        # Stage 3: Filter diagonal lines
        pos_lines, neg_lines = _filter_diagonal_lines(
            all_lines,
            angle_tolerance=config.diagonal_tolerance,
            min_length=config.min_line_length
        )
        result.metrics['positive_diagonal_lines'] = len(pos_lines)
        result.metrics['negative_diagonal_lines'] = len(neg_lines)

        if not pos_lines or not neg_lines:
            # Need both / and \ for X-marks
            result.flags.add('missing_diagonal_pair')
            return result

        # Stage 4: Find crossing pairs (X-marks)
        candidates = _find_crossing_pairs(
            pos_lines,
            neg_lines,
            max_distance=config.proximity_threshold
        )
        result.metrics['raw_candidates'] = len(candidates)

        if not candidates:
            # No crossing pairs found
            result.flags.add('no_crossings_found')
            return result

        # Stage 5: Filter by confidence threshold
        high_conf_candidates = [
            c for c in candidates
            if c.confidence >= config.confidence_threshold
        ]

        if not high_conf_candidates:
            # Candidates exist but below confidence threshold
            result.flags.add('low_confidence_candidates')
            result.metrics['max_candidate_confidence'] = candidates[0].confidence
            return result

        # X-marks detected!
        result.has_xmarks = True
        result.xmark_count = len(high_conf_candidates)
        result.confidence = high_conf_candidates[0].confidence  # Highest confidence
        result.candidates = high_conf_candidates

        # Populate flags
        if result.confidence > 0.8:
            result.flags.add('high_confidence')
        elif result.confidence > 0.6:
            result.flags.add('medium_confidence')
        else:
            result.flags.add('low_confidence')

        if result.xmark_count > 3:
            result.flags.add('multiple_xmarks')
        elif result.xmark_count > 1:
            result.flags.add('few_xmarks')
        else:
            result.flags.add('single_xmark')

        logging.info(f"X-mark detection: Found {result.xmark_count} X-marks on page {page_num} "
                     f"with confidence {result.confidence:.2f}")

        return result

    except Exception as e:
        logging.error(f"X-mark detection failed for page {page_num}: {e}", exc_info=True)
        raise


def detect_strikethrough(
    pdf_path: Path,
    page_num: int,
    confidence_threshold: float = 0.5
) -> bool:
    """
    Legacy/simplified API for X-mark detection (returns boolean).

    This function provides backward compatibility and a simpler interface
    for basic detection needs. For detailed results, use detect_strikethrough_enhanced().

    Args:
        pdf_path: Path to PDF file
        page_num: Page number (0-indexed)
        confidence_threshold: Minimum confidence to report positive (0.0-1.0)

    Returns:
        True if X-marks detected above threshold, False otherwise

    Example:
        >>> if detect_strikethrough(pdf_path, 0):
        >>>     print("This page has sous-rature!")
    """
    try:
        config = XMarkDetectionConfig(confidence_threshold=confidence_threshold)
        result = detect_strikethrough_enhanced(pdf_path, page_num, config=config)
        return result.has_xmarks
    except ImportError:
        logging.warning("X-mark detection unavailable (opencv or PyMuPDF not installed)")
        return False
    except Exception as e:
        logging.error(f"X-mark detection error: {e}")
        return False


# ============================================================================
# Module Initialization
# ============================================================================

# Log import status
if not OPENCV_AVAILABLE:
    logging.warning("opencv-python not available - X-mark detection will not work")
if not PYMUPDF_AVAILABLE:
    logging.warning("PyMuPDF not available - X-mark detection will not work")
