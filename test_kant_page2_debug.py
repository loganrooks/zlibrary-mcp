#!/usr/bin/env python3
"""Debug script to check Page 2 footnote detection in detail."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import fitz
from lib.rag_processing import _detect_footnotes_in_page

# Open Kant PDF
doc = fitz.open('test_files/kant_critique_pages_80_85.pdf')

# Check page 2 (index 1)
page = doc[1]
page_num = 1

print("="*70)
print(f"DEBUGGING KANT PAGE 2 (Index {page_num})")
print("="*70)

# Get footnote detection results
footnotes = _detect_footnotes_in_page(page, page_num)

print(f"\nMarkers found: {len(footnotes.get('markers', []))}")
for marker in footnotes.get('markers', []):
    print(f"  - {marker}")

print(f"\nDefinitions found: {len(footnotes.get('definitions', []))}")
for defn in footnotes.get('definitions', []):
    marker = defn.get('marker', '?')
    content = defn.get('content', '')
    print(f"\n  Marker '{marker}':")
    print(f"    Content: {content[:200]}...")
    print(f"    Full length: {len(content)} chars")

# Also get all text blocks to see what's on the page
print("\n" + "="*70)
print("ALL TEXT BLOCKS ON PAGE (for reference)")
print("="*70)

blocks = page.get_text("dict")["blocks"]
page_height = page.rect.height
footnote_threshold = page_height * 0.75

print(f"Page height: {page_height}")
print(f"Footnote threshold (75%): {footnote_threshold}")

for i, block in enumerate(blocks):
    if "lines" not in block:
        continue

    y_pos = block["bbox"][1]
    text = ""
    for line in block.get("lines", []):
        for span in line["spans"]:
            text += span["text"] + " "

    is_footnote_area = y_pos >= footnote_threshold
    print(f"\nBlock {i}: y={y_pos:.1f} {'[FOOTNOTE AREA]' if is_footnote_area else '[BODY]'}")
    print(f"  Text: {text[:150]}...")

doc.close()
