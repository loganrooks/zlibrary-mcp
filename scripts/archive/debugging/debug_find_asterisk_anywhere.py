#!/usr/bin/env python3
"""
Find ALL text containing "criticism" or starting with asterisk anywhere on all pages.
"""

import fitz  # PyMuPDF

# Open the PDF
pdf_path = "test_files/kant_critique_pages_80_85.pdf"
doc = fitz.open(pdf_path)

print("=" * 80)
print("FINDING ALL TEXT WITH 'criticism' OR ASTERISK")
print("=" * 80)
print()

for page_idx in range(len(doc)):
    page = doc[page_idx]
    page_height = page.rect.height
    footnote_threshold = page_height * 0.80

    print(f"{'=' * 80}")
    print(f"PAGE {page_idx + 1} (Index {page_idx})")
    print(f"{'=' * 80}")
    print()

    blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

    for block_idx, block in enumerate(blocks):
        if "lines" not in block:
            continue

        y_pos = block["bbox"][1]
        location = "FOOTNOTE" if y_pos >= footnote_threshold else "BODY"

        # Extract all text
        block_text_lines = []
        for line in block.get("lines", []):
            line_text = ""
            for span in line["spans"]:
                line_text += span["text"]
            block_text_lines.append(line_text.strip())

        full_block_text = " ".join(block_text_lines)

        # Check for criteria
        has_criticism = "criticism" in full_block_text.lower()
        has_asterisk = "*" in full_block_text
        starts_with_asterisk = full_block_text.strip().startswith("*")

        if has_criticism or has_asterisk or starts_with_asterisk:
            print(f"Block {block_idx + 1} [{location}]")
            print(f"BBox: {block['bbox']}")
            print(
                f"Has '*': {has_asterisk}, Starts with '*': {starts_with_asterisk}, Has 'criticism': {has_criticism}"
            )
            print(f"\nContent ({len(full_block_text)} chars):")

            # Show context around "criticism" or asterisk
            if len(full_block_text) > 300:
                # Find position of keyword
                if has_criticism:
                    pos = full_block_text.lower().find("criticism")
                    start = max(0, pos - 150)
                    end = min(len(full_block_text), pos + 150)
                    print(f"...{full_block_text[start:end]}...")
                elif has_asterisk:
                    pos = full_block_text.find("*")
                    start = max(0, pos - 150)
                    end = min(len(full_block_text), pos + 150)
                    print(f"...{full_block_text[start:end]}...")
            else:
                print(full_block_text)

            print()
            print("-" * 80)
            print()

doc.close()
