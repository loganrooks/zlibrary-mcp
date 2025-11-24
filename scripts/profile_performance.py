#!/usr/bin/env python3
"""
Performance Profiling Script for RAG Footnote Detection

Profiles each corpus to identify performance bottlenecks.
Creates baseline metrics for optimization tracking.
"""

import sys
import cProfile
import pstats
import io
from pathlib import Path
from typing import Dict, Any
import json
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.rag_processing import process_pdf


def profile_corpus(name: str, pdf_path: Path, pages: int) -> Dict[str, Any]:
    """Profile a single corpus and return metrics."""

    print(f"\n{'='*60}")
    print(f"Profiling: {name}")
    print(f"PDF: {pdf_path}")
    print(f"Pages: {pages}")
    print(f"{'='*60}\n")

    # Create profiler
    profiler = cProfile.Profile()

    # Profile the processing
    start_time = time.time()
    profiler.enable()

    result = process_pdf(
        file_path=pdf_path,
        output_format="markdown",
        detect_footnotes=True
    )

    profiler.disable()
    end_time = time.time()

    # Calculate metrics
    total_time_ms = (end_time - start_time) * 1000
    time_per_page_ms = total_time_ms / pages

    # Get top functions by cumulative time
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions

    profile_output = stream.getvalue()

    # Extract top 10 hotspots
    hotspots = []
    lines = profile_output.split('\n')
    for line in lines[5:25]:  # Skip header, get top 20
        if line.strip() and not line.startswith('---'):
            hotspots.append(line.strip())

    metrics = {
        'name': name,
        'pdf_path': str(pdf_path),
        'pages': pages,
        'total_time_ms': round(total_time_ms, 2),
        'time_per_page_ms': round(time_per_page_ms, 2),
        'budget_ms_per_page': 60,
        'over_budget_multiplier': round(time_per_page_ms / 60, 2),
        'hotspots': hotspots[:10]
    }

    # Print summary
    print(f"\n{'='*60}")
    print(f"RESULTS: {name}")
    print(f"{'='*60}")
    print(f"Total Time: {total_time_ms:.2f}ms")
    print(f"Per Page: {time_per_page_ms:.2f}ms")
    print(f"Budget: 60ms/page")
    print(f"Over Budget: {metrics['over_budget_multiplier']:.1f}x")
    print(f"\nTop 10 Hotspots:")
    for i, hotspot in enumerate(metrics['hotspots'], 1):
        print(f"  {i}. {hotspot}")
    print()

    # Save detailed profile
    profile_file = Path(__file__).parent.parent / f"profile_{name.lower().replace(' ', '_')}.prof"
    profiler.dump_stats(str(profile_file))
    print(f"Detailed profile saved: {profile_file}")

    return metrics


def main():
    """Profile all test corpora."""

    print("="*60)
    print("PERFORMANCE BASELINE PROFILING")
    print("="*60)
    print("\nTarget: <60ms per page")
    print("Current: 377-609ms per page (6-10x over budget)")
    print("\nProfiling 4 test corpora to identify hotspots...")

    corpora = [
        ("Derrida", Path("test_files/derrida_footnote_pages_120_125.pdf"), 6),
        ("Kant 64-65", Path("test_files/kant_critique_pages_64_65.pdf"), 2),
        ("Kant 80-85", Path("test_files/kant_critique_pages_80_85.pdf"), 6),
        ("Heidegger", Path("test_files/heidegger_pages_22-23_primary_footnote_test.pdf"), 2)
    ]

    all_metrics = []

    for name, path, pages in corpora:
        if path.exists():
            metrics = profile_corpus(name, path, pages)
            all_metrics.append(metrics)
        else:
            print(f"\n⚠️  Skipping {name}: PDF not found at {path}")

    # Save baseline metrics
    baseline_file = Path(__file__).parent.parent / "performance_baseline.json"
    with open(baseline_file, 'w') as f:
        json.dump({
            'date': '2025-11-02',
            'baseline': 'After BUG-1,2,3,4 fixes, before BUG-5 optimization',
            'target_ms_per_page': 60,
            'corpora': all_metrics
        }, f, indent=2)

    print(f"\n{'='*60}")
    print("BASELINE SUMMARY")
    print(f"{'='*60}\n")

    total_pages = sum(m['pages'] for m in all_metrics)
    avg_time_per_page = sum(m['time_per_page_ms'] * m['pages'] for m in all_metrics) / total_pages

    print(f"Total pages profiled: {total_pages}")
    print(f"Average time per page: {avg_time_per_page:.2f}ms")
    print(f"Budget: 60ms/page")
    print(f"Over budget: {avg_time_per_page / 60:.1f}x")
    print(f"\nPer Corpus:")
    for m in all_metrics:
        status = '🔴' if m['over_budget_multiplier'] >= 8 else '🟡' if m['over_budget_multiplier'] >= 5 else '🟢'
        print(f"  {status} {m['name']}: {m['time_per_page_ms']:.0f}ms/page ({m['over_budget_multiplier']:.1f}x)")

    print(f"\nBaseline saved: {baseline_file}")
    print(f"Detailed profiles: profile_*.prof files")
    print(f"\nReady for optimization! 🚀")


if __name__ == '__main__':
    main()
