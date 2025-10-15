#!/usr/bin/env python3
"""
Line Classification Test Script for PDF Document Analysis

This script tests whether we can reliably distinguish between:
1. Handwritten underlines (from previous owners - should be ignored)
2. Printed strikethrough text (from authors - should be preserved)
3. Regular underlines (various sources)

Approach:
- Use PyMuPDF to extract text bounding boxes
- Use OpenCV to detect lines in rendered page images
- Compare line positions to text bbox positions
- Classify lines as: over_text, through_text, under_text, unclear
"""

import fitz  # PyMuPDF
import cv2
import numpy as np
from pathlib import Path
import json
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional
import sys


@dataclass
class TextBox:
    """Represents a text bounding box from PDF"""
    x0: float
    y0: float
    x1: float
    y1: float
    text: str

    @property
    def top(self) -> float:
        return self.y0

    @property
    def bottom(self) -> float:
        return self.y1

    @property
    def middle(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def height(self) -> float:
        return self.y1 - self.y0


@dataclass
class DetectedLine:
    """Represents a line detected in the page image"""
    x1: int
    y1: int
    x2: int
    y2: int
    angle: float
    length: float

    @property
    def is_horizontal(self, threshold_degrees: float = 15.0) -> bool:
        """Check if line is approximately horizontal"""
        return abs(self.angle) < threshold_degrees or abs(self.angle - 180) < threshold_degrees

    @property
    def avg_y(self) -> float:
        """Average Y coordinate of the line"""
        return (self.y1 + self.y2) / 2


@dataclass
class LineClassification:
    """Classification result for a detected line"""
    line: DetectedLine
    classification: str  # 'over_text', 'through_text', 'under_text', 'unclear', 'no_text_nearby'
    confidence: float  # 0.0 to 1.0
    nearby_text: Optional[str] = None
    text_bbox: Optional[TextBox] = None
    explanation: str = ""


def extract_text_boxes(page: fitz.Page) -> List[TextBox]:
    """Extract text bounding boxes from a PDF page using PyMuPDF"""
    boxes = []
    blocks = page.get_text("dict")["blocks"]

    for block in blocks:
        if block["type"] == 0:  # Text block
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    bbox = span["bbox"]
                    text = span["text"]
                    if text.strip():  # Only include non-empty text
                        boxes.append(TextBox(
                            x0=bbox[0],
                            y0=bbox[1],
                            x1=bbox[2],
                            y1=bbox[3],
                            text=text
                        ))

    return boxes


def render_page_to_image(page: fitz.Page, dpi: int = 300) -> np.ndarray:
    """Render a PDF page to a high-resolution image"""
    # Calculate zoom factor based on DPI
    zoom = dpi / 72.0  # PDF default is 72 DPI
    mat = fitz.Matrix(zoom, zoom)

    # Render page to pixmap
    pix = page.get_pixmap(matrix=mat)

    # Convert to numpy array
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)

    # Convert RGB to BGR for OpenCV
    if pix.n == 3:  # RGB
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    elif pix.n == 4:  # RGBA
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)

    return img


def detect_lines_opencv(img: np.ndarray, min_length: int = 50) -> List[DetectedLine]:
    """
    Detect lines in an image using OpenCV

    Uses multiple approaches:
    1. Hough Line Transform for straight lines
    2. Morphological operations to enhance line-like structures
    """
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Apply edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    # Detect lines using Hough Transform
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi/180,
        threshold=100,
        minLineLength=min_length,
        maxLineGap=10
    )

    detected_lines = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]

            # Calculate angle and length
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)

            detected_lines.append(DetectedLine(
                x1=int(x1),
                y1=int(y1),
                x2=int(x2),
                y2=int(y2),
                angle=float(angle),
                length=float(length)
            ))

    return detected_lines


def classify_line_position(
    line: DetectedLine,
    text_boxes: List[TextBox],
    page_height: int,
    dpi: int = 300
) -> LineClassification:
    """
    Classify a line's position relative to text

    Classification categories:
    - 'over_text': Line passes over the top of text (rare)
    - 'through_text': Line passes through the middle of text (strikethrough)
    - 'under_text': Line passes under the bottom of text (underline)
    - 'no_text_nearby': No text near this line
    - 'unclear': Ambiguous positioning
    """
    # Only classify horizontal lines
    if not line.is_horizontal:
        return LineClassification(
            line=line,
            classification='unclear',
            confidence=0.0,
            explanation="Not a horizontal line"
        )

    # Scale factor to convert PDF coordinates to image coordinates
    zoom = dpi / 72.0
    line_y = line.avg_y

    # Find text boxes that overlap horizontally with the line
    nearby_boxes = []
    line_x_min = min(line.x1, line.x2)
    line_x_max = max(line.x1, line.x2)

    for box in text_boxes:
        # Scale text box coordinates to image coordinates
        box_x0 = box.x0 * zoom
        box_x1 = box.x1 * zoom
        box_y0 = box.y0 * zoom
        box_y1 = box.y1 * zoom

        # Check horizontal overlap
        if not (box_x1 < line_x_min or box_x0 > line_x_max):
            # Check if line is reasonably close vertically (within 2x text height)
            text_height = box_y1 - box_y0
            if abs(line_y - (box_y0 + box_y1) / 2) < text_height * 2:
                nearby_boxes.append((box, box_y0, box_y1, (box_y0 + box_y1) / 2, text_height))

    if not nearby_boxes:
        return LineClassification(
            line=line,
            classification='no_text_nearby',
            confidence=0.9,
            explanation="No text found near this line"
        )

    # Analyze the closest text box
    closest_box = min(nearby_boxes, key=lambda b: abs(line_y - b[3]))
    box, box_y0, box_y1, box_middle, text_height = closest_box

    # Define thresholds (as fraction of text height)
    over_threshold = box_y0 - text_height * 0.2
    through_top = box_y0 + text_height * 0.25
    through_bottom = box_y1 - text_height * 0.25
    under_threshold = box_y1 + text_height * 0.2

    # Classify based on position
    if line_y < over_threshold:
        classification = 'over_text'
        confidence = 0.8
        explanation = f"Line is {box_y0 - line_y:.1f}px above text (top={box_y0:.1f})"
    elif line_y < through_top:
        classification = 'unclear'
        confidence = 0.4
        explanation = f"Line is near top of text (ambiguous region)"
    elif line_y <= through_bottom:
        classification = 'through_text'
        confidence = 0.9
        explanation = f"Line passes through middle of text (y={line_y:.1f}, middle={box_middle:.1f})"
    elif line_y <= under_threshold:
        classification = 'under_text'
        confidence = 0.85
        explanation = f"Line is {line_y - box_y1:.1f}px below text (bottom={box_y1:.1f})"
    else:
        classification = 'no_text_nearby'
        confidence = 0.7
        explanation = f"Line is too far below text ({line_y - box_y1:.1f}px)"

    return LineClassification(
        line=line,
        classification=classification,
        confidence=confidence,
        nearby_text=box.text[:50],  # First 50 chars
        text_bbox=box,
        explanation=explanation
    )


def scan_pdf_for_lines(
    pdf_path: Path,
    start_page: int = 0,
    end_page: int = 30,
    dpi: int = 300
) -> dict:
    """
    Scan a PDF for lines and classify them

    Returns a dictionary with results for each page
    """
    doc = fitz.open(pdf_path)
    results = {
        'pdf_path': str(pdf_path),
        'total_pages': len(doc),
        'scanned_pages': [],
        'summary': {
            'total_lines': 0,
            'over_text': 0,
            'through_text': 0,
            'under_text': 0,
            'unclear': 0,
            'no_text_nearby': 0
        }
    }

    end_page = min(end_page, len(doc))

    for page_num in range(start_page, end_page):
        print(f"Processing page {page_num + 1}/{end_page}...", file=sys.stderr)

        page = doc[page_num]

        # Extract text boxes
        text_boxes = extract_text_boxes(page)

        # Render page to image
        img = render_page_to_image(page, dpi=dpi)

        # Detect lines
        detected_lines = detect_lines_opencv(img, min_length=50)

        # Classify each line
        classifications = []
        for line in detected_lines:
            if line.is_horizontal:  # Only classify horizontal lines
                classification = classify_line_position(line, text_boxes, img.shape[0], dpi)
                classifications.append(classification)

                # Update summary
                results['summary']['total_lines'] += 1
                results['summary'][classification.classification] += 1

        page_result = {
            'page_num': page_num,
            'text_boxes_count': len(text_boxes),
            'lines_detected': len(detected_lines),
            'horizontal_lines': len([l for l in detected_lines if l.is_horizontal]),
            'classifications': [
                {
                    'line': asdict(c.line),
                    'classification': c.classification,
                    'confidence': c.confidence,
                    'nearby_text': c.nearby_text,
                    'explanation': c.explanation
                }
                for c in classifications
            ]
        }

        results['scanned_pages'].append(page_result)

    doc.close()
    return results


def main():
    """Main entry point for the script"""
    import argparse

    parser = argparse.ArgumentParser(description='Test line classification in PDFs')
    parser.add_argument('pdf_path', type=Path, help='Path to PDF file')
    parser.add_argument('--start-page', type=int, default=0, help='Start page (0-indexed)')
    parser.add_argument('--end-page', type=int, default=30, help='End page (exclusive)')
    parser.add_argument('--dpi', type=int, default=300, help='Rendering DPI')
    parser.add_argument('--output', type=Path, help='Output JSON file path')

    args = parser.parse_args()

    if not args.pdf_path.exists():
        print(f"Error: PDF file not found: {args.pdf_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning {args.pdf_path}", file=sys.stderr)
    print(f"Pages: {args.start_page} to {args.end_page}", file=sys.stderr)
    print(f"DPI: {args.dpi}", file=sys.stderr)
    print("", file=sys.stderr)

    results = scan_pdf_for_lines(
        args.pdf_path,
        start_page=args.start_page,
        end_page=args.end_page,
        dpi=args.dpi
    )

    # Print summary
    print("\n" + "="*60, file=sys.stderr)
    print("SUMMARY", file=sys.stderr)
    print("="*60, file=sys.stderr)
    summary = results['summary']
    print(f"Total horizontal lines detected: {summary['total_lines']}", file=sys.stderr)
    print(f"  - Over text:        {summary['over_text']}", file=sys.stderr)
    print(f"  - Through text:     {summary['through_text']}", file=sys.stderr)
    print(f"  - Under text:       {summary['under_text']}", file=sys.stderr)
    print(f"  - Unclear:          {summary['unclear']}", file=sys.stderr)
    print(f"  - No text nearby:   {summary['no_text_nearby']}", file=sys.stderr)
    print("="*60, file=sys.stderr)

    # Output results as JSON
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {args.output}", file=sys.stderr)
    else:
        print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
