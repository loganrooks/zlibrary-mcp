#!/usr/bin/env python3
"""
Extract full content of page 2 blocks 10 and 11 (the asterisk footnote).
"""

import fitz  # PyMuPDF

# Open the PDF
pdf_path = "test_files/kant_critique_pages_80_85.pdf"
doc = fitz.open(pdf_path)

page = doc[1]  # Page 2 (0-indexed)
page_height = page.rect.height
footnote_threshold = page_height * 0.80

blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

print("=" * 80)
print("PAGE 2 - BLOCK 10 AND 11 (ASTERISK FOOTNOTE)")
print("=" * 80)
print(f"Page height: {page_height}")
print(f"Footnote threshold (80%): {footnote_threshold}")
print()

# Block 10
if len(blocks) > 9:
    block10 = blocks[9]  # 0-indexed
    print("BLOCK 10:")
    print(f"BBox: {block10['bbox']}")
    print(f"Y-position: {block10['bbox'][1]}")
    print(f"In footnote area: {block10['bbox'][1] >= footnote_threshold}")
    print()

    block10_lines = []
    for line in block10.get("lines", []):
        line_text = ""
        for span in line["spans"]:
            line_text += span["text"]
        block10_lines.append(line_text.strip())

    block10_text = " ".join(block10_lines)
    print(f"Content ({len(block10_text)} chars):")
    print(block10_text)
    print()
    print("-" * 80)
    print()

# Block 11
if len(blocks) > 10:
    block11 = blocks[10]  # 0-indexed
    print("BLOCK 11:")
    print(f"BBox: {block11['bbox']}")
    print(f"Y-position: {block11['bbox'][1]}")
    print(f"In footnote area: {block11['bbox'][1] >= footnote_threshold}")
    print()

    block11_lines = []
    for line in block11.get("lines", []):
        line_text = ""
        for span in line["spans"]:
            line_text += span["text"]
        block11_lines.append(line_text.strip())

    block11_text = " ".join(block11_lines)
    print(f"Content ({len(block11_text)} chars):")
    print(block11_text)
    print()

    # Check if ends with "to"
    print(f"Ends with ' to': {block11_text.endswith(' to')}")
    print(f"Last 50 chars: ...{block11_text[-50:]}")

doc.close()
