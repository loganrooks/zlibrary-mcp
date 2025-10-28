#!/usr/bin/env python3
"""
Find the actual location of Kant preface pages 64-65 mentioned in session notes.

Session notes mention: "Our age is the genuine age of criticism, to" on page 64,
continuing with "which everything must submit" on page 65.
"""

import sys
from pathlib import Path
import fitz  # PyMuPDF
import re

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def search_for_text(pdf_path: str, search_text: str, context_chars: int = 100):
    """
    Search for specific text in PDF and show which page it's on.

    Args:
        pdf_path: Path to PDF file
        search_text: Text to search for
        context_chars: Number of characters of context to show

    Returns:
        List of (page_num, context) tuples
    """
    doc = fitz.open(pdf_path)
    results = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()

        # Search for text (case-insensitive)
        if search_text.lower() in text.lower():
            # Find position and extract context
            pos = text.lower().find(search_text.lower())
            start = max(0, pos - context_chars)
            end = min(len(text), pos + len(search_text) + context_chars)
            context = text[start:end].replace('\n', ' ')

            results.append((page_num, context))
            print(f"\n{'='*80}")
            print(f"Found on PDF page {page_num} (0-based) = page {page_num + 1} (1-based)")
            print(f"{'='*80}")
            print(f"Context: ...{context}...")

    doc.close()
    return results

def main():
    source_pdf = project_root / "downloads" / "KantImmanuel_CritiqueOfPureReasonSecondEdition_119402590.pdf"

    if not source_pdf.exists():
        print(f"Error: Source PDF not found: {source_pdf}")
        sys.exit(1)

    print(f"Searching in: {source_pdf}\n")

    # Search for the specific text mentioned in session notes
    search_phrases = [
        "Our age is the genuine age of criticism",
        "age of criticism, to which everything must submit",
        "which everything must submit"
    ]

    all_results = []
    for phrase in search_phrases:
        print(f"\n{'#'*80}")
        print(f"Searching for: '{phrase}'")
        print(f"{'#'*80}")
        results = search_for_text(str(source_pdf), phrase, context_chars=200)
        all_results.extend(results)

        if not results:
            print(f"  ❌ Not found")

    # Also search for asterisk footnotes in the range
    print(f"\n\n{'#'*80}")
    print(f"Searching for asterisk markers in pages 60-70")
    print(f"{'#'*80}")

    doc = fitz.open(str(source_pdf))
    for page_num in range(59, 70):  # Pages 60-70 (0-based 59-69)
        if page_num >= len(doc):
            break

        page = doc[page_num]
        text = page.get_text()

        # Look for asterisk in footer or footnote area
        if '*' in text:
            # Count asterisks
            count = text.count('*')
            print(f"\nPage {page_num + 1} (0-based {page_num}): {count} asterisk(s)")

            # Show lines with asterisks
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if '*' in line:
                    print(f"  Line {i}: {line.strip()[:100]}")

    doc.close()

if __name__ == "__main__":
    main()
