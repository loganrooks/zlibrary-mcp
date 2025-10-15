#!/usr/bin/env python3
"""
Targeted analysis of specific pages with known sous rature instances.

Based on user's locations:
- Derrida p.110 (written p.19): Two instances at top
- Derrida p.135 (written p.44): "The Outside is the Inside" - "is" crossed out
- Heidegger p.79-80: 4 erasures of "Being"/"Sein" per page
- Heidegger p.85-88: 2 erasures per page

User notes: "More like X's than strikethroughs"
"""

import fitz
from pathlib import Path
import json


def analyze_page_deeply(page: fitz.Page, page_num: int, description: str):
    """
    Deep analysis of a specific page looking for strikethrough evidence.

    Args:
        page: PyMuPDF page object
        page_num: Page number (1-indexed)
        description: Description of what should be on this page
    """
    print(f"\n{'='*80}")
    print(f"Page {page_num}: {description}")
    print(f"{'='*80}\n")

    # 1. Extract text to see what PyMuPDF returns
    print("1. TEXT EXTRACTION")
    print("-" * 40)
    text = page.get_text("text")
    print(f"First 500 chars:\n{text[:500]}\n")

    # 2. Check for the specific words that should be crossed out
    print("2. SEARCHING FOR TARGET WORDS")
    print("-" * 40)

    target_words = ["is", "Being", "Sein"]
    for word in target_words:
        if word in text:
            # Find context around the word
            idx = text.find(word)
            context_start = max(0, idx - 50)
            context_end = min(len(text), idx + len(word) + 50)
            context = text[context_start:context_end]
            print(f"Found '{word}' at position {idx}:")
            print(f"  Context: ...{context}...")

    # 3. Check block structure for anything unusual
    print("\n3. BLOCK/SPAN ANALYSIS")
    print("-" * 40)
    blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT).get("blocks", [])

    text_blocks = [b for b in blocks if b.get('type') == 0]
    image_blocks = [b for b in blocks if b.get('type') == 1]

    print(f"Text blocks: {len(text_blocks)}")
    print(f"Image blocks: {len(image_blocks)}")

    if image_blocks:
        print("\n⚠️ IMAGE BLOCKS FOUND - Strikethrough might be in images!")
        for i, img_block in enumerate(image_blocks[:3]):
            bbox = img_block.get('bbox', (0, 0, 0, 0))
            print(f"  Image {i+1}: bbox={bbox}")

    # Look for spans containing target words
    print("\nSpans containing target words:")
    for block in text_blocks[:10]:  # First 10 text blocks
        for line in block.get('lines', []):
            for span in line.get('spans', []):
                span_text = span.get('text', '')
                if any(word in span_text for word in target_words):
                    print(f"  Span: '{span_text}'")
                    print(f"    flags: {span.get('flags', 0)} (binary: {bin(span.get('flags', 0))})")
                    print(f"    font: {span.get('font', 'unknown')}")
                    print(f"    size: {span.get('size', 0)}")
                    print(f"    bbox: {span.get('bbox', (0,0,0,0))}")

    # 4. Check all drawings on this page
    print("\n4. DRAWINGS ANALYSIS (Line Art)")
    print("-" * 40)
    try:
        drawings = page.get_drawings()
        print(f"Total drawings: {len(drawings)}")

        if drawings:
            # Look for ALL drawings, not just horizontal lines
            # X marks would be diagonal lines or multiple line segments
            print("\nAll drawings (first 20):")
            for i, drawing in enumerate(drawings[:20]):
                rect = drawing.get('rect', (0, 0, 0, 0))
                items = drawing.get('items', [])
                print(f"  Drawing {i+1}:")
                print(f"    rect: {rect}")
                print(f"    items: {len(items)} drawing items")

                # Check for line items
                for item in items[:3]:  # First 3 items
                    if item[0] == 'l':  # Line item
                        print(f"      Line from {item[1]} to {item[2]}")
    except Exception as e:
        print(f"⚠️ Error getting drawings: {e}")

    # 5. Check for special Unicode characters
    print("\n5. UNICODE ANALYSIS")
    print("-" * 40)

    # Look for strikethrough Unicode characters or combining marks
    # Unicode has strikethrough combining characters: U+0336 (combining long stroke overlay)
    strikethrough_chars = [
        '\u0336',  # Combining long stroke overlay
        '\u0337',  # Combining short stroke overlay
        '\u0338',  # Combining long solidus overlay
        '\u0335',  # Combining short stroke overlay
    ]

    for char in strikethrough_chars:
        if char in text:
            print(f"✅ Found Unicode strikethrough char: U+{ord(char):04X}")
            idx = text.find(char)
            context = text[max(0, idx-20):min(len(text), idx+20)]
            print(f"   Context: ...{context}...")

    # 6. Render page to image (if X marks are visual, they'll be in the render)
    print("\n6. PAGE RENDERING CHECK")
    print("-" * 40)
    try:
        # Render at low resolution just to check
        pix = page.get_pixmap(dpi=72)
        print(f"Page rendered successfully: {pix.width}x{pix.height} pixels")
        print("(X marks would be visible in rendered image if they exist)")
    except Exception as e:
        print(f"⚠️ Error rendering page: {e}")

    return {
        "page_num": page_num,
        "text_blocks": len(text_blocks),
        "image_blocks": len(image_blocks),
        "drawings": len(drawings) if 'drawings' in locals() else 0,
        "text_sample": text[:200]
    }


def main():
    """Analyze specific pages with known sous rature instances."""

    # Test cases from user
    test_cases = [
        {
            "file": "test_files/DerridaJacques_OfGrammatology_1268316.pdf",
            "pages": [
                (110, "written p.19, two instances at top"),
                (135, "written p.44, header 'The Outside is the Inside'")
            ]
        },
        {
            "file": "test_files/HeideggerMartin_TheQuestionOfBeing_964793.pdf",
            "pages": [
                (79, "4 erasures of Being/Sein"),
                (80, "4 erasures of Being/Sein"),
                (85, "2 erasures per page"),
                (86, "2 erasures per page"),
                (87, "2 erasures per page"),
                (88, "2 erasures per page")
            ]
        }
    ]

    all_findings = []

    for test_case in test_cases:
        pdf_path = Path(test_case["file"])

        if not pdf_path.exists():
            print(f"⚠️ File not found: {pdf_path}")
            continue

        print(f"\n{'#'*80}")
        print(f"# {pdf_path.name}")
        print(f"{'#'*80}")

        try:
            doc = fitz.open(str(pdf_path))

            for page_num, description in test_case["pages"]:
                # PyMuPDF uses 0-indexed pages
                if page_num >= len(doc):
                    print(f"⚠️ Page {page_num} exceeds document length {len(doc)}")
                    continue

                page = doc[page_num - 1]  # Convert to 0-indexed
                findings = analyze_page_deeply(page, page_num, description)
                all_findings.append(findings)

            doc.close()

        except Exception as e:
            print(f"❌ Error analyzing {pdf_path.name}: {e}")
            import traceback
            traceback.print_exc()

    # Save findings
    output_file = Path("test_specific_pages_findings.json")
    with open(output_file, 'w') as f:
        json.dump(all_findings, f, indent=2, default=str)

    print(f"\n{'='*80}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*80}")
    print(f"Findings saved to: {output_file}")
    print("\nKey question: Do the extracted text strings contain the crossed-out words")
    print("WITHOUT any indication of the crossing-out?")
    print("\nIf YES: X marks are visual overlays that OCR/extraction ignores")
    print("If NO: Text might be missing or have special encoding")


if __name__ == "__main__":
    main()
