#!/usr/bin/env python3
"""
Verify true baseline performance (without detect_footnotes enabled).
"""

import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / 'lib'))

import logging
logging.getLogger().setLevel(logging.ERROR)

from rag_processing import process_pdf

pdf_path = Path('test_files/kant_critique_pages_80_85.pdf')

# WITHOUT footnote detection
runs = 10
timings_no_footnotes = []

for _ in range(runs):
    start = time.perf_counter()
    output = process_pdf(pdf_path, detect_footnotes=False)
    end = time.perf_counter()
    timings_no_footnotes.append((end - start) * 1000)

avg_no_footnotes = sum(timings_no_footnotes) / len(timings_no_footnotes)
print(f"WITHOUT footnote detection: {avg_no_footnotes:.2f}ms total ({avg_no_footnotes/6:.2f}ms per page)")

# WITH footnote detection
timings_with_footnotes = []

for _ in range(runs):
    start = time.perf_counter()
    output = process_pdf(pdf_path, detect_footnotes=True)
    end = time.perf_counter()
    timings_with_footnotes.append((end - start) * 1000)

avg_with_footnotes = sum(timings_with_footnotes) / len(timings_with_footnotes)
print(f"WITH footnote detection: {avg_with_footnotes:.2f}ms total ({avg_with_footnotes/6:.2f}ms per page)")

footnote_overhead = (avg_with_footnotes - avg_no_footnotes) / 6
print(f"\nFootnote detection overhead: {footnote_overhead:.2f}ms per page")
print(f"Budget: 5.0ms")
print(f"Status: {'✅ PASS' if footnote_overhead <= 5.0 else '❌ FAIL'}")
