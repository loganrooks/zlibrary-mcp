#!/usr/bin/env python3
"""
Validation script for multi-page footnote continuation feature.
Tests existing fixtures to check for incomplete/multi-page footnotes.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import fitz  # PyMuPDF
from lib.rag_processing import _detect_footnotes_in_page
from lib.footnote_continuation import (
    CrossPageFootnoteParser,
    is_footnote_incomplete,
    FootnoteWithContinuation
)
from lib.footnote_corruption_model import apply_corruption_recovery


def test_pdf_footnotes(pdf_path: str):
    """Test footnote detection on a PDF file."""
    print(f"\n{'='*70}")
    print(f"TESTING: {pdf_path}")
    print(f"{'='*70}\n")

    doc = fitz.open(pdf_path)
    all_footnotes_by_page = {}

    # Detect footnotes on all pages
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_footnotes = _detect_footnotes_in_page(page, page_num)

        if page_footnotes and page_footnotes.get('definitions'):
            all_footnotes_by_page[page_num] = page_footnotes

    doc.close()

    # Apply corruption recovery
    all_footnotes_recovered = {}
    for page_num, page_fns in all_footnotes_by_page.items():
        markers = page_fns.get('markers', [])
        definitions = page_fns.get('definitions', [])

        # Apply corruption recovery
        recovered_markers, recovered_definitions = apply_corruption_recovery(markers, definitions)

        # Store recovered footnotes
        all_footnotes_recovered[page_num] = {
            'markers': recovered_markers,
            'definitions': recovered_definitions
        }

    # Check for incomplete footnotes and multi-page continuations
    continuation_parser = CrossPageFootnoteParser()

    for page_num in sorted(all_footnotes_recovered.keys()):
        page_footnotes = all_footnotes_recovered[page_num]
        definitions = page_footnotes.get('definitions', [])

        print(f"\n--- Page {page_num + 1} ({len(definitions)} footnotes) ---")

        for fn_def in definitions:
            marker = fn_def.get('marker', '?')
            content = fn_def.get('content', '')

            # Check if footnote appears incomplete
            is_incomplete, incomplete_confidence, incomplete_reason = is_footnote_incomplete(content)

            print(f"\n  Footnote {marker}:")
            print(f"    Complete: {not is_incomplete}")

            if is_incomplete:
                print(f"    INCOMPLETE: {incomplete_reason}")
                print(f"    Confidence: {incomplete_confidence:.2f}")

            # Show content preview
            content_preview = content[:150].replace('\n', ' ')
            print(f"    Content: {content_preview}...")

    # Test continuation parser
    print(f"\n{'='*70}")
    print("TESTING CROSS-PAGE CONTINUATION PARSER")
    print(f"{'='*70}\n")

    # Feed all footnotes to continuation parser in page order
    all_completed = []
    for page_num in sorted(all_footnotes_recovered.keys()):
        page_footnotes = all_footnotes_recovered[page_num]
        definitions = page_footnotes.get('definitions', [])

        # Process this page
        completed_on_page = continuation_parser.process_page(definitions, page_num + 1)
        all_completed.extend(completed_on_page)

    # Finalize to get any remaining incomplete footnotes
    final_footnotes = continuation_parser.finalize()

    print(f"Total pages processed: {len(all_footnotes_recovered)}")
    print(f"Total footnotes after continuation merging: {len(final_footnotes)}")

    # Check for multi-page footnotes
    multipage_count = 0
    for fn in final_footnotes:
        pages = fn.pages
        if len(pages) > 1:
            multipage_count += 1

            print(f"\n  MULTI-PAGE FOOTNOTE DETECTED!")
            print(f"    Marker: {fn.marker}")
            print(f"    Pages: {pages}")
            print(f"    Continuation confidence: {fn.continuation_confidence:.2f}")

            # Show merged content preview
            content_preview = fn.content[:200].replace('\n', ' ')
            print(f"    Merged content: {content_preview}...")

    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Total footnotes: {len(final_footnotes)}")
    print(f"Multi-page footnotes: {multipage_count}")

    # Convert footnotes to dict for JSON serialization
    footnotes_dict = []
    for fn in final_footnotes:
        footnotes_dict.append({
            'marker': fn.marker,
            'content': fn.content[:300],  # Truncate for JSON
            'pages': fn.pages,
            'is_complete': fn.is_complete,
            'continuation_confidence': fn.continuation_confidence
        })

    return {
        'pdf_path': pdf_path,
        'total_footnotes': len(final_footnotes),
        'multipage_footnotes': multipage_count,
        'footnotes': footnotes_dict
    }


if __name__ == '__main__':
    # Test Kant fixture
    kant_result = test_pdf_footnotes('test_files/kant_critique_pages_80_85.pdf')

    # Test Derrida fixture
    derrida_result = test_pdf_footnotes('test_files/derrida_footnote_pages_120_125.pdf')

    # Save results to file
    results = {
        'kant': kant_result,
        'derrida': derrida_result
    }

    with open('footnote_validation_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n\nResults saved to: footnote_validation_results.json")
