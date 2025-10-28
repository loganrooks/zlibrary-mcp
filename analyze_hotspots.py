#!/usr/bin/env python3
"""
Deep dive into performance hotspots for marker-driven architecture.
"""

import cProfile
import pstats
import io
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / 'lib'))

import logging
logging.getLogger('lib.footnote_continuation').setLevel(logging.ERROR)

from rag_processing import process_pdf

# Profile with detailed breakdown
profiler = cProfile.Profile()
profiler.enable()

result = process_pdf(
    Path('test_files/kant_critique_pages_80_85.pdf'),
    detect_footnotes=True
)

profiler.disable()

# Detailed stats
s = io.StringIO()
stats = pstats.Stats(profiler, stream=s)

print("=" * 80)
print("TOP 50 FUNCTIONS BY CUMULATIVE TIME")
print("=" * 80)
stats.sort_stats('cumulative')
stats.print_stats(50)
print(s.getvalue())

s = io.StringIO()
stats = pstats.Stats(profiler, stream=s)
print("\n" + "=" * 80)
print("TOP 30 FUNCTIONS BY TOTAL TIME (self time)")
print("=" * 80)
stats.sort_stats('tottime')
stats.print_stats(30)
print(s.getvalue())

# Focus on footnote-specific functions
s = io.StringIO()
stats = pstats.Stats(profiler, stream=s)
print("\n" + "=" * 80)
print("FOOTNOTE-RELATED FUNCTIONS")
print("=" * 80)
stats.sort_stats('cumulative')
stats.print_stats('footnote')
print(s.getvalue())
