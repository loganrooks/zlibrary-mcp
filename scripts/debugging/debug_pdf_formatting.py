#!/usr/bin/env python3
"""
Debug script to inspect raw PyMuPDF formatting data.
"""

import fitz
from pathlib import Path

def debug_pdf_formatting(pdf_path: Path):
    """Print detailed formatting information from PDF."""
    print(f"\n{'=' * 80}")
    print(f"Debugging: {pdf_path.name}")
    print(f"{'=' * 80}")

    doc = fitz.open(pdf_path)

    for page_num, page in enumerate(doc, start=1):
        print(f"\n--- PAGE {page_num} ---")

        blocks = page.get_text("dict")["blocks"]

        for block_idx, block in enumerate(blocks):
            if block["type"] == 0:  # Text block
                print(f"\nBlock {block_idx}:")

                for line_idx, line in enumerate(block["lines"]):
                    print(f"  Line {line_idx}:")

                    for span_idx, span in enumerate(line["spans"]):
                        text = span["text"]
                        font = span["font"]
                        size = span["size"]
                        flags = span["flags"]
                        color = span.get("color", None)

                        print(f"    Span {span_idx}: '{text}'")
                        print(f"      Font: {font}")
                        print(f"      Size: {size}")
                        print(f"      Flags: {flags} (binary: {bin(flags)})")
                        print(f"      Color: {color}")

                        # Decode flags
                        flag_meanings = []
                        if flags & 2**0:
                            flag_meanings.append("superscript")
                        if flags & 2**1:
                            flag_meanings.append("italic")
                        if flags & 2**2:
                            flag_meanings.append("serifed")
                        if flags & 2**3:
                            flag_meanings.append("monospaced")
                        if flags & 2**4:
                            flag_meanings.append("bold")

                        if flag_meanings:
                            print(f"      Detected: {', '.join(flag_meanings)}")

                        # Check font name patterns
                        font_lower = font.lower()
                        name_patterns = []
                        if "bold" in font_lower:
                            name_patterns.append("bold (from name)")
                        if "italic" in font_lower or "oblique" in font_lower:
                            name_patterns.append("italic (from name)")
                        if "courier" in font_lower or "mono" in font_lower:
                            name_patterns.append("monospaced (from name)")

                        if name_patterns:
                            print(f"      From Name: {', '.join(name_patterns)}")

    doc.close()


if __name__ == "__main__":
    test_files = [
        "test_files/test_digital_formatting.pdf",
        "test_files/test_xmarks_and_strikethrough.pdf",
    ]

    for pdf_path in test_files:
        pdf_path = Path(pdf_path)
        if pdf_path.exists():
            debug_pdf_formatting(pdf_path)
        else:
            print(f"⚠️  Not found: {pdf_path}")
