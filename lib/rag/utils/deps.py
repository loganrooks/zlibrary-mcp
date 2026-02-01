"""
Shared optional dependency imports for RAG processing.

All optional library imports are centralized here to allow consistent
mocking in tests. Both the facade (rag_processing.py) and submodules
import from this single location.
"""
import logging

logger = logging.getLogger(__name__)

# OCR Dependencies (Optional)
try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    pytesseract = None
    convert_from_path = None
    Image = None

try:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup, NavigableString
    EBOOKLIB_AVAILABLE = True
except ImportError:
    EBOOKLIB_AVAILABLE = False
    ebooklib = None
    epub = None
    BeautifulSoup = None
    NavigableString = None

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None

# X-mark detection (opencv) - Phase 2.3
try:
    import cv2
    import numpy as np
    XMARK_AVAILABLE = True
except ImportError:
    XMARK_AVAILABLE = False
    cv2 = None
    np = None
