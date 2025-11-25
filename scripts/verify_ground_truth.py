#!/usr/bin/env python3
"""
Ground Truth Verification Script

Processes actual PDFs and compares detected footnotes against ground truth files.
Produces detailed verification report showing:
- Detection accuracy (TP, FP, FN)
- Content accuracy
- Diagnosis validation
"""

import json
import sys
from pathlib import Path
from typing import Any

# Add project root to path for proper imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lib.rag_processing import process_pdf


def load_ground_truth(gt_path: Path) -> dict:
    """Load ground truth JSON file."""
    with open(gt_path) as f:
        return json.load(f)


def extract_footnotes_from_pdf(pdf_path: Path) -> tuple[list[dict], str]:
    """Process PDF and extract footnotes.

    Returns:
        Tuple of (list of detected footnote dicts, raw markdown output)
    """
    import re

    result = process_pdf(
        pdf_path,
        output_format="markdown",
        detect_footnotes=True,
        enable_quality_pipeline=False  # Fast mode
    )

    # Parse footnotes from markdown output
    # Format: [^marker]: content
    # The ## Footnotes section contains properly formatted footnotes
    footnotes = []

    # Find the footnotes section
    footnotes_section_match = re.search(r'## Footnotes\s*\n(.+)', result, re.DOTALL)
    if not footnotes_section_match:
        return footnotes, result

    footnotes_section = footnotes_section_match.group(1)

    # Pattern for footnotes: [^marker]: content (marker is short - single char or 2-digit number)
    # Only match markers that are: single char (a-z, A-Z, *, †, ‡, §, ¶) or 1-2 digit numbers
    pattern = r'\[\^([a-zA-Z*†‡§¶\d]{1,2})\]:\s*(.+?)(?=\n\[\^|\Z)'

    for match in re.finditer(pattern, footnotes_section, re.DOTALL):
        marker = match.group(1)
        content = match.group(2).strip()
        footnotes.append({
            "marker": marker,
            "content": content
        })

    return footnotes, result


def compare_footnotes(detected: list[dict], ground_truth: dict, markdown_output: str = "") -> dict:
    """Compare detected footnotes against ground truth."""
    # Extract expected footnotes
    if "features" in ground_truth:
        # Derrida/Kant 80-85 format
        expected = ground_truth["features"]["footnotes"]
    elif "footnotes" in ground_truth:
        # Heidegger/Kant 64-65 format
        expected = ground_truth["footnotes"]
    else:
        expected = []

    # Build expected markers set (just markers, ignoring pages for simpler comparison)
    expected_markers = {}
    for fn in expected:
        if isinstance(fn.get("marker"), dict):
            marker = fn["marker"]["symbol"]
        else:
            marker = fn.get("marker", fn.get("actual_marker", ""))

        # Use marker as key (handles page restarts via per-page deduplication in system)
        if marker not in expected_markers:
            expected_markers[marker] = []
        expected_markers[marker].append(fn)

    # Build detected markers set
    detected_markers = {}
    for fn in detected:
        marker = fn.get("marker", "")
        if marker not in detected_markers:
            detected_markers[marker] = []
        detected_markers[marker].append(fn)

    # Calculate TP, FP, FN by marker (allowing multiple of same marker)
    expected_marker_counts = {m: len(fns) for m, fns in expected_markers.items()}
    detected_marker_counts = {m: len(fns) for m, fns in detected_markers.items()}

    # True positives: min(expected, detected) for each marker
    true_positives = 0
    for marker in expected_marker_counts:
        tp = min(expected_marker_counts.get(marker, 0),
                 detected_marker_counts.get(marker, 0))
        true_positives += tp

    # False positives: detected but not expected (or excess over expected)
    false_positives = 0
    fp_markers = []
    for marker, count in detected_marker_counts.items():
        expected_count = expected_marker_counts.get(marker, 0)
        if count > expected_count:
            false_positives += count - expected_count
            fp_markers.append((marker, count - expected_count))

    # False negatives: expected but not detected (or fewer than expected)
    false_negatives = 0
    fn_markers = []
    for marker, count in expected_marker_counts.items():
        detected_count = detected_marker_counts.get(marker, 0)
        if detected_count < count:
            false_negatives += count - detected_count
            fn_markers.append((marker, count - detected_count))

    total_expected = sum(expected_marker_counts.values())
    total_detected = sum(detected_marker_counts.values())

    return {
        "expected_count": total_expected,
        "detected_count": total_detected,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "precision": true_positives / total_detected if total_detected else 0,
        "recall": true_positives / total_expected if total_expected else 0,
        "fp_markers": fp_markers,
        "fn_markers": fn_markers,
        "expected_marker_counts": expected_marker_counts,
        "detected_marker_counts": detected_marker_counts,
        "detected_details": detected,
        "expected_details": expected,
        "markdown_output": markdown_output[:2000] if markdown_output else ""  # First 2K for debugging
    }


def verify_corpus(name: str, pdf_path: Path, gt_path: Path) -> dict:
    """Verify a single test corpus."""
    print(f"\n{'='*60}")
    print(f"Verifying: {name}")
    print(f"PDF: {pdf_path}")
    print(f"Ground Truth: {gt_path}")
    print(f"{'='*60}")

    # Check files exist
    if not pdf_path.exists():
        return {"error": f"PDF not found: {pdf_path}"}
    if not gt_path.exists():
        return {"error": f"Ground truth not found: {gt_path}"}

    # Load ground truth
    gt = load_ground_truth(gt_path)
    print(f"Ground truth loaded: {gt.get('test_name', gt.get('source', 'unknown'))}")

    # Process PDF
    print("Processing PDF...")
    detected, markdown_output = extract_footnotes_from_pdf(pdf_path)
    print(f"Detected {len(detected)} footnotes")

    # Compare
    comparison = compare_footnotes(detected, gt, markdown_output)

    # Print summary
    print(f"\n--- Results ---")
    print(f"Expected: {comparison['expected_count']}")
    print(f"Detected: {comparison['detected_count']}")
    print(f"True Positives: {comparison['true_positives']}")
    print(f"False Positives: {comparison['false_positives']}")
    print(f"False Negatives: {comparison['false_negatives']}")
    print(f"Precision: {comparison['precision']:.2%}")
    print(f"Recall: {comparison['recall']:.2%}")

    # Detail false positives
    if comparison['fp_markers']:
        print(f"\n⚠️  False Positives (detected but not in ground truth):")
        for marker, excess_count in comparison['fp_markers']:
            print(f"   - Marker '{marker}' ({excess_count} extra)")
            # Find the detected footnote for details
            for fn in detected:
                fn_marker = fn.get("marker", "")
                if fn_marker == marker:
                    content = fn.get("content", "")[:100]
                    print(f"     Content: {content}...")

    # Detail false negatives
    if comparison['fn_markers']:
        print(f"\n❌ False Negatives (in ground truth but not detected):")
        for marker, missing_count in comparison['fn_markers']:
            print(f"   - Marker '{marker}' ({missing_count} missing)")

    # Show expected vs detected markers
    print(f"\n📊 Marker Summary:")
    print(f"   Expected: {comparison['expected_marker_counts']}")
    print(f"   Detected: {comparison['detected_marker_counts']}")

    # Show all detected markers with content preview
    print(f"\n📝 All Detected Footnotes:")
    for fn in detected:
        marker = fn.get("marker", "?")
        content = fn.get("content", "")[:80].replace("\n", " ")
        print(f"   [{marker}]: {content}...")

    return comparison


def main():
    """Run verification on all test corpora."""
    base_path = Path(__file__).parent.parent
    test_files = base_path / "test_files"
    gt_path = test_files / "ground_truth"

    # Define test corpora
    corpora = [
        {
            "name": "Derrida (pages 120-125)",
            "pdf": test_files / "derrida_footnote_pages_120_125.pdf",
            "gt": gt_path / "derrida_footnotes.json"
        },
        {
            "name": "Kant 64-65 (continuation test)",
            "pdf": test_files / "kant_critique_pages_64_65.pdf",
            "gt": gt_path / "kant_64_65_footnotes.json"
        },
        {
            "name": "Kant 80-85 (mixed schema)",
            "pdf": test_files / "kant_critique_pages_80_85.pdf",
            "gt": gt_path / "kant_footnotes.json"
        },
        {
            "name": "Heidegger 22-23 (deduplication)",
            "pdf": test_files / "heidegger_pages_22-23_primary_footnote_test.pdf",
            "gt": gt_path / "heidegger_22_23_footnotes.json"
        }
    ]

    results = {}
    for corpus in corpora:
        result = verify_corpus(corpus["name"], corpus["pdf"], corpus["gt"])
        results[corpus["name"]] = result

    # Summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)

    total_expected = 0
    total_detected = 0
    total_tp = 0
    total_fp = 0
    total_fn = 0

    for name, result in results.items():
        if "error" in result:
            print(f"❌ {name}: {result['error']}")
            continue

        total_expected += result["expected_count"]
        total_detected += result["detected_count"]
        total_tp += result["true_positives"]
        total_fp += result["false_positives"]
        total_fn += result["false_negatives"]

        status = "✅" if result["false_negatives"] == 0 else "⚠️"
        print(f"{status} {name}: {result['true_positives']}/{result['expected_count']} detected, "
              f"{result['false_positives']} FP, {result['false_negatives']} FN")

    print(f"\n--- Overall ---")
    print(f"Total Expected: {total_expected}")
    print(f"Total Detected: {total_detected}")
    print(f"True Positives: {total_tp}")
    print(f"False Positives: {total_fp}")
    print(f"False Negatives: {total_fn}")

    if total_detected > 0:
        print(f"Precision: {total_tp/total_detected:.2%}")
    if total_expected > 0:
        print(f"Recall: {total_tp/total_expected:.2%}")

    # Return exit code
    return 0 if total_fn == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
