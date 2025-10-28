import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'lib'))

# Time the module import
start = time.perf_counter()
from footnote_continuation import is_footnote_incomplete
end = time.perf_counter()

print(f"Module import time: {(end - start) * 1000:.2f}ms")

# Time a call
start = time.perf_counter()
result = is_footnote_incomplete("This is a test sentence that ends mid")
end = time.perf_counter()

print(f"Function call time: {(end - start) * 1000:.2f}ms")
print(f"Result: {result}")
