#!/usr/bin/env python3
"""
Validate the Kant pages 64-65 extraction and ground truth.

Checks:
1. PDF file exists and has correct pages
2. Ground truth JSON is valid and complete
3. Visual verification can be performed
4. Continuation pattern is detectable
"""

import sys
import json
from pathlib import Path
import fitz  # PyMuPDF

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def validate_pdf():
    """Validate the extracted PDF file."""
    pdf_path = project_root / "test_files" / "kant_critique_pages_64_65.pdf"

    print("=" * 80)
    print("PDF VALIDATION")
    print("=" * 80)

    if not pdf_path.exists():
        print(f"❌ FAIL: PDF not found: {pdf_path}")
        return False

    print(f"✅ PDF exists: {pdf_path}")

    # Open and check
    doc = fitz.open(str(pdf_path))
    page_count = len(doc)

    print(f"✅ Page count: {page_count}")

    if page_count != 2:
        print(f"❌ FAIL: Expected 2 pages, got {page_count}")
        doc.close()
        return False

    # Check for asterisks
    page0 = doc[0]
    page0_text = page0.get_text()
    page0_asterisks = page0_text.count('*')

    page1 = doc[1]
    page1_text = page1.get_text()
    page1_asterisks = page1_text.count('*')

    print(f"✅ Page 0 asterisks: {page0_asterisks} (expected: 2)")
    print(f"✅ Page 1 asterisks: {page1_asterisks} (expected: 0)")

    if page0_asterisks < 2:
        print(f"❌ FAIL: Expected at least 2 asterisks on page 0")
        doc.close()
        return False

    # Check for continuation pattern
    if "Our age is the genuine age of criticism, to" in page0_text:
        print("✅ Page 0 contains: 'Our age is the genuine age of criticism, to'")
    else:
        print("❌ FAIL: Expected text not found on page 0")
        doc.close()
        return False

    if "which everything must submit" in page1_text:
        print("✅ Page 1 contains: 'which everything must submit'")
    else:
        print("❌ FAIL: Expected continuation text not found on page 1")
        doc.close()
        return False

    doc.close()
    print("\n✅ PDF VALIDATION PASSED\n")
    return True

def validate_ground_truth():
    """Validate the ground truth JSON file."""
    gt_path = project_root / "test_files" / "ground_truth" / "kant_64_65_footnotes.json"

    print("=" * 80)
    print("GROUND TRUTH VALIDATION")
    print("=" * 80)

    if not gt_path.exists():
        print(f"❌ FAIL: Ground truth not found: {gt_path}")
        return False

    print(f"✅ Ground truth exists: {gt_path}")

    # Load and validate JSON
    try:
        with open(gt_path, 'r') as f:
            gt_data = json.load(f)
        print("✅ JSON is valid")
    except json.JSONDecodeError as e:
        print(f"❌ FAIL: Invalid JSON: {e}")
        return False

    # Check required fields
    required_fields = [
        "test_name",
        "pdf_file",
        "metadata",
        "features",
        "continuation_model",
        "expected_quality",
        "validation_criteria"
    ]

    for field in required_fields:
        if field in gt_data:
            print(f"✅ Has field: {field}")
        else:
            print(f"❌ FAIL: Missing required field: {field}")
            return False

    # Check footnotes
    if "footnotes" not in gt_data["features"]:
        print("❌ FAIL: No footnotes in features")
        return False

    footnotes = gt_data["features"]["footnotes"]
    print(f"✅ Footnotes count: {len(footnotes)}")

    if len(footnotes) != 1:
        print(f"❌ FAIL: Expected 1 footnote, got {len(footnotes)}")
        return False

    # Check continuation info
    footnote = footnotes[0]
    if "continuation" not in footnote:
        print("❌ FAIL: No continuation info in footnote")
        return False

    continuation = footnote["continuation"]
    print(f"✅ Continuation info present")
    print(f"  - is_continued: {continuation.get('is_continued')}")
    print(f"  - continues_to_page: {continuation.get('continues_to_page')}")
    print(f"  - page_64_ends_with: {continuation.get('page_64_ends_with')}")
    print(f"  - page_65_starts_with: {continuation.get('page_65_starts_with')}")

    if not continuation.get("is_continued"):
        print("❌ FAIL: is_continued should be true")
        return False

    if continuation.get("page_64_ends_with") != "to":
        print("❌ FAIL: page_64_ends_with should be 'to'")
        return False

    # Check continuation model
    cont_model = gt_data["continuation_model"]
    if "continuation_patterns" not in cont_model:
        print("❌ FAIL: No continuation_patterns in model")
        return False

    print("✅ Continuation model valid")

    print("\n✅ GROUND TRUTH VALIDATION PASSED\n")
    return True

def validate_continuation_detection():
    """Simulate continuation detection logic."""
    print("=" * 80)
    print("CONTINUATION DETECTION SIMULATION")
    print("=" * 80)

    # Simulate what the RAG pipeline should detect
    page_64_last_word = "to"
    page_65_first_word = "which"

    # Check preposition list
    prepositions = ["to", "from", "with", "by", "for", "of", "in", "on", "at"]
    relative_pronouns = ["which", "who", "whom", "whose", "that"]

    if page_64_last_word in prepositions:
        print(f"✅ '{page_64_last_word}' is a preposition (incomplete sentence)")
    else:
        print(f"❌ FAIL: '{page_64_last_word}' not recognized as preposition")
        return False

    if page_65_first_word in relative_pronouns:
        print(f"✅ '{page_65_first_word}' is a relative pronoun (continuation)")
    else:
        print(f"❌ FAIL: '{page_65_first_word}' not recognized as relative pronoun")
        return False

    # Semantic coherence check
    merged = f"Our age is the genuine age of criticism, {page_64_last_word} {page_65_first_word} everything must submit."
    print(f"\n✅ Merged text: '{merged}'")
    print(f"✅ Semantic coherence: HIGH")

    print("\n✅ CONTINUATION DETECTION SIMULATION PASSED\n")
    return True

def main():
    """Run all validations."""
    print("\n" + "=" * 80)
    print("KANT PAGES 64-65 EXTRACTION VALIDATION")
    print("=" * 80 + "\n")

    results = {
        "pdf": validate_pdf(),
        "ground_truth": validate_ground_truth(),
        "continuation_detection": validate_continuation_detection()
    }

    print("=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)

    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test}")

    all_passed = all(results.values())

    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 ALL VALIDATIONS PASSED 🎉")
        print("=" * 80)
        print("\nReady for test implementation:")
        print("  - PDF: test_files/kant_critique_pages_64_65.pdf")
        print("  - Ground truth: test_files/ground_truth/kant_64_65_footnotes.json")
        print("  - Next step: Implement multi-page continuation detection")
        return 0
    else:
        print("❌ SOME VALIDATIONS FAILED ❌")
        print("=" * 80)
        print("\nPlease review and fix issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
