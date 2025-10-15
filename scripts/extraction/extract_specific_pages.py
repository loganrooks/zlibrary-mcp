#!/usr/bin/env python3
"""Extract specific pages from PDFs for detailed analysis."""

import fitz
from pathlib import Path


def extract_pages(input_pdf: Path, output_pdf: Path, pages: list):
    """
    Extract specific pages from PDF.

    Args:
        input_pdf: Source PDF path
        output_pdf: Output PDF path
        pages: List of page numbers (1-indexed)
    """
    src = fitz.open(str(input_pdf))
    dst = fitz.open()

    for page_num in pages:
        # Convert to 0-indexed
        dst.insert_pdf(src, from_page=page_num-1, to_page=page_num-1)

    dst.save(str(output_pdf))
    dst.close()
    src.close()

    print(f"✅ Extracted {len(pages)} pages from {input_pdf.name}")
    print(f"   Saved to: {output_pdf}")


def main():
    # Derrida pages
    derrida_src = Path("test_files/DerridaJacques_OfGrammatology_1268316.pdf")
    derrida_dst = Path("test_files/derrida_pages_110_135.pdf")
    extract_pages(derrida_src, derrida_dst, [110, 135])

    # Heidegger pages
    heidegger_src = Path("test_files/HeideggerMartin_TheQuestionOfBeing_964793.pdf")
    heidegger_dst = Path("test_files/heidegger_pages_79-88.pdf")
    extract_pages(heidegger_src, heidegger_dst, [79, 80, 85, 86, 87, 88])


if __name__ == "__main__":
    main()
