#!/usr/bin/env python3
"""
Test script for marginalia detection using spatial segmentation.

Tests with Kant's Critique of Pure Reason to validate design.
"""

import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))

import fitz  # PyMuPDF
from marginalia_extraction import (
    analyze_page_layout,
    classify_text_blocks_by_zone
)


def analyze_kant_pdf(pdf_path: str, pages_to_check: list = [50, 100, 150]):
    """
    Analyze Kant PDF for marginalia structure.

    Args:
        pdf_path: Path to Kant PDF
        pages_to_check: List of page indices to analyze
    """
    print(f"\n{'='*70}")
    print(f"Analyzing: {Path(pdf_path).name}")
    print(f"{'='*70}\n")

    doc = fitz.open(pdf_path)

    for page_idx in pages_to_check:
        if page_idx >= len(doc):
            print(f"⚠️  Page {page_idx} exceeds document length ({len(doc)} pages)")
            continue

        print(f"\n{'─'*70}")
        print(f"PAGE {page_idx + 1} (index {page_idx})")
        print(f"{'─'*70}\n")

        page = doc[page_idx]

        # Analyze layout
        zones = analyze_page_layout(page)

        print("📐 Layout Analysis:")
        print(f"  Page size: {zones['page_width']:.1f} x {zones['page_height']:.1f}")
        print(f"  Body zone: x [{zones['body_zone']['x_start']:.1f}, {zones['body_zone']['x_end']:.1f}]")
        print(f"  Left margin: x [0, {zones['left_margin']['x_end']:.1f}]")
        print(f"  Right margin: x [{zones['right_margin']['x_start']:.1f}, {zones['page_width']:.1f}]")

        # Classify blocks
        classified = classify_text_blocks_by_zone(page, zones)

        print(f"\n📊 Text Classification:")
        print(f"  Body blocks: {len(classified['body'])}")
        print(f"  Left margin blocks: {len(classified['margin_left'])}")
        print(f"  Right margin blocks: {len(classified['margin_right'])}")

        # Show margin samples
        if classified['margin_left']:
            print(f"\n📝 Left Margin Samples (first 5):")
            for i, block in enumerate(classified['margin_left'][:5]):
                print(f"    {i+1}. \"{block['text'][:50]}\" (y={block['y']:.1f})")

        if classified['margin_right']:
            print(f"\n📝 Right Margin Samples (first 5):")
            for i, block in enumerate(classified['margin_right'][:5]):
                print(f"    {i+1}. \"{block['text'][:50]}\" (y={block['y']:.1f})")

        # Show body samples
        if classified['body']:
            print(f"\n📄 Body Text Samples (first 3):")
            for i, block in enumerate(classified['body'][:3]):
                text_preview = block['text'][:80].replace('\n', ' ')
                print(f"    {i+1}. \"{text_preview}...\" (y={block['y']:.1f})")

    doc.close()

    print(f"\n{'='*70}")
    print("Analysis complete!")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    # Test with downloaded Kant PDF
    kant_pdf = "test_downloads/KantImmanuel_CritiqueOfPureReasonTheCambridgeEditionOfTheWorksOfImmanuelKant_23371882.pdf"

    if not Path(kant_pdf).exists():
        print(f"❌ File not found: {kant_pdf}")
        print("Please download Kant's Critique first.")
        sys.exit(1)

    analyze_kant_pdf(kant_pdf, pages_to_check=[50, 100, 150, 200])
