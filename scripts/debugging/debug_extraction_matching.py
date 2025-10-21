#!/usr/bin/env python3
"""Debug the extraction matching logic."""

import json
import fitz
from pathlib import Path

def extract_with_pymupdf_native(pdf_path: Path):
    """Extract formatting using PyMuPDF's native capabilities."""
    doc = fitz.open(pdf_path)
    results = {}

    for page_num, page in enumerate(doc, start=1):
        page_results = []

        # Get text with format information
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if block["type"] == 0:  # Text block
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if not text:
                            continue

                        formats = []
                        font_name = span["font"].lower()
                        flags = span["flags"]

                        # Font-based detection
                        if "bold" in font_name or (flags & 16):  # Bold flag (bit 4)
                            formats.append("bold")
                        if "italic" in font_name or "oblique" in font_name or (flags & 2):  # Italic flag (bit 1)
                            formats.append("italic")
                        if "courier" in font_name or "mono" in font_name or (flags & 8):  # Monospaced flag (bit 3)
                            formats.append("monospaced")

                        # Superscript detection (flag bit 0)
                        if flags & 1:
                            formats.append("superscript")

                        # Subscript detection by size and position
                        if span["size"] < 10 and len(text) <= 3 and not (flags & 1):
                            formats.append("subscript")

                        page_results.append({
                            "text": text,
                            "formatting": formats,
                            "bbox": span["bbox"],
                            "y_position": span["origin"][1],
                            "font": span["font"],
                            "flags": flags
                        })

        results[f"page_{page_num}"] = page_results

    doc.close()
    return results


# Test
pdf_path = Path("test_files/test_digital_formatting.pdf")
if pdf_path.exists():
    print("Extracted data:")
    extracted = extract_with_pymupdf_native(pdf_path)

    for page, items in extracted.items():
        print(f"\n{page}:")
        for item in items:
            print(f"  '{item['text']}' - formats: {item['formatting']}, y: {item['y_position']:.1f}, font: {item['font']}, flags: {item['flags']}")

    # Now show ground truth
    print("\n\nGround truth:")
    with open("test_files/test_formatting_ground_truth.json") as f:
        gt = json.load(f)

    for pdf_name, pdf_data in gt.items():
        if "digital_formatting" in pdf_name:
            for page, items in pdf_data.items():
                print(f"\n{page}:")
                for item in items:
                    print(f"  '{item['text']}' - formats: {item['formatting']}, y_approx: {item.get('y_approx', 'N/A')}")
