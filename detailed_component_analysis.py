#!/usr/bin/env python3
"""
Detailed component breakdown for marker architecture performance.
"""

import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / 'lib'))

import logging
logging.getLogger('lib.footnote_continuation').setLevel(logging.ERROR)

# Import after path is set
import fitz
from rag_processing import process_pdf, _detect_footnotes_in_page, _get_cached_text_blocks, _clear_textpage_cache

# Test on Kant (mixed)
pdf_path = Path('test_files/kant_critique_pages_80_85.pdf')
doc = fitz.open(pdf_path)

print("Component Timing Analysis")
print("=" * 80)

# Time PDF open
start = time.perf_counter()
doc2 = fitz.open(pdf_path)
pdf_open_time = (time.perf_counter() - start) * 1000
print(f"PDF Open: {pdf_open_time:.2f}ms")

# Time textpage extraction (first page)
page = doc[0]
start = time.perf_counter()
blocks = page.get_text("dict")["blocks"]
textpage_time = (time.perf_counter() - start) * 1000
print(f"Textpage Extraction (uncached): {textpage_time:.2f}ms")

# Time cached extraction
start = time.perf_counter()
blocks2 = _get_cached_text_blocks(page, "dict")
cached_textpage_time = (time.perf_counter() - start) * 1000
print(f"Textpage Extraction (cached): {cached_textpage_time:.2f}ms")

# Time footnote detection per page
total_detect_time = 0
for i, page in enumerate(doc):
    start = time.perf_counter()
    result = _detect_footnotes_in_page(page, i)
    detect_time = (time.perf_counter() - start) * 1000
    total_detect_time += detect_time
    print(f"Page {i+1} footnote detection: {detect_time:.2f}ms (markers: {len(result['markers'])}, defs: {len(result['definitions'])})")

avg_detect = total_detect_time / len(doc)
print(f"\nAverage footnote detection: {avg_detect:.2f}ms per page")

# Total pipeline timing
_clear_textpage_cache()
doc.close()

start = time.perf_counter()
full_output = process_pdf(pdf_path, detect_footnotes=True)
total_time = (time.perf_counter() - start) * 1000
print(f"\nTotal process_pdf: {total_time:.2f}ms")
print(f"Per page: {total_time / 6:.2f}ms")

# Non-footnote overhead
non_footnote_overhead = (total_time - total_detect_time) / 6
print(f"\nNon-footnote overhead per page: {non_footnote_overhead:.2f}ms")
print(f"  (OCR quality, TOC, headings, etc.)")
