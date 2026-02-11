#!/usr/bin/env python3
"""
Debug script to inspect Kant page 3 content for asterisk footnote continuation.

Based on validation reports:
- Page 2: Asterisk footnote ends with "criticism, to"
- Page 3: Should contain continuation starting with "which everything must submit..."

This script will show ALL text blocks on page 3 to understand why continuation isn't detected.
"""

import fitz  # PyMuPDF

# Open the PDF
pdf_path = "test_files/kant_critique_pages_80_85.pdf"
doc = fitz.open(pdf_path)

# Page 3 (0-indexed: page 2)
page = doc[2]

# Get page dimensions
page_rect = page.rect
page_height = page_rect.height
footnote_threshold = page_height * 0.80  # Bottom 20%

print("=" * 80)
print("PAGE 3 (Index 2) ANALYSIS")
print("=" * 80)
print(f"Page height: {page_height}")
print(f"Footnote threshold (80%): {footnote_threshold}")
print(f"Footnote area: y > {footnote_threshold}")
print()

# Get all text blocks with positions
blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

print(f"Total blocks: {len(blocks)}")
print()

# Separate body vs footnote blocks
body_blocks = []
footnote_blocks = []

for block in blocks:
    if "lines" not in block:
        continue

    y_pos = block["bbox"][1]  # Top y-coordinate

    if y_pos < footnote_threshold:
        body_blocks.append(block)
    else:
        footnote_blocks.append(block)

print(f"Body blocks: {len(body_blocks)}")
print(f"Footnote blocks: {len(footnote_blocks)}")
print()

# Analyze footnote area blocks
print("=" * 80)
print("FOOTNOTE AREA BLOCKS (Bottom 20%)")
print("=" * 80)

for i, block in enumerate(footnote_blocks):
    print(f"\n--- Block {i + 1} ---")
    print(f"BBox: {block['bbox']}")
    print(f"Lines: {len(block.get('lines', []))}")
    print()

    # Extract all text from this block
    block_text_lines = []
    for line in block.get("lines", []):
        line_text = ""
        for span in line["spans"]:
            line_text += span["text"]
        block_text_lines.append(line_text.strip())

    full_block_text = "\n".join(block_text_lines)
    print(f"Content:\n{full_block_text}")
    print()

    # Check if this looks like continuation
    if (
        full_block_text
        and not full_block_text[0].isdigit()
        and not full_block_text[0].isalpha()
        and full_block_text[0] not in ["*", "†", "‡", "§"]
    ):
        # Might be continuation (doesn't start with marker)
        print("⚠️  POTENTIAL CONTINUATION: No obvious marker at start")
    elif full_block_text.startswith("which "):
        print("🔍 FOUND CONTINUATION: Starts with 'which'")

    # Check for marker patterns
    import re

    marker_patterns = {
        "numeric": r"^\d+[\.\s\t]",
        "letter": r"^[a-z][\.\s\t]",
        "symbol": r"^[*†‡§¶#][\.\s\t]",
    }

    for pattern_name, pattern in marker_patterns.items():
        if re.match(pattern, full_block_text):
            print(f"✅ MARKER DETECTED ({pattern_name}): {full_block_text[:50]}")

# Also check body area for reference
print()
print("=" * 80)
print("BODY AREA - LAST FEW BLOCKS (For Context)")
print("=" * 80)

# Show last 3 body blocks
for i, block in enumerate(body_blocks[-3:]):
    print(f"\n--- Body Block {len(body_blocks) - 3 + i + 1} ---")
    print(f"BBox: {block['bbox']}")

    block_text_lines = []
    for line in block.get("lines", []):
        line_text = ""
        for span in line["spans"]:
            line_text += span["text"]
        block_text_lines.append(line_text.strip())

    full_block_text = "\n".join(block_text_lines)
    # Show only last 200 chars
    if len(full_block_text) > 200:
        print(f"Content (last 200 chars):\n...{full_block_text[-200:]}")
    else:
        print(f"Content:\n{full_block_text}")

doc.close()

print()
print("=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
