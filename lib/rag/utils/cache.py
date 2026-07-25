"""
Caching utilities for RAG processing.

Contains the textpage cache for PyMuPDF performance optimization,
avoiding redundant text extractions (13.3x reduction per page).
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

__all__ = [
    '_TEXTPAGE_CACHE',
    '_get_cached_text_blocks',
    '_clear_textpage_cache',
]

# Cache for PyMuPDF textpage objects (performance optimization)
# Key: (page_obj_id, extraction_type) -> (page, cached result)
#
# The entry pins a strong reference to the page object. Without the pin,
# CPython recycles the id() of a garbage-collected Page for the next Page
# allocated (measured ~90% of the time for back-to-back load_page calls),
# and the cache then serves page N's blocks for page M — non-deterministic
# footnote detection that depends on heap state (i.e. on which tests ran
# earlier in the suite). Storing the page keeps its id unique for the
# lifetime of the entry; the identity check on read is belt-and-braces.
_TEXTPAGE_CACHE = {}

def _get_cached_text_blocks(page: Any, extraction_type: str = "dict") -> List[Dict[str, Any]]:
    """
    Get text blocks from page with caching to avoid redundant extractions.

    Performance Note: Without caching, we extract textpage 13.3x per page.
    With caching, we extract once and reuse, saving ~12ms per page.

    Args:
        page: PyMuPDF page object
        extraction_type: "dict" or "text"

    Returns:
        List of text blocks (for "dict") or extracted text (for "text")
    """
    cache_key = (id(page), extraction_type)

    entry = _TEXTPAGE_CACHE.get(cache_key)
    if entry is not None and entry[0] is page:
        return entry[1]

    if extraction_type == "dict":
        result = page.get_text("dict")["blocks"]
    elif extraction_type == "text":
        result = page.get_text("text")
    else:
        raise ValueError(f"Invalid extraction_type: {extraction_type}")

    _TEXTPAGE_CACHE[cache_key] = (page, result)
    return result


def _clear_textpage_cache():
    """Clear textpage cache (call between documents or when memory is tight)."""
    global _TEXTPAGE_CACHE
    _TEXTPAGE_CACHE.clear()
