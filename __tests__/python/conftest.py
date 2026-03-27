import sys
import os
import pytest

# Add project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.fixture(autouse=True)
def _clear_pymupdf_cache():
    """Clear PyMuPDF textpage cache before each test to prevent stale object ID reuse."""
    try:
        from lib.rag.utils.cache import _clear_textpage_cache

        _clear_textpage_cache()
    except ImportError:
        pass
