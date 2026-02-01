"""
Custom exceptions for RAG processing.

Contains exception classes for file saving errors, OCR dependencies,
and Tesseract availability.
"""
import logging

logger = logging.getLogger(__name__)

__all__ = [
    'TesseractNotFoundError',
    'FileSaveError',
    'OCRDependencyError',
]

# Define placeholder initially, overwrite if import succeeds
class TesseractNotFoundError(Exception): pass

try:
    import pytesseract
    # If import succeeds, use the actual exception
    TesseractNotFoundError = pytesseract.TesseractNotFoundError
except ImportError:
    pass
    # Placeholder is already defined outside

# Custom Exception (Consider moving if used elsewhere, but keep here for now)
class FileSaveError(Exception):
    """Custom exception for errors during processed file saving."""
    pass

# Custom Exception for Dependency Issues
class OCRDependencyError(Exception): pass
