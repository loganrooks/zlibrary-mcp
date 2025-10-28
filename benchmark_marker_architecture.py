#!/usr/bin/env python3
"""
Performance benchmark for marker-driven footnote architecture.
Tests against <5ms budget and compares with baseline.
"""

import time
import cProfile
import pstats
import io
import statistics
from pathlib import Path
import sys
import logging

# Suppress noisy warnings
logging.getLogger('lib.footnote_continuation').setLevel(logging.ERROR)

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent / 'lib'))

from rag_processing import process_pdf

# Test fixtures with different characteristics
FIXTURES = [
    ('kant_critique_pages_80_85.pdf', 'Mixed inline + traditional'),
    ('derrida_footnote_pages_120_125.pdf', 'Traditional only'),
    ('kant_critique_pages_64_65.pdf', 'Inline only'),
]

BUDGET = {
    'marker_scan': 1.0,  # ms per page
    'definition_search': 2.0,  # ms per page
    'markerless_detection': 1.0,  # ms per page
    'total_new_overhead': 5.0  # ms per page
}

BASELINE = {
    'classification': 0.038,  # ms per footnote
    'incomplete_detection': 0.0004,  # ms per footnote (cached)
    'state_machine': 0.005,  # ms per page
    'total_per_page': 0.29  # ms per page (5 footnotes)
}

def count_pages(pdf_path):
    """Count pages in PDF."""
    import fitz
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    doc.close()
    return page_count

def benchmark_fixture(fixture_path, description, runs=10):
    """Benchmark a single fixture with multiple runs."""
    full_path = Path('test_files') / fixture_path
    
    if not full_path.exists():
        print(f"⚠️  Skipping {fixture_path}: File not found")
        return None
    
    page_count = count_pages(str(full_path))
    timings = []
    
    # Warm-up run
    process_pdf(Path(full_path), detect_footnotes=True)

    # Timed runs
    for _ in range(runs):
        start = time.perf_counter()
        process_pdf(Path(full_path), detect_footnotes=True)
        end = time.perf_counter()
        timings.append((end - start) * 1000)  # Convert to ms
    
    # Statistics
    avg_total = statistics.mean(timings)
    stdev_total = statistics.stdev(timings) if len(timings) > 1 else 0
    min_total = min(timings)
    max_total = max(timings)
    
    avg_per_page = avg_total / page_count
    
    return {
        'fixture': fixture_path,
        'description': description,
        'pages': page_count,
        'runs': runs,
        'avg_total_ms': avg_total,
        'stdev_ms': stdev_total,
        'min_ms': min_total,
        'max_ms': max_total,
        'avg_per_page_ms': avg_per_page,
        'timings': timings
    }

def profile_fixture(fixture_path):
    """Profile a fixture with cProfile."""
    full_path = Path('test_files') / fixture_path
    
    if not full_path.exists():
        return None
    
    profiler = cProfile.Profile()
    profiler.enable()

    process_pdf(Path(full_path), detect_footnotes=True)

    profiler.disable()
    
    # Capture stats
    s = io.StringIO()
    stats = pstats.Stats(profiler, stream=s)
    stats.sort_stats('cumulative')
    stats.print_stats(30)  # Top 30 functions
    
    return s.getvalue()

def main():
    print("=" * 80)
    print("MARKER-DRIVEN ARCHITECTURE PERFORMANCE VALIDATION")
    print("=" * 80)
    print()
    
    # Run benchmarks
    results = []
    for fixture_path, description in FIXTURES:
        print(f"Benchmarking: {fixture_path}")
        print(f"Type: {description}")
        result = benchmark_fixture(fixture_path, description)
        if result:
            results.append(result)
            print(f"  Pages: {result['pages']}")
            print(f"  Avg per page: {result['avg_per_page_ms']:.3f} ms ± {result['stdev_ms']/result['pages']:.3f} ms")
            print(f"  Total avg: {result['avg_total_ms']:.3f} ms (min: {result['min_ms']:.3f}, max: {result['max_ms']:.3f})")
            print()
    
    # Overall statistics
    if results:
        all_per_page = [r['avg_per_page_ms'] for r in results]
        overall_avg = statistics.mean(all_per_page)
        overall_stdev = statistics.stdev(all_per_page) if len(all_per_page) > 1 else 0
        
        print("=" * 80)
        print("OVERALL PERFORMANCE")
        print("=" * 80)
        print(f"Average per page (all fixtures): {overall_avg:.3f} ms ± {overall_stdev:.3f} ms")
        print(f"Baseline per page: {BASELINE['total_per_page']:.3f} ms")
        print(f"Overhead: +{overall_avg - BASELINE['total_per_page']:.3f} ms ({((overall_avg / BASELINE['total_per_page']) - 1) * 100:.1f}% increase)")
        print(f"Budget: {BUDGET['total_new_overhead']:.1f} ms")
        print()
        
        # Budget validation
        overhead = overall_avg - BASELINE['total_per_page']
        if overhead <= BUDGET['total_new_overhead']:
            print("✅ PASS: Within budget")
        else:
            print(f"❌ FAIL: Over budget by {overhead - BUDGET['total_new_overhead']:.3f} ms")
        print()
    
    # Profile the mixed fixture (most comprehensive)
    print("=" * 80)
    print("DETAILED PROFILING (kant_critique_pages_80_85.pdf)")
    print("=" * 80)
    profile_output = profile_fixture('kant_critique_pages_80_85.pdf')
    if profile_output:
        print(profile_output)
    
    # Real-world impact
    print("=" * 80)
    print("REAL-WORLD IMPACT")
    print("=" * 80)
    if results:
        for pages in [300, 600]:
            impact = overall_avg * pages
            print(f"{pages}-page book: +{impact:.0f} ms total ({impact/1000:.2f} seconds)")
        print()
        
        if overall_avg < 1.0:
            print("Impact: IMPERCEPTIBLE (< 1ms per page)")
        elif overall_avg < 5.0:
            print("Impact: NEGLIGIBLE (< 5ms per page)")
        elif overall_avg < 10.0:
            print("Impact: NOTICEABLE (5-10ms per page)")
        else:
            print("Impact: UNACCEPTABLE (> 10ms per page)")

if __name__ == '__main__':
    main()
