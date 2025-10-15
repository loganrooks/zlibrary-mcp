#!/usr/bin/env python3
"""
Test PyMuPDF's native strikethrough detection capability

PyMuPDF can detect text formatting flags including strikethrough,
which is much more reliable than OpenCV line detection for digital PDFs.
"""

import fitz  # PyMuPDF
from pathlib import Path
import json
from dataclasses import dataclass, asdict
from typing import List
import sys


@dataclass
class StrikethroughSpan:
    """Represents a text span with strikethrough formatting"""
    page_num: int
    text: str
    bbox: tuple  # (x0, y0, x1, y1)
    font_name: str
    font_size: float
    flags: int


def detect_strikethrough_spans(pdf_path: Path, start_page: int = 0, end_page: int = None) -> dict:
    """
    Detect text spans with strikethrough formatting using PyMuPDF's native detection

    PyMuPDF text span flags (bitwise):
    - 2^0 (1): superscript
    - 2^1 (2): italic
    - 2^2 (4): serifed
    - 2^3 (8): monospaced
    - 2^4 (16): bold
    - 2^5 (32): strikethrough  ← This is what we're looking for!
    """
    doc = fitz.open(pdf_path)

    if end_page is None:
        end_page = len(doc)
    else:
        end_page = min(end_page, len(doc))

    results = {
        'pdf_path': str(pdf_path),
        'total_pages': len(doc),
        'pages_scanned': end_page - start_page,
        'strikethrough_spans': [],
        'summary': {
            'total_strikethrough_spans': 0,
            'pages_with_strikethrough': 0,
            'sample_text': []
        }
    }

    pages_with_strikethrough = set()

    for page_num in range(start_page, end_page):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if block["type"] == 0:  # Text block
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        flags = span.get("flags", 0)

                        # Check if strikethrough flag is set (2^5 = 32)
                        if flags & 32:  # Strikethrough flag
                            strikethrough_span = StrikethroughSpan(
                                page_num=page_num,
                                text=span["text"],
                                bbox=tuple(span["bbox"]),
                                font_name=span.get("font", "unknown"),
                                font_size=span.get("size", 0.0),
                                flags=flags
                            )

                            results['strikethrough_spans'].append(asdict(strikethrough_span))
                            results['summary']['total_strikethrough_spans'] += 1
                            pages_with_strikethrough.add(page_num)

                            # Collect sample text (first 10 examples)
                            if len(results['summary']['sample_text']) < 10:
                                results['summary']['sample_text'].append({
                                    'page': page_num,
                                    'text': span["text"][:100]  # First 100 chars
                                })

    results['summary']['pages_with_strikethrough'] = len(pages_with_strikethrough)

    doc.close()
    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Test PyMuPDF native strikethrough detection')
    parser.add_argument('pdf_path', type=Path, help='Path to PDF file')
    parser.add_argument('--start-page', type=int, default=0, help='Start page (0-indexed)')
    parser.add_argument('--end-page', type=int, help='End page (exclusive)')
    parser.add_argument('--output', type=Path, help='Output JSON file path')

    args = parser.parse_args()

    if not args.pdf_path.exists():
        print(f"Error: PDF file not found: {args.pdf_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Testing PyMuPDF strikethrough detection on: {args.pdf_path}", file=sys.stderr)
    print(f"Pages: {args.start_page} to {args.end_page or 'end'}", file=sys.stderr)
    print("", file=sys.stderr)

    results = detect_strikethrough_spans(
        args.pdf_path,
        start_page=args.start_page,
        end_page=args.end_page
    )

    # Print summary
    print("="*60, file=sys.stderr)
    print("SUMMARY", file=sys.stderr)
    print("="*60, file=sys.stderr)
    summary = results['summary']
    print(f"Total pages scanned: {results['pages_scanned']}", file=sys.stderr)
    print(f"Pages with strikethrough: {summary['pages_with_strikethrough']}", file=sys.stderr)
    print(f"Total strikethrough spans: {summary['total_strikethrough_spans']}", file=sys.stderr)
    print("", file=sys.stderr)

    if summary['sample_text']:
        print("Sample strikethrough text:", file=sys.stderr)
        for sample in summary['sample_text']:
            print(f"  Page {sample['page']}: {sample['text']}", file=sys.stderr)
    else:
        print("No strikethrough text detected.", file=sys.stderr)

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
