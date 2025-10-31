#!/usr/bin/env python3
"""
Multi-Corpus Validation Script
Validates footnote processing across Derrida, Kant, and Heidegger corpora
"""

import sys
import json
import time
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from rag_processing import process_pdf


def load_ground_truth(filename):
    """Load ground truth JSON file"""
    path = Path("test_files/ground_truth") / filename
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def validate_corpus(pdf_path, corpus_name, expected_footnotes, ground_truth_file=None):
    """Validate a single corpus PDF"""
    print(f"\n{'='*80}")
    print(f"VALIDATING: {corpus_name}")
    print(f"PDF: {pdf_path}")
    print(f"{'='*80}")

    # Load ground truth if available
    ground_truth = None
    if ground_truth_file:
        ground_truth = load_ground_truth(ground_truth_file)
        if ground_truth:
            print(f"Ground truth loaded: {ground_truth_file}")

    # Time the processing
    start = time.perf_counter()
    result = process_pdf(pdf_path, output_format="markdown", detect_footnotes=True)
    end = time.perf_counter()

    duration_ms = (end - start) * 1000

    # Extract footnotes from result
    footnotes = []
    if "## Footnotes" in result:
        # Count markdown footnotes
        lines = result.split('\n')
        for line in lines:
            if line.startswith('[^'):
                footnotes.append(line)

    detected_count = len(footnotes)

    # Performance metrics
    import fitz  # PyMuPDF
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    doc.close()
    ms_per_page = duration_ms / page_count if page_count > 0 else 0

    # Validation results
    print(f"\n📊 RESULTS:")
    print(f"  Expected footnotes: {expected_footnotes}")
    print(f"  Detected footnotes: {detected_count}")
    print(f"  Match: {'✓' if detected_count == expected_footnotes else '✗'}")
    print(f"\n⏱️  PERFORMANCE:")
    print(f"  Total time: {duration_ms:.2f}ms")
    print(f"  Pages: {page_count}")
    print(f"  Time per page: {ms_per_page:.2f}ms")
    print(f"  Budget: <60ms per page")
    print(f"  Status: {'✓ PASS' if ms_per_page < 60 else '✗ FAIL'}")

    # Ground truth comparison
    if ground_truth:
        print(f"\n🎯 GROUND TRUTH VALIDATION:")
        if "footnotes" in ground_truth:
            gt_count = len(ground_truth["footnotes"])
            print(f"  Ground truth count: {gt_count}")
            print(f"  Match: {'✓' if detected_count == gt_count else '✗'}")

            # Check individual footnotes
            for gt_fn in ground_truth["footnotes"]:
                marker = gt_fn.get("marker", "?")
                found = any(f"[^{marker}]:" in fn for fn in footnotes)
                print(f"  Marker '{marker}': {'✓' if found else '✗'}")

    # Show detected footnotes (first 3 for brevity)
    print(f"\n📝 DETECTED FOOTNOTES (showing first 3):")
    for i, fn in enumerate(footnotes[:3]):
        preview = fn[:100] + "..." if len(fn) > 100 else fn
        print(f"  {i+1}. {preview}")

    if len(footnotes) > 3:
        print(f"  ... and {len(footnotes) - 3} more")

    return {
        "corpus": corpus_name,
        "expected": expected_footnotes,
        "detected": detected_count,
        "match": detected_count == expected_footnotes,
        "duration_ms": duration_ms,
        "pages": page_count,
        "ms_per_page": ms_per_page,
        "budget_pass": ms_per_page < 60,
        "footnotes": footnotes,
        "ground_truth_available": ground_truth is not None
    }


def main():
    """Run multi-corpus validation"""
    print("="*80)
    print("MULTI-CORPUS VALIDATION")
    print("Testing: Derrida, Kant, Heidegger")
    print("="*80)

    # Define test cases
    test_cases = [
        {
            "pdf": "test_files/derrida_footnote_pages_120_125.pdf",
            "name": "Derrida (Traditional Bottom Footnotes)",
            "expected": 2,
            "ground_truth": "derrida_footnotes.json"
        },
        {
            "pdf": "test_files/kant_critique_pages_64_65.pdf",
            "name": "Kant 64-65 (Multi-Page Continuation)",
            "expected": 1,
            "ground_truth": None
        },
        {
            "pdf": "test_files/kant_critique_pages_80_85.pdf",
            "name": "Kant 80-85 (Mixed Schema)",
            "expected": 20,  # Approximate
            "ground_truth": None
        },
        {
            "pdf": "test_files/heidegger_pages_22-23_primary_footnote_test.pdf",
            "name": "Heidegger 22-23 (OCR Quality Test)",
            "expected": 4,
            "ground_truth": "heidegger_22_23_footnotes.json"
        }
    ]

    # Run all validations
    results = []
    for tc in test_cases:
        try:
            result = validate_corpus(
                tc["pdf"],
                tc["name"],
                tc["expected"],
                tc["ground_truth"]
            )
            results.append(result)
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "corpus": tc["name"],
                "error": str(e),
                "match": False,
                "budget_pass": False
            })

    # Summary report
    print(f"\n{'='*80}")
    print("SUMMARY REPORT")
    print(f"{'='*80}")

    total = len(results)
    passed = sum(1 for r in results if r.get("match", False))
    budget_pass = sum(1 for r in results if r.get("budget_pass", False))

    print(f"\n📊 Overall Results:")
    print(f"  Total corpora: {total}")
    print(f"  Footnote detection pass: {passed}/{total} ({100*passed/total:.1f}%)")
    print(f"  Performance budget pass: {budget_pass}/{total} ({100*budget_pass/total:.1f}%)")

    print(f"\n📋 Detailed Results:")
    print(f"  {'Corpus':<40} {'Detect':<10} {'Perf':<10}")
    print(f"  {'-'*40} {'-'*10} {'-'*10}")
    for r in results:
        if "error" not in r:
            detect_status = "✓" if r["match"] else "✗"
            perf_status = "✓" if r["budget_pass"] else "✗"
            corpus_name = r["corpus"][:39]
            print(f"  {corpus_name:<40} {detect_status:<10} {perf_status:<10}")

    # Production readiness verdict
    print(f"\n{'='*80}")
    print("PRODUCTION READINESS VERDICT")
    print(f"{'='*80}")

    all_pass = passed == total and budget_pass == total

    if all_pass:
        print("✅ APPROVED - All corpora validated successfully")
    else:
        print("⚠️  NEEDS ATTENTION - Some validations failed")
        print("\nIssues:")
        for r in results:
            if not r.get("match", False):
                print(f"  - {r['corpus']}: Footnote detection mismatch")
            if not r.get("budget_pass", False):
                print(f"  - {r['corpus']}: Performance budget exceeded")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
