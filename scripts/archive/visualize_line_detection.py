#!/usr/bin/env python3
"""
Visualize line detection results by rendering pages with detected lines highlighted
"""

import fitz  # PyMuPDF
import cv2
import numpy as np
from pathlib import Path
import json
import sys


def render_page_to_image(page: fitz.Page, dpi: int = 300) -> np.ndarray:
    """Render a PDF page to a high-resolution image"""
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)

    if pix.n == 3:  # RGB
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    elif pix.n == 4:  # RGBA
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)

    return img


def visualize_page(pdf_path: Path, page_num: int, results_data: dict, output_path: Path, dpi: int = 300):
    """
    Visualize detected lines on a specific page

    Color coding:
    - GREEN: under_text (potential underlines - may be handwritten)
    - RED: through_text (potential strikethrough)
    - BLUE: over_text
    - YELLOW: unclear
    - GRAY: no_text_nearby
    """
    doc = fitz.open(pdf_path)
    page = doc[page_num]

    # Render page
    img = render_page_to_image(page, dpi=dpi)

    # Find the page results
    page_results = None
    for p in results_data['scanned_pages']:
        if p['page_num'] == page_num:
            page_results = p
            break

    if not page_results:
        print(f"No results found for page {page_num}", file=sys.stderr)
        doc.close()
        return

    # Color map for classifications
    color_map = {
        'under_text': (0, 255, 0),      # GREEN
        'through_text': (0, 0, 255),    # RED
        'over_text': (255, 0, 0),       # BLUE
        'unclear': (0, 255, 255),       # YELLOW
        'no_text_nearby': (128, 128, 128)  # GRAY
    }

    # Draw each classified line
    for classification in page_results['classifications']:
        line_data = classification['line']
        cls = classification['classification']
        confidence = classification['confidence']

        x1 = line_data['x1']
        y1 = line_data['y1']
        x2 = line_data['x2']
        y2 = line_data['y2']

        color = color_map.get(cls, (255, 255, 255))

        # Draw line (thicker for higher confidence)
        thickness = 2 if confidence > 0.7 else 1
        cv2.line(img, (x1, y1), (x2, y2), color, thickness)

    # Add legend
    y_offset = 30
    legend_items = [
        ('Under text (underlines)', (0, 255, 0)),
        ('Through text (strikethrough)', (0, 0, 255)),
        ('Over text', (255, 0, 0)),
        ('Unclear', (0, 255, 255)),
        ('No text nearby', (128, 128, 128))
    ]

    for label, color in legend_items:
        cv2.putText(img, label, (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        y_offset += 30

    # Save output
    cv2.imwrite(str(output_path), img)
    print(f"Saved visualization to {output_path}", file=sys.stderr)

    doc.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Visualize line detection results')
    parser.add_argument('pdf_path', type=Path, help='Path to PDF file')
    parser.add_argument('results_json', type=Path, help='Path to results JSON')
    parser.add_argument('--page', type=int, required=True, help='Page number to visualize (0-indexed)')
    parser.add_argument('--output', type=Path, required=True, help='Output image path')
    parser.add_argument('--dpi', type=int, default=300, help='Rendering DPI')

    args = parser.parse_args()

    if not args.pdf_path.exists():
        print(f"Error: PDF file not found: {args.pdf_path}", file=sys.stderr)
        sys.exit(1)

    if not args.results_json.exists():
        print(f"Error: Results JSON not found: {args.results_json}", file=sys.stderr)
        sys.exit(1)

    # Load results
    with open(args.results_json) as f:
        results_data = json.load(f)

    visualize_page(
        args.pdf_path,
        args.page,
        results_data,
        args.output,
        dpi=args.dpi
    )


if __name__ == '__main__':
    main()
