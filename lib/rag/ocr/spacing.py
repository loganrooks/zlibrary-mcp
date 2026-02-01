"""
OCR letter spacing detection and correction.

Detects and corrects excessive letter spacing artifacts common in
scanned PDFs (e.g., "T H E" instead of "THE").
"""
import logging
import re

logger = logging.getLogger(__name__)

__all__ = [
    'detect_letter_spacing_issue',
    'correct_letter_spacing',
]

def detect_letter_spacing_issue(text: str, sample_size: int = 500) -> bool:
    """
    Detects if text has excessive letter spacing (e.g., "T H E" instead of "THE").

    This is a common OCR issue in scanned PDFs where spaces appear between every letter.

    Args:
        text: Text to analyze
        sample_size: Number of characters to sample for analysis

    Returns:
        True if letter spacing issue detected
    """
    if len(text) < 10:  # Lower threshold for short samples
        return False

    # Sample text for analysis (first N characters)
    sample = text[:sample_size] if len(text) > sample_size else text

    # Count words that are single letters (the symptom of letter spacing)
    words = sample.split()
    if len(words) == 0:
        return False

    single_letter_words = sum(1 for word in words if len(word.strip()) == 1 and word.isalpha())

    # Calculate ratio of single-letter words to total words
    ratio = single_letter_words / len(words)

    # If more than 50% of words are single letters, it's likely a spacing issue
    # Lowered threshold to catch "T h e  B o o k" style cases
    if ratio > 0.5:
        logging.debug(f"Letter spacing issue detected: {single_letter_words}/{len(words)} words are single letters ({ratio:.1%})")
        return True

    return False


def correct_letter_spacing(text: str) -> str:
    """
    Corrects excessive letter spacing in OCR text.

    Transforms: "T H E  B U R N O U T" → "THE BURNOUT"

    Algorithm:
    1. Identify sequences of single letters separated by spaces
    2. Collapse them into words
    3. Preserve intentional spacing and punctuation

    Args:
        text: Text with potential letter spacing issues

    Returns:
        Corrected text
    """
    if not text or not detect_letter_spacing_issue(text):
        return text

    logging.info("Applying letter spacing correction...")

    # Split into lines to preserve paragraph structure
    lines = text.split('\n')
    corrected_lines = []

    for line in lines:
        # Pattern explanation:
        # - Matches sequences of single letters with spaces between them
        # - Handles: "T H E", "T h e", "T H E ,", etc.
        # - Captures letters and spaces, excluding punctuation at boundaries
        #
        # Strategy: Find patterns like "X Y Z" where X, Y, Z are single letters
        # This works by looking for: letter + (space + letter) repeated 1+ times

        # First, handle case where letters are separated by single spaces
        # This pattern captures "T H E" or "T h e" style sequences
        corrected_line = line

        # Multiple passes to handle all patterns
        max_iterations = 5
        for _ in range(max_iterations):
            original = corrected_line

            # Pattern: Single letter, space, another single letter (repeated)
            # Matches: "T H E", "T h e", "B O O K", etc.
            # Uses lookbehind and lookahead to avoid word boundaries issues
            corrected_line = re.sub(
                r'(?<!\S)([A-Za-z])(\s+[A-Za-z])+(?!\S)',
                lambda m: m.group(0).replace(' ', ''),
                corrected_line
            )

            # If no changes, we're done
            if corrected_line == original:
                break

        corrected_lines.append(corrected_line)

    corrected_text = '\n'.join(corrected_lines)

    # Clean up any excessive spaces that may have been introduced
    corrected_text = re.sub(r'\s{3,}', '  ', corrected_text)

    logging.info(f"Letter spacing correction complete. Length: {len(text)} → {len(corrected_text)}")
    return corrected_text


