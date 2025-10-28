#!/usr/bin/env python3
"""
Extract pages 81-82 (1-based) from Kant's Critique of Pure Reason for multi-page footnote testing.

These are the actual pages with the asterisk footnote mentioned in session notes:
- Page 81: "Our age is the genuine age of criticism, to*"
- Page 82: "*which everything must submit..."

Note: PDF uses 0-based indexing, so page 81 = index 80, page 82 = index 81
"""

import sys
from pathlib import Path
import fitz  # PyMuPDF

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def extract_pages(source_pdf: str, output_pdf: str, pages: list):
    """
    Extract specific pages from a PDF.

    Args:
        source_pdf: Path to source PDF file
        output_pdf: Path to output PDF file
        pages: List of 0-based page indices to extract
    """
    # Open source PDF
    doc = fitz.open(source_pdf)

    # Create new PDF with selected pages
    output_doc = fitz.open()

    for page_num in pages:
        if page_num < 0 or page_num >= len(doc):
            print(f"Warning: Page {page_num} out of range (0-{len(doc)-1})")
            continue

        # Insert page into output document
        output_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
        print(f"Extracted page {page_num} (PDF page {page_num + 1})")

        # Show preview of page content
        page = doc[page_num]
        text_preview = page.get_text()[:200].replace('\n', ' ')
        print(f"  Preview: {text_preview}...")

    # Save output
    output_doc.save(output_pdf)
    output_doc.close()
    doc.close()

    print(f"\nSaved {len(pages)} pages to: {output_pdf}")

def main():
    # Paths
    source_pdf = project_root / "downloads" / "KantImmanuel_CritiqueOfPureReasonSecondEdition_119402590.pdf"
    output_pdf = project_root / "test_files" / "kant_critique_pages_64_65.pdf"

    # Page numbers (0-based index)
    # PDF page 81 = index 80, PDF page 82 = index 81
    # These correspond to the preface section pages A xi-xii / A xii-xiii
    pages_to_extract = [80, 81]  # Pages 81-82 in PDF (1-based)

    if not source_pdf.exists():
        print(f"Error: Source PDF not found: {source_pdf}")
        sys.exit(1)

    print(f"Source: {source_pdf}")
    print(f"Output: {output_pdf}")
    print(f"Extracting PDF pages: {[p+1 for p in pages_to_extract]} (0-based: {pages_to_extract})\n")

    extract_pages(str(source_pdf), str(output_pdf), pages_to_extract)

    # Verify output
    if output_pdf.exists():
        verify_doc = fitz.open(str(output_pdf))
        print(f"\nVerification:")
        print(f"  Pages in output: {len(verify_doc)}")
        print(f"  File size: {output_pdf.stat().st_size / 1024:.1f} KB")

        # Check for asterisk
        for i in range(len(verify_doc)):
            page = verify_doc[i]
            text = page.get_text()
            asterisk_count = text.count('*')
            print(f"  Page {i}: {asterisk_count} asterisk(s) found")

        verify_doc.close()

if __name__ == "__main__":
    main()
