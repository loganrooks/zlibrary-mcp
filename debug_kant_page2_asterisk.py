#!/usr/bin/env python3
"""
Debug script to find the asterisk footnote on Kant page 2.
Looking for content ending with "criticism, to"
"""

import fitz  # PyMuPDF
import re

# Open the PDF
pdf_path = "test_files/kant_critique_pages_80_85.pdf"
doc = fitz.open(pdf_path)

# Page 2 (0-indexed: page 1)
page = doc[1]

# Get page dimensions
page_rect = page.rect
page_height = page_rect.height
footnote_threshold = page_height * 0.80  # Bottom 20%

print(f"=" * 80)
print(f"PAGE 2 (Index 1) ANALYSIS - LOOKING FOR ASTERISK FOOTNOTE")
print(f"=" * 80)
print(f"Page height: {page_height}")
print(f"Footnote threshold (80%): {footnote_threshold}")
print()

# Get all text blocks
blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

print(f"Total blocks: {len(blocks)}")
print()

# Look for asterisk marker in body
print("=" * 80)
print("SEARCHING FOR ASTERISK (*) MARKER IN BODY TEXT")
print("=" * 80)

for i, block in enumerate(blocks):
    if "lines" not in block:
        continue

    y_pos = block["bbox"][1]  # Top y-coordinate

    # Extract all text from this block
    block_text_lines = []
    for line in block.get("lines", []):
        for span in line["spans"]:
            text = span["text"]
            # Check for asterisk
            if '*' in text:
                print(f"\n⭐ ASTERISK FOUND IN BLOCK {i+1}")
                print(f"BBox: {block['bbox']}")
                print(f"Y-position: {y_pos} ({'BODY' if y_pos < footnote_threshold else 'FOOTNOTE'} area)")
                print(f"Is superscript: {(span.get('flags', 0) & (1 << 0)) != 0}")
                print(f"Font: {span.get('font', 'unknown')}")
                print(f"Size: {span.get('size', 0)}")
                print()

                # Get context (full line)
                line_text = ""
                for s in line["spans"]:
                    line_text += s["text"]
                print(f"Line context: {line_text}")
                print()

# Look for content ending with "criticism, to" or "to" in footnote area
print("=" * 80)
print("SEARCHING FOR FOOTNOTE ENDING WITH 'to'")
print("=" * 80)

for i, block in enumerate(blocks):
    if "lines" not in block:
        continue

    y_pos = block["bbox"][1]
    if y_pos < footnote_threshold:
        continue  # Only check footnote area

    # Extract all text
    block_text_lines = []
    for line in block.get("lines", []):
        line_text = ""
        for span in line["spans"]:
            line_text += span["text"]
        block_text_lines.append(line_text.strip())

    full_block_text = " ".join(block_text_lines)

    # Check if ends with "to" or "criticism"
    if full_block_text.endswith(" to") or "criticism" in full_block_text:
        print(f"\n🔍 POTENTIAL MATCH IN BLOCK {i+1}")
        print(f"BBox: {block['bbox']}")
        print(f"Content (last 200 chars):")
        if len(full_block_text) > 200:
            print(f"...{full_block_text[-200:]}")
        else:
            print(full_block_text)
        print()

        # Check for marker at start
        marker_patterns = {
            'numeric': r'^\d+[\.\s\t]',
            'letter': r'^[a-z][\.\s\t]',
            'symbol': r'^[*†‡§¶#][\.\s\t]'
        }

        for pattern_name, pattern in marker_patterns.items():
            if re.match(pattern, full_block_text):
                print(f"✅ Marker type: {pattern_name}")
                break
        else:
            print(f"⚠️  NO MARKER at start")

doc.close()
