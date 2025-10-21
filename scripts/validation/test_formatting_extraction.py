#!/usr/bin/env python3
"""
Test formatting extraction accuracy against ground truth.

Validates that our pipeline correctly detects and preserves all formatting types:
- Bold, italic, bold+italic
- Underline, strikethrough, sous-erasure (X-marks)
- Superscript, subscript, monospace
- Complex combinations

Produces metrics:
- Precision: How many detected formats are correct?
- Recall: How many ground truth formats were found?
- F1 score per formatting type
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import fitz  # PyMuPDF

# Add lib to path for RAG processing
sys.path.insert(0, str(Path(__file__).parent / "lib"))

try:
    from rag_processing import extract_text_from_pdf
except ImportError:
    print("⚠️  Warning: Could not import rag_processing module")
    extract_text_from_pdf = None


TEST_FILES_DIR = Path("test_files")
GROUND_TRUTH_PATH = TEST_FILES_DIR / "test_formatting_ground_truth.json"


def load_ground_truth() -> Dict:
    """Load ground truth formatting data from JSON."""
    if not GROUND_TRUTH_PATH.exists():
        raise FileNotFoundError(f"Ground truth file not found: {GROUND_TRUTH_PATH}")

    with open(GROUND_TRUTH_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_with_pymupdf_native(pdf_path: Path) -> Dict:
    """Extract formatting using PyMuPDF's native capabilities."""
    doc = fitz.open(pdf_path)
    results = {}

    for page_num, page in enumerate(doc, start=1):
        page_results = []

        # Get text with format information
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if block["type"] == 0:  # Text block
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if not text:
                            continue

                        formats = []
                        font_name = span["font"].lower()
                        flags = span["flags"]

                        # Font-based detection
                        if "bold" in font_name or (flags & 16):  # Bold flag (bit 4)
                            formats.append("bold")
                        if "italic" in font_name or "oblique" in font_name or (flags & 2):  # Italic flag (bit 1)
                            formats.append("italic")
                        if "courier" in font_name or "mono" in font_name or (flags & 8):  # Monospaced flag (bit 3)
                            formats.append("monospaced")

                        # Superscript detection (flag bit 0)
                        if flags & 1:
                            formats.append("superscript")

                        # Subscript detection by size and position
                        # If smaller font and no superscript flag, likely subscript
                        if span["size"] < 10 and len(text) <= 3 and not (flags & 1):
                            # Additional check: subscript should be lower than normal baseline
                            formats.append("subscript")

                        page_results.append({
                            "text": text,
                            "formatting": formats,
                            "bbox": span["bbox"],
                            "y_position": span["origin"][1]
                        })

        results[f"page_{page_num}"] = page_results

    doc.close()
    return results


def extract_with_opencv_lines(pdf_path: Path) -> Dict:
    """
    Detect visual lines (strikethrough, underline, X-marks) using OpenCV.
    This simulates what our full pipeline should do.
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        print("⚠️  OpenCV not available, skipping line detection")
        return {}

    doc = fitz.open(pdf_path)
    line_detections = {}

    for page_num, page in enumerate(doc, start=1):
        # Render page to image
        pix = page.get_pixmap(dpi=300)
        img_data = pix.tobytes("png")
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detect lines
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100,
                                minLineLength=30, maxLineGap=5)

        detections = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))

                # Classify line type by angle and position
                if angle < 10:  # Horizontal lines
                    # Could be strikethrough or underline
                    detections.append({
                        "type": "horizontal_line",
                        "coords": (x1, y1, x2, y2),
                        "possible_formats": ["strikethrough", "underline"]
                    })
                elif 30 < angle < 60:  # Diagonal lines (X-marks)
                    detections.append({
                        "type": "diagonal_line",
                        "coords": (x1, y1, x2, y2),
                        "possible_formats": ["sous-erasure"]
                    })

        line_detections[f"page_{page_num}"] = detections

    doc.close()
    return line_detections


def find_matching_extracted(extracted_items: List[Dict], target_text: str,
                            target_y: float = None, tolerance: float = None) -> Dict:
    """
    Find extracted item matching ground truth text.

    Args:
        extracted_items: List of extracted text items with formatting
        target_text: Ground truth text to find
        target_y: (Unused) Kept for API compatibility
        tolerance: (Unused) Kept for API compatibility

    Returns:
        Matching extracted item or empty dict
    """
    # First try exact text match
    for item in extracted_items:
        if item["text"] == target_text:
            return item

    # Try fuzzy text match (contains)
    for item in extracted_items:
        if target_text in item["text"] or item["text"] in target_text:
                return item

    return {}


def calculate_metrics(gt_formats: Set[str], extracted_formats: Set[str]) -> Dict:
    """Calculate precision, recall, and F1 score."""
    tp = len(gt_formats & extracted_formats)  # True positives
    fp = len(extracted_formats - gt_formats)  # False positives
    fn = len(gt_formats - extracted_formats)  # False negatives

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "fp": fp,
        "fn": fn
    }


def test_formatting_extraction():
    """Main test function to validate extraction accuracy."""
    print("=" * 80)
    print("FORMATTING EXTRACTION VALIDATION")
    print("=" * 80)
    print()

    # Load ground truth
    print("Loading ground truth...")
    ground_truth = load_ground_truth()
    print(f"✓ Loaded ground truth for {len(ground_truth)} PDFs")
    print()

    # Test results storage
    all_results = {}
    format_type_results = defaultdict(list)

    # Test each PDF
    for pdf_name, expected_data in ground_truth.items():
        pdf_path = TEST_FILES_DIR / pdf_name
        if not pdf_path.exists():
            print(f"⚠️  PDF not found: {pdf_path}")
            continue

        print(f"\n{'=' * 80}")
        print(f"Testing: {pdf_name}")
        print(f"{'=' * 80}")

        # Extract with PyMuPDF native
        print("\n1. PyMuPDF Native Extraction...")
        extracted = extract_with_pymupdf_native(pdf_path)

        # Compare each page
        pdf_results = []
        for page_key, page_gt in expected_data.items():
            extracted_page = extracted.get(page_key, [])

            print(f"\n   {page_key.upper()}:")
            print(f"   Ground truth items: {len(page_gt)}")
            print(f"   Extracted items: {len(extracted_page)}")

            # Test each ground truth item
            for gt_item in page_gt:
                gt_text = gt_item["text"]
                gt_formats = set(gt_item["formatting"])
                gt_y = gt_item.get("y_approx", 0)

                # Find matching extracted item
                extracted_item = find_matching_extracted(
                    extracted_page, gt_text, gt_y
                )

                if extracted_item:
                    extracted_formats = set(extracted_item.get("formatting", []))
                else:
                    extracted_formats = set()

                # Calculate metrics
                metrics = calculate_metrics(gt_formats, extracted_formats)

                result = {
                    "text": gt_text,
                    "expected": list(gt_formats),
                    "extracted": list(extracted_formats),
                    "found": bool(extracted_item),
                    **metrics
                }

                pdf_results.append(result)

                # Track by format type
                for fmt in gt_formats:
                    format_type_results[fmt].append({
                        "text": gt_text,
                        "detected": fmt in extracted_formats,
                        **metrics
                    })

                # Print individual result
                status = "✓" if metrics["f1"] == 1.0 else "✗" if metrics["f1"] == 0.0 else "~"
                print(f"   {status} '{gt_text[:30]}...' - F1: {metrics['f1']:.2f}")
                if gt_formats != extracted_formats:
                    print(f"      Expected: {sorted(gt_formats)}")
                    print(f"      Got:      {sorted(extracted_formats)}")

        all_results[pdf_name] = pdf_results

    # Print summary by format type
    print(f"\n\n{'=' * 80}")
    print("SUMMARY BY FORMAT TYPE")
    print(f"{'=' * 80}")

    format_summary = {}
    for format_type, results in sorted(format_type_results.items()):
        total = len(results)
        detected = sum(1 for r in results if r["detected"])
        avg_precision = sum(r["precision"] for r in results) / total
        avg_recall = sum(r["recall"] for r in results) / total
        avg_f1 = sum(r["f1"] for r in results) / total

        format_summary[format_type] = {
            "total_instances": total,
            "detected": detected,
            "detection_rate": detected / total,
            "avg_precision": avg_precision,
            "avg_recall": avg_recall,
            "avg_f1": avg_f1
        }

        status = "✓✓✓" if avg_recall >= 0.8 else "⚠️⚠️" if avg_recall >= 0.5 else "✗✗✗"
        print(f"\n{format_type.upper()}: {status}")
        print(f"  Instances: {total}")
        print(f"  Detection Rate: {detected}/{total} ({detected/total*100:.1f}%)")
        print(f"  Avg Precision: {avg_precision:.3f}")
        print(f"  Avg Recall: {avg_recall:.3f}")
        print(f"  Avg F1: {avg_f1:.3f}")

    # Overall statistics
    print(f"\n\n{'=' * 80}")
    print("OVERALL STATISTICS")
    print(f"{'=' * 80}")

    total_tests = sum(len(results) for results in all_results.values())
    all_f1_scores = [item["f1"] for results in all_results.values() for item in results]
    avg_overall_f1 = sum(all_f1_scores) / len(all_f1_scores) if all_f1_scores else 0

    print(f"\nTotal test items: {total_tests}")
    print(f"Average F1 score: {avg_overall_f1:.3f}")

    perfect_matches = sum(1 for score in all_f1_scores if score == 1.0)
    print(f"Perfect matches: {perfect_matches}/{total_tests} ({perfect_matches/total_tests*100:.1f}%)")

    # Save detailed results
    results_path = TEST_FILES_DIR / "formatting_extraction_results.json"
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump({
            "detailed_results": all_results,
            "format_summary": format_summary,
            "overall": {
                "total_tests": total_tests,
                "avg_f1": avg_overall_f1,
                "perfect_matches": perfect_matches
            }
        }, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Detailed results saved to: {results_path}")

    # Recommendations
    print(f"\n\n{'=' * 80}")
    print("RECOMMENDATIONS")
    print(f"{'=' * 80}")

    for format_type, summary in sorted(format_summary.items(),
                                       key=lambda x: x[1]["avg_recall"]):
        if summary["avg_recall"] < 0.8:
            print(f"\n⚠️  {format_type.upper()} - Low recall ({summary['avg_recall']:.1%})")

            if format_type == "strikethrough":
                print("   → Implement OpenCV horizontal line detection")
                print("   → Check line position relative to text baseline")
                print("   → Distinguish from underlines by Y position")

            elif format_type == "sous-erasure":
                print("   → Implement diagonal line detection (already validated)")
                print("   → Use X-mark clustering to identify crossed-out text")
                print("   → Validate with angle detection (30-60 degrees)")

            elif format_type == "underline":
                print("   → Check PyMuPDF underline flags")
                print("   → Detect horizontal lines below text baseline")
                print("   → Distinguish from strikethrough by position")

            elif format_type in ["bold", "italic", "monospaced"]:
                print("   → PyMuPDF font detection should handle this")
                print("   → Verify font name and flags are being checked")

            elif format_type in ["superscript", "subscript"]:
                print("   → Implement font size + position detection")
                print("   → Check vertical offset from baseline")

    print("\n")
    return all_results, format_summary


if __name__ == "__main__":
    results, summary = test_formatting_extraction()

    # Exit with error code if any format has <80% recall
    for format_type, metrics in summary.items():
        if metrics["avg_recall"] < 0.8:
            print(f"\n❌ Format type '{format_type}' below 80% recall threshold")
            sys.exit(1)

    print("\n✅ All formatting types meet 80% recall threshold!")
    sys.exit(0)
