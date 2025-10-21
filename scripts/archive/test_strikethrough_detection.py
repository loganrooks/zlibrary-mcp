#!/usr/bin/env python3
"""
Test script to analyze strikethrough detection in philosophy PDFs.

Tests PyMuPDF's capabilities for detecting Derrida's sous rature and
Heidegger's crossed-out Being (Sein).

Created: 2025-10-14
Purpose: Validate Phase 2 strikethrough detection strategy
"""

import fitz  # PyMuPDF
from pathlib import Path
import json


def analyze_strikethrough_methods(pdf_path: Path, sample_pages: int = 20):
    """
    Analyze how strikethrough appears in PyMuPDF data structures.

    Tests three methods:
    1. Annotations (page.annots() - easiest)
    2. Text flags (span['flags'] - unlikely but check)
    3. Drawings/line art (page.get_drawings() - most likely)

    Args:
        pdf_path: Path to PDF file
        sample_pages: Number of pages to sample

    Returns:
        Dict with findings from each method
    """
    print(f"\n{'='*80}")
    print(f"Analyzing: {pdf_path.name}")
    print(f"{'='*80}\n")

    doc = fitz.open(str(pdf_path))
    findings = {
        "file": pdf_path.name,
        "total_pages": len(doc),
        "methods": {
            "annotations": {"found": False, "details": []},
            "text_flags": {"found": False, "details": []},
            "drawings": {"found": False, "details": []}
        }
    }

    # Sample pages (first N pages, middle, last few)
    pages_to_check = list(range(min(sample_pages, len(doc))))
    if len(doc) > sample_pages:
        # Add some middle pages
        middle = len(doc) // 2
        pages_to_check.extend(range(middle, min(middle + 5, len(doc))))

    for page_num in pages_to_check:
        page = doc[page_num]
        print(f"\n--- Page {page_num + 1} ---")

        # Method 1: Check annotations
        print("Checking annotations...")
        annot_count = 0
        for annot in page.annots():
            annot_count += 1
            annot_type = annot.type[0]  # Annotation type code
            annot_name = annot.type[1]  # Annotation name

            # PDF_ANNOT_STRIKEOUT = 9
            if annot_type == 9 or "strike" in annot_name.lower():
                findings["methods"]["annotations"]["found"] = True
                rect = annot.rect
                # Try to get text under annotation
                text = page.get_textbox(rect)
                details = {
                    "page": page_num + 1,
                    "type": annot_name,
                    "rect": tuple(rect),
                    "text": text
                }
                findings["methods"]["annotations"]["details"].append(details)
                print(f"  ✅ STRIKETHROUGH ANNOTATION FOUND!")
                print(f"     Type: {annot_name}, Text: '{text}'")

        if annot_count > 0:
            print(f"  Found {annot_count} annotations (none were strikethrough)")

        # Method 2: Check text flags
        print("Checking text span flags...")
        blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT).get("blocks", [])
        unusual_flags = []

        for block in blocks:
            if block.get('type') != 0:  # Skip non-text blocks
                continue

            for line in block.get('lines', []):
                for span in line.get('spans', []):
                    flags = span.get('flags', 0)

                    # Check for unusual flag combinations
                    # Standard flags: 1=superscript, 2=italic, 4=serifed, 8=mono, 16=bold
                    # Check if there are other bits set
                    standard_bits = 1 | 2 | 4 | 8 | 16  # = 31
                    unknown_bits = flags & ~standard_bits

                    if unknown_bits != 0:
                        unusual_flags.append({
                            "text": span.get('text', '')[:50],
                            "flags": flags,
                            "unknown_bits": unknown_bits
                        })

        if unusual_flags:
            findings["methods"]["text_flags"]["found"] = True
            findings["methods"]["text_flags"]["details"] = unusual_flags[:5]  # First 5
            print(f"  ⚠️ Found {len(unusual_flags)} spans with unusual flags")
            for uf in unusual_flags[:3]:
                print(f"     Text: '{uf['text']}', flags={uf['flags']}, unknown={uf['unknown_bits']}")

        # Method 3: Check drawings (line art)
        print("Checking drawings (line art)...")
        try:
            drawings = page.get_drawings()
            line_drawings = []

            for drawing in drawings:
                # Check if this is a horizontal line (potential strikethrough)
                # Drawings have 'rect' and 'items' attributes
                if 'rect' in drawing:
                    rect = drawing['rect']
                    width = rect[2] - rect[0]
                    height = rect[3] - rect[1]

                    # Horizontal line heuristic: width >> height
                    if width > 10 and height < 3:
                        line_drawings.append({
                            "rect": tuple(rect),
                            "width": width,
                            "height": height,
                            "type": drawing.get('type', 'unknown')
                        })

            if line_drawings:
                findings["methods"]["drawings"]["found"] = True
                findings["methods"]["drawings"]["details"].extend(line_drawings[:10])
                print(f"  ✅ Found {len(line_drawings)} potential strikethrough lines!")

                # Try to find text that intersects with these lines
                for line_draw in line_drawings[:3]:
                    line_rect = line_draw['rect']
                    # Expand rect slightly to catch overlapping text
                    expanded = (
                        line_rect[0] - 5, line_rect[1] - 5,
                        line_rect[2] + 5, line_rect[3] + 5
                    )
                    text_under = page.get_textbox(expanded)
                    if text_under.strip():
                        print(f"     Line at y={line_rect[1]:.1f}, width={line_draw['width']:.1f}")
                        print(f"     Text nearby: '{text_under[:100]}'")

        except Exception as e:
            print(f"  ⚠️ Error getting drawings: {e}")

    doc.close()
    return findings


def main():
    """Run strikethrough analysis on philosophy PDFs."""

    test_files = [
        Path("test_files/DerridaJacques_OfGrammatology_1268316.pdf"),
        Path("test_files/HeideggerMartin_TheQuestionOfBeing_964793.pdf"),
    ]

    all_findings = []

    for pdf_path in test_files:
        if not pdf_path.exists():
            print(f"⚠️ File not found: {pdf_path}")
            continue

        try:
            findings = analyze_strikethrough_methods(pdf_path, sample_pages=30)
            all_findings.append(findings)
        except Exception as e:
            print(f"❌ Error analyzing {pdf_path.name}: {e}")
            import traceback
            traceback.print_exc()

    # Summary report
    print(f"\n{'='*80}")
    print("SUMMARY REPORT")
    print(f"{'='*80}\n")

    for finding in all_findings:
        print(f"File: {finding['file']}")
        print(f"  Total pages: {finding['total_pages']}")

        for method_name, method_data in finding['methods'].items():
            status = "✅ FOUND" if method_data['found'] else "❌ NOT FOUND"
            detail_count = len(method_data['details'])
            print(f"  {method_name.upper():20} {status:15} ({detail_count} instances)")

        print()

    # Save detailed findings
    output_file = Path("test_strikethrough_findings.json")
    with open(output_file, 'w') as f:
        json.dump(all_findings, f, indent=2, default=str)
    print(f"Detailed findings saved to: {output_file}")

    # Recommendations
    print(f"\n{'='*80}")
    print("RECOMMENDATIONS")
    print(f"{'='*80}\n")

    annotations_work = any(f['methods']['annotations']['found'] for f in all_findings)
    drawings_work = any(f['methods']['drawings']['found'] for f in all_findings)
    flags_work = any(f['methods']['text_flags']['found'] for f in all_findings)

    if annotations_work:
        print("✅ Annotations method works - use page.annots() for strikethrough detection")
    if drawings_work:
        print("✅ Drawings method works - use page.get_drawings() for line art analysis")
    if flags_work:
        print("⚠️ Unusual flags found - may indicate strikethrough in font flags")

    if not (annotations_work or drawings_work or flags_work):
        print("❌ No strikethrough detected with PyMuPDF")
        print("   Recommendation: May need alternative library (borb, pdfplumber)")
        print("   Or: Strikethrough may be encoded differently in these PDFs")


if __name__ == "__main__":
    main()
