#!/usr/bin/env python3
"""
Analyze the asterisk footnote on Kant pages 64-65 for ground truth creation.

Visual verification shows:
- Page 64: Asterisk after "power of judgment,*"
- Page 64 footer: Footnote begins
- Page 65 footer: Footnote continues with "which everything must submit."
"""

import sys
from pathlib import Path
import fitz  # PyMuPDF
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def extract_footnote_details(pdf_path: str):
    """
    Extract detailed information about the asterisk footnote.

    Returns dict with:
    - marker location
    - footnote text on each page
    - continuation information
    """
    doc = fitz.open(pdf_path)

    results = {
        "source": "Kant - Critique of Pure Reason (Second Edition)",
        "pdf_pages": [64, 65],
        "pages_analyzed": []
    }

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()

        page_info = {
            "page_num": page_num,
            "pdf_page_number": 64 + page_num,
            "asterisk_count": text.count('*'),
            "text_preview": text[:500],
            "text_full": text
        }

        # Find asterisk positions
        lines = text.split('\n')
        asterisk_lines = []
        for i, line in enumerate(lines):
            if '*' in line:
                asterisk_lines.append({
                    "line_num": i,
                    "line_text": line.strip()
                })

        page_info["asterisk_lines"] = asterisk_lines
        results["pages_analyzed"].append(page_info)

    doc.close()
    return results

def main():
    pdf_path = project_root / "test_files" / "kant_critique_pages_64_65.pdf"

    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        sys.exit(1)

    print(f"Analyzing: {pdf_path}\n")

    results = extract_footnote_details(str(pdf_path))

    # Print summary
    print("=" * 80)
    print("VISUAL VERIFICATION SUMMARY")
    print("=" * 80)

    for page_info in results["pages_analyzed"]:
        print(f"\nPage {page_info['page_num']} (PDF page {page_info['pdf_page_number']}):")
        print(f"  Asterisks found: {page_info['asterisk_count']}")
        print(f"  Lines with asterisks: {len(page_info['asterisk_lines'])}")

        for ast_line in page_info['asterisk_lines']:
            print(f"    Line {ast_line['line_num']}: {ast_line['line_text'][:100]}")

    # Extract footnote content from page 64 (page 0)
    print("\n" + "=" * 80)
    print("FOOTNOTE CONTENT EXTRACTION")
    print("=" * 80)

    page0_text = results["pages_analyzed"][0]["text_full"]
    page1_text = results["pages_analyzed"][1]["text_full"]

    # Find where the footnote starts (after the asterisk marker in footer)
    # Visual inspection shows footnote starts with "Now and again one hears complaints"
    footnote_start_marker = "Now and again one hears complaints"

    if footnote_start_marker in page0_text:
        # Extract from this marker to end of page
        start_idx = page0_text.find(footnote_start_marker)
        page0_footnote = page0_text[start_idx:].strip()

        print(f"\nPage 64 footnote content (starts at char {start_idx}):")
        print("-" * 80)
        print(page0_footnote)
        print("-" * 80)

        # Check if it ends with "to" (continuation indicator)
        if page0_footnote.rstrip().endswith("to"):
            print("\n✅ Page 64 footnote ends with 'to' - CONTINUATION CONFIRMED")

    # Find continuation on page 65
    continuation_marker = "which everything must submit"

    if continuation_marker in page1_text:
        # Extract continuation
        start_idx = page1_text.find(continuation_marker)
        # Get some context
        end_idx = page1_text.find("examination.", start_idx) + len("examination.")
        page1_footnote = page1_text[start_idx:end_idx].strip()

        print(f"\nPage 65 footnote continuation (starts at char {start_idx}):")
        print("-" * 80)
        print(page1_footnote)
        print("-" * 80)
        print("\n✅ Page 65 contains footnote continuation")

    # Save detailed results
    output_file = project_root / "test_files" / "kant_asterisk_footnote_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n\nDetailed results saved to: {output_file}")

if __name__ == "__main__":
    main()
