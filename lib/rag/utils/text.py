"""
Text utility functions for RAG processing.

Contains slugification, HTML-to-text conversion, and markdown formatting helpers.
"""
import logging
import re
import unicodedata

logger = logging.getLogger(__name__)

__all__ = [
    '_slugify',
    '_html_to_text',
    '_apply_formatting_to_text',
]

# Conditional import for BeautifulSoup
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


# --- Slugify Helper ---

def _slugify(value, allow_unicode=False):
    """
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value).lower() # Ensure string and lowercase
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
        # Replace non-word chars (letters, numbers, underscore) with a space
        value = re.sub(r'[^\w]', ' ', value)
    else:
        # ASCII path: Normalize, encode/decode
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
        # Replace non a-z0-9 chars (including underscore) with a space
        value = re.sub(r'[^a-z0-9]', ' ', value)

    # Collapse consecutive whitespace to single hyphen
    value = re.sub(r'\s+', '-', value)
    # Strip leading/trailing hyphens
    value = value.strip('-')

    # Ensure slug is not empty, default to 'file' if it becomes empty
    return value if value else 'file'


def _html_to_text(html_content):
    """Extracts plain text from HTML using BeautifulSoup."""
    if not BeautifulSoup:
        logging.warning("BeautifulSoup not available, cannot extract text from HTML.")
        return ""
    try:
        soup = BeautifulSoup(html_content, 'lxml')
        return soup.get_text(separator='\n', strip=True)
    except Exception as e:
        logging.error(f"Error parsing HTML with BeautifulSoup: {e}")
        return "" # Return empty string on parsing error


def _apply_formatting_to_text(text: str, formatting: set) -> str:
    """
    Apply markdown formatting to text based on formatting set.

    IMPORTANT: Only applies if text doesn't already end with whitespace.
    This prevents malformed markdown like "*word *" which should be "*word* "

    Args:
        text: Plain text content
        formatting: Set of formatting types ('bold', 'italic', 'strikethrough', etc.)

    Returns:
        Text with markdown formatting applied (or plain if has trailing space)

    Examples:
        >>> _apply_formatting_to_text("hello", {"bold"})
        '**hello**'
        >>> _apply_formatting_to_text("hello ", {"bold"})  # Has trailing space
        'hello '  # Don't format - will be grouped later
    """
    if not formatting:
        return text

    # Don't apply formatting if text ends with whitespace
    # This prevents: "*word *" + "*another *" → malformed "*word **another *"
    # Instead: "word " + "another " → will be grouped and formatted together
    if text.endswith((' ', '\t', '\n')):
        return text

    # Apply formatting (same logic as TextSpan.to_markdown())
    # Handle bold + italic together (must check before individual)
    if "bold" in formatting and "italic" in formatting:
        text = f"***{text}***"
    elif "bold" in formatting:
        text = f"**{text}**"
    elif "italic" in formatting:
        text = f"*{text}*"

    # Other formatting (can combine with bold/italic)
    if "strikethrough" in formatting:
        text = f"~~{text}~~"
    if "sous-erasure" in formatting and "strikethrough" not in formatting:
        text = f"~~{text}~~"
    if "underline" in formatting:
        text = f"<u>{text}</u>"
    if "superscript" in formatting:
        text = f"^{text}^"
    if "subscript" in formatting:
        text = f"~{text}~"

    return text
