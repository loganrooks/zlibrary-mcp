#!/usr/bin/env python3
"""
Search page 3 for continuation text starting with "which" or containing "submit".
"""

import fitz  # PyMuPDF

# Open the PDF
pdf_path = "test_files/kant_critique_pages_80_85.pdf"
doc = fitz.open(pdf_path)

page = doc[2]  # Page 3 (0-indexed)
page_height = page.rect.height
footnote_threshold = page_height * 0.80

blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

print("=" * 80)
print("PAGE 3 - SEARCHING FOR CONTINUATION")
print("=" * 80)
print(f"Page height: {page_height}")
print(f"Footnote threshold (80%): {footnote_threshold}")
print()

for idx, block in enumerate(blocks):
    if "lines" not in block:
        continue

    y_pos = block["bbox"][1]
    location = "FOOTNOTE" if y_pos >= footnote_threshold else "BODY"

    # Extract all text
    block_lines = []
    for line in block.get("lines", []):
        line_text = ""
        for span in line["spans"]:
            line_text += span["text"]
        block_lines.append(line_text.strip())

    block_text = " ".join(block_lines)

    # Look for "which" or "submit"
    if "which" in block_text.lower() or "submit" in block_text.lower():
        print(f"BLOCK {idx + 1} [{location}]:")
        print(f"BBox: {block['bbox']}")
        print(f"Y-position: {y_pos}")
        print()
        print(f"Content ({len(block_text)} chars):")

        # Show context around keyword
        if len(block_text) > 300:
            if "which" in block_text.lower():
                pos = block_text.lower().find("which")
                start = max(0, pos - 100)
                end = min(len(block_text), pos + 200)
                print(f"...{block_text[start:end]}...")
            elif "submit" in block_text.lower():
                pos = block_text.lower().find("submit")
                start = max(0, pos - 100)
                end = min(len(block_text), pos + 200)
                print(f"...{block_text[start:end]}...")
        else:
            print(block_text)

        print()
        print("-" * 80)
        print()

doc.close()
