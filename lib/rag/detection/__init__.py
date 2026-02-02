"""
lib.rag.detection - Detection modules for RAG processing.

Contains footnote, heading, TOC, front matter, page number, and margin detection.
"""

from lib.rag.detection.margins import detect_margin_content
from lib.rag.detection.margin_patterns import classify_margin_content

__all__ = ["detect_margin_content", "classify_margin_content"]
