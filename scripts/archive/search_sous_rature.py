#!/usr/bin/env python3
"""
Search for specific phrases with sous rature in Derrida and Heidegger PDFs.

Targets:
- Derrida: "The Outside is the Inside" (should have "is" crossed out)
- Heidegger: Look for garbled text patterns indicating OCR'd X marks
"""

import fitz
from pathlib import Path
import re


def search_phrase_in_pdf(pdf_path: Path, search_phrase: str, context_chars: int = 200):
    """
    Search for a phrase in PDF and show context.

    Args:
        pdf_path: Path to PDF
        search_phrase: Phrase to search for
        context_chars: Characters of context before/after
    """
    print(f"\n{'='*80}")
    print(f"Searching '{search_phrase}' in {pdf_path.name}")
    print(f"{'='*80}\n")

    doc = fitz.open(str(pdf_path))
    found_instances = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")

        # Case-insensitive search
        if search_phrase.lower() in text.lower():
            # Find all occurrences
            text_lower = text.lower()
            phrase_lower = search_phrase.lower()

            idx = 0
            while True:
                idx = text_lower.find(phrase_lower, idx)
                if idx == -1:
                    break

                # Get context
                start = max(0, idx - context_chars)
                end = min(len(text), idx + len(search_phrase) + context_chars)
                context = text[start:end]

                # Get the actual text (with original case)
                actual_phrase = text[idx:idx + len(search_phrase)]

                print(f"Page {page_num + 1} (PDF page {page_num + 1}):")
                print(f"  Found: '{actual_phrase}'")
                print(f"  Context:\n{context}\n")

                # Check block/span structure around this text
                blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT).get("blocks", [])

                for block in blocks:
                    if block.get('type') != 0:
                        continue

                    block_text = ""
                    for line in block.get('lines', []):
                        line_text = ""
                        for span in line.get('spans', []):
                            line_text += span.get('text', '')
                        block_text += line_text

                    if search_phrase.lower() in block_text.lower():
                        print(f"  Block bbox: {block.get('bbox', 'unknown')}")

                        # Check all spans in this block
                        for line in block.get('lines', []):
                            for span in line.get('spans', []):
                                span_text = span.get('text', '')
                                # If this span contains any word from the phrase
                                for word in search_phrase.split():
                                    if word.lower() in span_text.lower():
                                        print(f"    Span: '{span_text}' | flags={span.get('flags', 0)} | font={span.get('font', 'unknown')}")
                        break

                found_instances.append({
                    "page": page_num + 1,
                    "phrase": actual_phrase,
                    "context": context
                })

                idx += len(search_phrase)

    doc.close()

    if not found_instances:
        print(f"  ❌ Phrase not found in entire document")

    return found_instances


def detect_ocr_corruption(pdf_path: Path, sample_pages: list = None):
    """
    Detect garbled text patterns that might indicate OCR'd strikethrough.

    Patterns:
    - ^X©»^ style (X = any letter)
    - Multiple special chars together
    - Mixture of letters and special chars
    """
    print(f"\n{'='*80}")
    print(f"OCR Corruption Detection: {pdf_path.name}")
    print(f"{'='*80}\n")

    doc = fitz.open(str(pdf_path))

    # Corruption patterns
    patterns = [
        (r'\^[A-Z]©»\^', "X-mark pattern (^X©»^)"),
        (r'[A-Z][a-z]*fö[sö]', "Umlaut corruption (Xfös)"),
        (r'[a-z]{3,}[A-Z]{2,}', "Mixed case corruption"),
        (r'[^\w\s]{4,}', "4+ special chars"),
        (r'[A-Za-z]+[©»^«]{1,}', "Letters with special symbols"),
    ]

    pages_to_check = sample_pages if sample_pages else range(len(doc))
    corruptions_found = []

    for page_num in pages_to_check:
        if page_num >= len(doc):
            continue

        page = doc[page_num]
        text = page.get_text("text")

        for pattern, description in patterns:
            matches = re.findall(pattern, text)
            if matches:
                print(f"Page {page_num + 1}: {description}")
                for match in matches[:5]:  # First 5 matches
                    # Get context
                    idx = text.find(match)
                    context_start = max(0, idx - 30)
                    context_end = min(len(text), idx + len(match) + 30)
                    context = text[context_start:context_end]

                    print(f"  Match: '{match}'")
                    print(f"  Context: ...{context}...")

                    corruptions_found.append({
                        "page": page_num + 1,
                        "pattern": description,
                        "match": match,
                        "context": context
                    })
                print()

    doc.close()
    return corruptions_found


def main():
    """Main analysis."""

    derrida_pdf = Path("test_files/DerridaJacques_OfGrammatology_1268316.pdf")
    heidegger_pdf = Path("test_files/HeideggerMartin_TheQuestionOfBeing_964793.pdf")

    # Search for specific phrases
    print("PHRASE SEARCH")
    print("=" * 80)

    if derrida_pdf.exists():
        search_phrase_in_pdf(derrida_pdf, "The Outside is the Inside")
        search_phrase_in_pdf(derrida_pdf, "Outside is Inside")  # Try without "the"

    # OCR corruption detection
    print("\n\nOCR CORRUPTION DETECTION")
    print("=" * 80)

    if heidegger_pdf.exists():
        # Check the specific pages user mentioned
        heidegger_pages = [78, 79, 84, 85, 86, 87]  # 0-indexed
        corruptions = detect_ocr_corruption(heidegger_pdf, heidegger_pages)

        print(f"\nTotal corruptions found: {len(corruptions)}")

    if derrida_pdf.exists():
        # Check Derrida pages
        derrida_pages = [109, 134]  # 0-indexed
        corruptions = detect_ocr_corruption(derrida_pdf, derrida_pages)

        print(f"\nTotal corruptions found: {len(corruptions)}")


if __name__ == "__main__":
    main()
