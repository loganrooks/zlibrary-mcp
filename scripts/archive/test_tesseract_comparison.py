#!/usr/bin/env python3
"""
Compare PyMuPDF vs Tesseract OCR for strikethrough-corrupted text.

Tests whether Tesseract can recover text that PyMuPDF corrupts due to
strikethrough annotations.
"""

import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
from pathlib import Path
import json

def extract_with_pymupdf(pdf_path: Path) -> dict:
    """Extract text using PyMuPDF."""
    doc = fitz.open(pdf_path)
    pages = {}

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        pages[page_num + 1] = text

    doc.close()
    return pages

def extract_with_tesseract(pdf_path: Path) -> dict:
    """Extract text using Tesseract OCR."""
    # Convert PDF to images (one per page)
    images = convert_from_path(pdf_path, dpi=300)

    pages = {}
    for page_num, image in enumerate(images, start=1):
        # Run Tesseract OCR
        text = pytesseract.image_to_string(image, lang='eng')
        pages[page_num] = text

    return pages

def compare_extractions(pdf_path: Path, name: str) -> dict:
    """Compare PyMuPDF vs Tesseract for a given PDF."""
    print(f"\n{'='*80}")
    print(f"Processing: {name}")
    print(f"File: {pdf_path}")
    print(f"{'='*80}\n")

    # Extract with both methods
    pymupdf_pages = extract_with_pymupdf(pdf_path)
    tesseract_pages = extract_with_tesseract(pdf_path)

    comparison = {
        "file": str(pdf_path),
        "name": name,
        "page_count": len(pymupdf_pages),
        "pages": {}
    }

    # Compare page by page
    for page_num in pymupdf_pages.keys():
        pymupdf_text = pymupdf_pages[page_num]
        tesseract_text = tesseract_pages[page_num]

        print(f"\n--- Page {page_num} ---")
        print(f"PyMuPDF length: {len(pymupdf_text)} chars")
        print(f"Tesseract length: {len(tesseract_text)} chars")

        # Check for corruption patterns
        pymupdf_has_corruption = any([
            ")(" in pymupdf_text,
            "^B©»^" in pymupdf_text,
            "^e" in pymupdf_text,
            "^fi" in pymupdf_text,
        ])

        tesseract_has_corruption = any([
            ")(" in tesseract_text,
            "^B©»^" in tesseract_text,
            "^e" in tesseract_text,
            "^fi" in tesseract_text,
        ])

        print(f"PyMuPDF has corruption: {pymupdf_has_corruption}")
        print(f"Tesseract has corruption: {tesseract_has_corruption}")

        # Sample first 500 chars
        print(f"\nPyMuPDF sample (first 500 chars):")
        print(pymupdf_text[:500])
        print(f"\nTesseract sample (first 500 chars):")
        print(tesseract_text[:500])

        comparison["pages"][page_num] = {
            "pymupdf_length": len(pymupdf_text),
            "tesseract_length": len(tesseract_text),
            "pymupdf_has_corruption": pymupdf_has_corruption,
            "tesseract_has_corruption": tesseract_has_corruption,
            "pymupdf_text": pymupdf_text,
            "tesseract_text": tesseract_text
        }

    return comparison

def main():
    """Main comparison workflow."""
    test_files = [
        {
            "path": Path("test_files/derrida_pages_110_135.pdf"),
            "name": "Derrida (Pages 110-135)",
            "critical_pages": [2],  # Page 135 (index 2)
            "corruption_example": "is → )("
        },
        {
            "path": Path("test_files/heidegger_pages_79-88.pdf"),
            "name": "Heidegger (Pages 79-88)",
            "critical_pages": [2],  # Page 80 (index 2)
            "corruption_example": "Being → ^B©»^"
        }
    ]

    results = []

    for test_file in test_files:
        if not test_file["path"].exists():
            print(f"WARNING: File not found: {test_file['path']}")
            continue

        comparison = compare_extractions(test_file["path"], test_file["name"])
        comparison["critical_pages"] = test_file["critical_pages"]
        comparison["corruption_example"] = test_file["corruption_example"]
        results.append(comparison)

    # Generate report
    report_path = Path("test_files/tesseract_comparison_report.txt")

    with open(report_path, 'w') as f:
        f.write("="*80 + "\n")
        f.write("TESSERACT OCR vs PyMuPDF COMPARISON REPORT\n")
        f.write("Testing Strikethrough Corruption Handling\n")
        f.write("="*80 + "\n\n")

        for result in results:
            f.write(f"\n{'='*80}\n")
            f.write(f"FILE: {result['name']}\n")
            f.write(f"Path: {result['file']}\n")
            f.write(f"Expected Corruption: {result['corruption_example']}\n")
            f.write(f"Critical Pages: {result['critical_pages']}\n")
            f.write(f"{'='*80}\n\n")

            for page_num, page_data in result["pages"].items():
                f.write(f"\n--- PAGE {page_num} ---\n")
                f.write(f"PyMuPDF: {page_data['pymupdf_length']} chars, "
                       f"Corruption: {page_data['pymupdf_has_corruption']}\n")
                f.write(f"Tesseract: {page_data['tesseract_length']} chars, "
                       f"Corruption: {page_data['tesseract_has_corruption']}\n\n")

                # Check if this is a critical page
                if page_num in result["critical_pages"]:
                    f.write("⚠️  CRITICAL PAGE (Known Corruption)\n\n")

                f.write("PyMuPDF EXTRACTION (first 1000 chars):\n")
                f.write("-" * 80 + "\n")
                f.write(page_data['pymupdf_text'][:1000] + "\n")
                f.write("-" * 80 + "\n\n")

                f.write("TESSERACT EXTRACTION (first 1000 chars):\n")
                f.write("-" * 80 + "\n")
                f.write(page_data['tesseract_text'][:1000] + "\n")
                f.write("-" * 80 + "\n\n")

                # Comparison
                if page_data['pymupdf_has_corruption'] and not page_data['tesseract_has_corruption']:
                    f.write("✅ TESSERACT IMPROVEMENT: Tesseract avoided PyMuPDF corruption patterns\n\n")
                elif not page_data['pymupdf_has_corruption'] and page_data['tesseract_has_corruption']:
                    f.write("❌ TESSERACT REGRESSION: Tesseract introduced corruption\n\n")
                elif page_data['pymupdf_has_corruption'] and page_data['tesseract_has_corruption']:
                    f.write("⚠️  BOTH CORRUPTED: Both methods show corruption patterns\n\n")
                else:
                    f.write("✅ BOTH CLEAN: Neither method shows corruption patterns\n\n")

        # Summary and Recommendations
        f.write("\n" + "="*80 + "\n")
        f.write("SUMMARY AND RECOMMENDATIONS\n")
        f.write("="*80 + "\n\n")

        # Count improvements
        tesseract_better = 0
        pymupdf_better = 0
        both_corrupted = 0
        both_clean = 0

        for result in results:
            for page_num, page_data in result["pages"].items():
                if page_data['pymupdf_has_corruption'] and not page_data['tesseract_has_corruption']:
                    tesseract_better += 1
                elif not page_data['pymupdf_has_corruption'] and page_data['tesseract_has_corruption']:
                    pymupdf_better += 1
                elif page_data['pymupdf_has_corruption'] and page_data['tesseract_has_corruption']:
                    both_corrupted += 1
                else:
                    both_clean += 1

        total_pages = tesseract_better + pymupdf_better + both_corrupted + both_clean

        f.write(f"Total Pages Analyzed: {total_pages}\n\n")
        f.write(f"Tesseract Better: {tesseract_better} ({tesseract_better/total_pages*100:.1f}%)\n")
        f.write(f"PyMuPDF Better: {pymupdf_better} ({pymupdf_better/total_pages*100:.1f}%)\n")
        f.write(f"Both Corrupted: {both_corrupted} ({both_corrupted/total_pages*100:.1f}%)\n")
        f.write(f"Both Clean: {both_clean} ({both_clean/total_pages*100:.1f}%)\n\n")

        # Recommendation
        f.write("RECOMMENDATION:\n")
        if tesseract_better > pymupdf_better:
            f.write("✅ USE TESSERACT: Tesseract shows improvement over PyMuPDF for strikethrough handling.\n")
            f.write("   Consider using Tesseract OCR as fallback when strikethrough is detected.\n")
        elif tesseract_better == 0 and both_corrupted > 0:
            f.write("❌ TESSERACT DOESN'T HELP: Both methods fail similarly on strikethrough pages.\n")
            f.write("   Strikethrough corruption is likely in the PDF rendering itself, not extraction.\n")
            f.write("   Consider:\n")
            f.write("   1. Pre-processing PDFs to remove strikethrough annotations\n")
            f.write("   2. Using alternative PDF libraries (pdfplumber, camelot)\n")
            f.write("   3. Detecting and flagging corrupted pages for manual review\n")
        else:
            f.write("⚠️  MIXED RESULTS: No clear winner between PyMuPDF and Tesseract.\n")
            f.write("   May need page-by-page analysis to choose best method.\n")

    print(f"\n{'='*80}")
    print(f"Report saved to: {report_path}")
    print(f"{'='*80}\n")

    # Also save JSON for programmatic analysis
    json_path = Path("test_files/tesseract_comparison_data.json")
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"JSON data saved to: {json_path}\n")

if __name__ == "__main__":
    main()
