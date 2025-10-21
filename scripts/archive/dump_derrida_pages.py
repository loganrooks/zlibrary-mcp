#!/usr/bin/env python3
"""Dump full text of Derrida pages to see what's actually there."""

import fitz


doc = fitz.open("test_files/derrida_pages_110_135.pdf")

for i, page in enumerate(doc):
    print(f"\n{'='*80}")
    print(f"PAGE {i+1} (Original PDF page {[110, 135][i]})")
    print(f"{'='*80}\n")

    text = page.get_text("text")
    print(text)
    print(f"\n{'='*80}\n")

doc.close()
