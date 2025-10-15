#!/usr/bin/env python3
"""
Analyze the extracted pages to find and validate strikethrough instances.

User's specific locations:
- Derrida p.110: Two instances at top
- Derrida p.135: "The Outside is the Inside" with "is" crossed
- Heidegger p.79-88: Multiple erasures of Being/Sein
"""

import fitz
from pathlib import Path
import re


def analyze_for_sous_rature(pdf_path: Path):
    """Full analysis of extracted pages."""
    print(f"\n{'='*80}")
    print(f"ANALYZING: {pdf_path.name}")
    print(f"{'='*80}\n")

    doc = fitz.open(str(pdf_path))

    for page_num in range(len(doc)):
        page = doc[page_num]
        actual_page_num = page_num + 1  # This is relative to extracted PDF

        print(f"\n--- Page {actual_page_num} (from extracted PDF) ---\n")

        # Get full text
        full_text = page.get_text("text")

        # Search for OCR corruption patterns
        corruption_patterns = {
            r'\^[A-Z]©»\^': 'Being (English)',
            r'[A-Z]fcfö[sö]': 'Sein (German)',
            r'[JTjt][a-z]*tekig\^': 'Being (English)',
            r'Tßöiog\^': 'Being (English)',
            r'[A-Z][a-z]*ci\^': 'Sein (German)',
            r'[A-Za-z]+[©»^«]{2,}': 'Unknown corruption',
        }

        found_corruptions = []
        for pattern, meaning in corruption_patterns.items():
            matches = re.findall(pattern, full_text)
            if matches:
                for match in matches:
                    # Get context
                    idx = full_text.find(match)
                    context_start = max(0, idx - 80)
                    context_end = min(len(full_text), idx + len(match) + 80)
                    context = full_text[context_start:context_end]

                    found_corruptions.append({
                        'match': match,
                        'meaning': meaning,
                        'context': context
                    })

                    print(f"✅ FOUND OCR CORRUPTION: '{match}' → {meaning}")
                    print(f"   Context: ...{context}...")
                    print()

        # Search for specific text (for Derrida)
        if 'Derrida' in pdf_path.name:
            # Look for the header
            searches = [
                "Outside",
                "Inside",
                "The Outside",
                "the Inside"
            ]

            for search in searches:
                if search in full_text:
                    idx = full_text.find(search)
                    context_start = max(0, idx - 50)
                    context_end = min(len(full_text), idx + len(search) + 50)
                    context = full_text[context_start:context_end]
                    print(f"Found '{search}': ...{context}...")

        # Count total "is", "Being", "Sein" occurrences
        is_count = full_text.count(" is ")
        being_count = full_text.count("Being")
        sein_count = full_text.count("Sein")

        if is_count > 0:
            print(f"\nTotal occurrences: 'is'={is_count}, 'Being'={being_count}, 'Sein'={sein_count}")

        if not found_corruptions and 'Heidegger' in pdf_path.name:
            print("⚠️ No corruptions found on this page (unexpected for Heidegger)")

    doc.close()


if __name__ == "__main__":
    derrida = Path("test_files/derrida_pages_110_135.pdf")
    heidegger = Path("test_files/heidegger_pages_79-88.pdf")

    if derrida.exists():
        analyze_for_sous_rature(derrida)

    if heidegger.exists():
        analyze_for_sous_rature(heidegger)
