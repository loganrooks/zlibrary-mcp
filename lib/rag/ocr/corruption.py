"""
OCR corruption detection.

Detects OCR corruption artifacts (tildes, excessive special characters,
mixed punctuation patterns) that indicate unreliable text.
"""
import logging
import re
from typing import Tuple

logger = logging.getLogger(__name__)

__all__ = [
    '_is_ocr_corrupted',
]

def _is_ocr_corrupted(text: str) -> Tuple[bool, float, str]:
    """
    Detect OCR corruption artifacts that indicate unreliable text.

    OCR corruption indicators:
    - Tilde (~) character - OCR uncertainty marker
    - Multiple special characters (>2 in short text)
    - Mixed punctuation patterns (letter-punct-letter)
    - Non-standard single characters

    This prevents false positive marker detection from corrupted text like:
    - "the~" (tilde corruption)
    - "of~·" (tilde + special chars)
    - "r:~sentially" (embedded corruption)
    - "cnt.i,ic~" (severe corruption)
    - "a.b,c:" (excessive punctuation)

    Args:
        text: Text to check for OCR corruption

    Returns:
        Tuple of (is_corrupted, confidence, reason):
        - is_corrupted: True if text appears corrupted
        - confidence: 0.0-1.0 confidence score
        - reason: Description of corruption type or 'clean_text'

    Examples:
        >>> _is_ocr_corrupted("the~")
        (True, 0.95, 'tilde_corruption')

        >>> _is_ocr_corrupted("cnt.i,ic~")
        (True, 0.95, 'tilde_corruption')

        >>> _is_ocr_corrupted("*")
        (False, 0.90, 'clean_text')

        >>> _is_ocr_corrupted("1")
        (False, 0.90, 'clean_text')
    """
    import re

    # Signal 1: Tilde character (strong corruption indicator)
    # This is the most reliable OCR corruption marker
    if '~' in text:
        return True, 0.95, 'tilde_corruption'

    # Signal 2: Multiple special characters in short text
    # Count non-alphanumeric characters (excluding valid marker symbols)
    special_chars = sum(1 for c in text if c in '.,;:!?@#$%^&*()[]{}|\\/<>')

    # Threshold: >2 special chars in text length <10
    if len(text) < 10 and special_chars > 2:
        return True, 0.90, 'excessive_special_chars'

    # Signal 3: Mixed corruption patterns (letter-punctuation-letter)
    # This catches patterns like "a.b" or "h:i" which are unlikely to be valid
    if re.search(r'[a-z][.,;:][a-z]', text):
        return True, 0.85, 'mixed_corruption'

    # Signal 4: Invalid single character
    # Single characters that are not valid markers should be rejected
    # Valid single char markers: digits, letters, common symbols
    if len(text) == 1:
        valid_single_chars = set('0123456789abcdefghijklmnopqrstuvwxyz*†‡§¶#')
        if text.lower() not in valid_single_chars:
            return True, 0.80, 'invalid_single_char'

    # Text appears clean
    return False, 0.90, 'clean_text'


