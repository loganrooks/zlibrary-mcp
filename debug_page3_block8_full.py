#!/usr/bin/env python3
"""
Get full content of page 3, block 8 (the continuation).
"""

import fitz  # PyMuPDF

# Open the PDF
pdf_path = "test_files/kant_critique_pages_80_85.pdf"
doc = fitz.open(pdf_path)

page = doc[2]  # Page 3 (0-indexed)
page_height = page.rect.height
footnote_threshold = page_height * 0.80

blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

# Block 8 (0-indexed: 7)
block8 = blocks[7]

print(f"=" * 80)
print(f"PAGE 3 - BLOCK 8 (ASTERISK FOOTNOTE CONTINUATION)")
print(f"=" * 80)
print(f"Page height: {page_height}")
print(f"Footnote threshold (80%): {footnote_threshold}")
print()

print(f"BBox: {block8['bbox']}")
print(f"Y-position: {block8['bbox'][1]}")
print(f"In footnote area: {block8['bbox'][1] >= footnote_threshold}")
print()

block8_lines = []
for line in block8.get("lines", []):
    line_text = ""
    for span in line["spans"]:
        line_text += span["text"]
    block8_lines.append(line_text.strip())

block8_text = " ".join(block8_lines)
print(f"Content ({len(block8_text)} chars):")
print(block8_text)
print()

# Check for characteristics
print("CHARACTERISTICS:")
print(f"- Starts with 'which': {block8_text.lower().startswith('which')}")
print(f"- Starts with marker: {block8_text[0] if block8_text else 'N/A'}")
print(f"- First word: {block8_text.split()[0] if block8_text else 'N/A'}")

doc.close()
