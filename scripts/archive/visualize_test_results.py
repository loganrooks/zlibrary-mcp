#!/usr/bin/env python3
"""
Create a visual summary of formatting extraction test results.
"""

import json
from pathlib import Path

def create_ascii_chart(format_summary):
    """Create ASCII bar chart of recall by format type."""
    print("\n" + "=" * 80)
    print("FORMATTING EXTRACTION RECALL BY TYPE")
    print("=" * 80 + "\n")

    # Sort by recall (ascending)
    sorted_formats = sorted(
        format_summary.items(),
        key=lambda x: x[1]["avg_recall"]
    )

    max_label_len = max(len(fmt) for fmt, _ in sorted_formats)

    for format_type, metrics in sorted_formats:
        recall = metrics["avg_recall"]
        bar_length = int(recall * 50)  # 50 chars = 100%
        bar = "█" * bar_length
        spaces = " " * (50 - bar_length)

        # Color coding
        if recall >= 0.8:
            status = "✅"
        elif recall >= 0.5:
            status = "⚠️ "
        else:
            status = "❌"

        print(f"{status} {format_type.upper():<{max_label_len + 2}} |{bar}{spaces}| {recall*100:5.1f}%")

    print("\n" + "=" * 80)
    print("THRESHOLD: 80% recall required")
    print("=" * 80 + "\n")


def print_detailed_breakdown(detailed_results):
    """Print breakdown by test PDF."""
    print("\n" + "=" * 80)
    print("DETAILED BREAKDOWN BY TEST PDF")
    print("=" * 80 + "\n")

    for pdf_name, results in detailed_results.items():
        total = len(results)
        perfect = sum(1 for r in results if r["f1"] == 1.0)
        failed = sum(1 for r in results if r["f1"] == 0.0)
        partial = total - perfect - failed

        print(f"\n📄 {pdf_name}")
        print(f"   Total items: {total}")
        print(f"   ✅ Perfect (F1=1.0): {perfect} ({perfect/total*100:.1f}%)")
        print(f"   ~ Partial (0<F1<1): {partial} ({partial/total*100:.1f}%)")
        print(f"   ❌ Failed (F1=0.0): {failed} ({failed/total*100:.1f}%)")

        # Show failed items
        if failed > 0:
            print(f"\n   Failed items:")
            for result in results:
                if result["f1"] == 0.0 and result["expected"]:
                    text_preview = result["text"][:40] + "..." if len(result["text"]) > 40 else result["text"]
                    print(f"      - '{text_preview}'")
                    print(f"        Expected: {sorted(result['expected'])}")
                    print(f"        Got:      {sorted(result['extracted'])}")


def print_recommendations(format_summary):
    """Print actionable recommendations."""
    print("\n" + "=" * 80)
    print("ACTIONABLE RECOMMENDATIONS")
    print("=" * 80 + "\n")

    # Group by severity
    critical = []
    moderate = []
    good = []

    for format_type, metrics in format_summary.items():
        recall = metrics["avg_recall"]
        if recall < 0.5:
            critical.append((format_type, metrics))
        elif recall < 0.8:
            moderate.append((format_type, metrics))
        else:
            good.append((format_type, metrics))

    if critical:
        print("🔴 CRITICAL (Recall < 50%):\n")
        for format_type, metrics in sorted(critical, key=lambda x: x[1]["avg_recall"]):
            print(f"   {format_type.upper()} ({metrics['avg_recall']*100:.1f}% recall)")

            if format_type == "strikethrough":
                print(f"   → Implement: OpenCV horizontal line detection")
                print(f"   → Check: Line at ~50% text height (middle)")
                print(f"   → Priority: HIGH\n")

            elif format_type == "sous-erasure":
                print(f"   → Implement: Diagonal line detection (30-60° angles)")
                print(f"   → Check: Crossing diagonals forming X pattern")
                print(f"   → Priority: CRITICAL (core feature)\n")

            elif format_type == "underline":
                print(f"   → Implement: Horizontal line detection below text")
                print(f"   → Check: Line at <20% text height (bottom)")
                print(f"   → Priority: MODERATE\n")

    if moderate:
        print("\n🟡 NEEDS IMPROVEMENT (50% ≤ Recall < 80%):\n")
        for format_type, metrics in sorted(moderate, key=lambda x: x[1]["avg_recall"]):
            print(f"   {format_type.upper()} ({metrics['avg_recall']*100:.1f}% recall)")
            print(f"   → Review detection logic for edge cases\n")

    if good:
        print("\n🟢 GOOD (Recall ≥ 80%):\n")
        for format_type, metrics in sorted(good, key=lambda x: -x[1]["avg_recall"]):
            print(f"   ✓ {format_type.upper()} ({metrics['avg_recall']*100:.1f}% recall)")


def main():
    """Generate visual summary of test results."""
    results_path = Path("test_files/formatting_extraction_results.json")

    if not results_path.exists():
        print(f"❌ Results file not found: {results_path}")
        print("Run 'python test_formatting_extraction.py' first.")
        return

    with open(results_path, 'r') as f:
        data = json.load(f)

    detailed_results = data["detailed_results"]
    format_summary = data["format_summary"]
    overall = data["overall"]

    # Header
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "FORMATTING EXTRACTION TEST RESULTS" + " " * 24 + "║")
    print("╚" + "═" * 78 + "╝")

    # Overall stats
    print(f"\nOverall Performance:")
    print(f"  Total test items:  {overall['total_tests']}")
    print(f"  Average F1 score:  {overall['avg_f1']:.3f}")
    print(f"  Perfect matches:   {overall['perfect_matches']}/{overall['total_tests']} ({overall['perfect_matches']/overall['total_tests']*100:.1f}%)")

    # Visual chart
    create_ascii_chart(format_summary)

    # Detailed breakdown
    print_detailed_breakdown(detailed_results)

    # Recommendations
    print_recommendations(format_summary)

    print("\n" + "=" * 80)
    print("Full report: test_files/FORMATTING_VALIDATION_REPORT.md")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
