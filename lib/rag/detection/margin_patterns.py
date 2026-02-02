"""
Typed classification of margin content in scholarly PDFs.

Classifies text found in margin zones as Stephanus references (Plato),
Bekker numbers (Aristotle), line numbers, or generic margin annotations.
"""

import re
from typing import Tuple

# Stephanus: 2-3 digits + letter a-e, optional range like "b-c" or "b–c"
STEPHANUS_RE = re.compile(r"^(\d{2,3}[a-e](?:\s*[-\u2013]\s*[a-e])?)$")

# Bekker: 3-4 digits + a/b + 1-2 digit line number
BEKKER_RE = re.compile(r"^(\d{3,4}[ab]\d{1,2})$")

# Line numbers: 1-4 digits (validated to 1-9999 in code)
LINE_NUMBER_RE = re.compile(r"^(\d{1,4})$")


def classify_margin_content(text: str) -> Tuple[str, str]:
    """Classify margin text into a typed category.

    Returns:
        Tuple of (type, normalized_text) where type is one of:
        'stephanus', 'bekker', 'line_number', 'margin'
    """
    text = text.strip()
    if not text:
        return ("margin", text)

    # Check Bekker before Stephanus — Bekker is more specific
    # (digit+letter+digit vs digit+letter)
    if BEKKER_RE.match(text):
        return ("bekker", text)
    if STEPHANUS_RE.match(text):
        return ("stephanus", text)
    if LINE_NUMBER_RE.match(text):
        num = int(text)
        if 1 <= num <= 9999:
            return ("line_number", text)
    return ("margin", text)
