"""
Front matter extraction from PDF documents.

Contains publisher and year extraction from title/copyright pages.
"""
import logging

logger = logging.getLogger(__name__)

# Re-export from header module (where it lives alongside _generate_document_header)
from lib.rag.utils.header import _extract_publisher_from_front_matter

__all__ = [
    '_extract_publisher_from_front_matter',
]
