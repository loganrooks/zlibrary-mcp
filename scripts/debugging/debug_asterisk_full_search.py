#!/usr/bin/env python3
"""
Comprehensive search for asterisk footnote across all pages.
Looking for content ending with "to" that might continue.
"""

import fitz  # PyMuPDF

# Open the PDF
pdf_path = "test_files/kant_critique_pages_80_85.pdf"
doc = fitz.open(pdf_path)

print("=" * 80)
print("COMPREHENSIVE ASTERISK FOOTNOTE SEARCH")
print("=" * 80)
print()

for page_idx in range(len(doc)):
    page = doc[page_idx]
    page_height = page.rect.height
    footnote_threshold = page_height * 0.80

    print(f"--- PAGE {page_idx + 1} (Index {page_idx}) ---")

    # Get all text blocks
    blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

    # Look for asterisk content in footnote area
    for block in blocks:
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

        # Check if starts with asterisk or ends with "to"
        if (
            full_block_text.startswith("*")
            or full_block_text.endswith(" to")
            or "criticism" in full_block_text.lower()
        ):
            print("\n🔍 POTENTIAL FOOTNOTE:")
            print(f"BBox: {block['bbox']}")
            print(f"Starts with asterisk: {full_block_text.startswith('*')}")
            print(f"Ends with 'to': {full_block_text.endswith(' to')}")
            print(f"Contains 'criticism': {'criticism' in full_block_text.lower()}")
            print(f"\nFull content ({len(full_block_text)} chars):")
            print(full_block_text)
            print()

print()
print("=" * 80)
print("SEARCHING FOR CONTINUATION TEXT")
print("=" * 80)
print()

for page_idx in range(len(doc)):
    page = doc[page_idx]
    page_height = page.rect.height
    footnote_threshold = page_height * 0.80

    print(f"--- PAGE {page_idx + 1} (Index {page_idx}) ---")

    blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

    for block in blocks:
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

        # Look for continuation markers
        if full_block_text.startswith("which ") or full_block_text.startswith(
            "everything"
        ):
            print("\n🔍 POTENTIAL CONTINUATION:")
            print(f"BBox: {block['bbox']}")
            print(f"Content ({len(full_block_text)} chars):")
            print(full_block_text[:200] + ("..." if len(full_block_text) > 200 else ""))
            print()

doc.close()

print()
print("=" * 80)
print("SEARCH COMPLETE")
print("=" * 80)
