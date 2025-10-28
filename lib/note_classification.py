"""
Note classification for scholarly document processing.

This module provides multi-factor classification to distinguish between:
- Author notes (original work annotations)
- Translator notes (language/cultural glosses)
- Editor notes (textual commentary, modern additions)

Classification Strategy:
    1. Schema-based primary classification (marker patterns)
    2. Content-based validation (linguistic markers, editorial phrases)
    3. Conflict resolution with confidence scoring

Design Philosophy:
    "Preserve scholarly attribution" - Correctly attributing notes to their
    source is critical for academic integrity and proper citation.

Created: 2025-10-27 (Phase 3 of RAG architecture enhancement)

Example Usage:
    from lib.note_classification import classify_note_comprehensive
    from lib.rag_data_models import NoteSource

    result = classify_note_comprehensive(
        marker="a",
        content="German: 'aufgegeben' (given up)",
        schema_type="alphabetic",
        marker_info={'is_lowercase': True}
    )
    # result = {
    #     'note_source': NoteSource.TRANSLATOR,
    #     'confidence': 0.95,
    #     'evidence': {...},
    #     'method': 'schema+content_agreement'
    # }
"""

import re
from typing import Dict, Tuple, Optional
from enum import Enum

from lib.rag_data_models import NoteSource


# =============================================================================
# Classification Patterns
# =============================================================================

# Editorial phrase patterns (case-insensitive)
EDITORIAL_PATTERNS = [
    r'\bas\s+in\s+the\s+(first|second|original)\s+edition\b',
    r'\b(kant|hegel|heidegger|derrida)\s+(wrote|says|argues|notes)\b',
    r'\bwe\s+follow\b',
    r'\bin\s+the\s+original\s+(text|manuscript)\b',
    r'\bthe\s+editor\b',
    r'\btextual\s+variant\b',
    r'\bsee\s+also\s+the\s+editor',
    r'\bthis\s+passage\b',
    r'\bin\s+some\s+editions\b',
    r'\bomitted\s+in\b',
    r'\badded\s+in\b',
]

# Translation indicator patterns (case-insensitive)
TRANSLATION_PATTERNS = [
    r'\bliteral(ly)?\b',
    r'\bgerman:',
    r'\blat(in)?:',
    r'\bfrench:',
    r'\bgreek:',
    r'\b(lit\.|i\.e\.|viz\.)\b',
    r'\bin\s+the\s+original\b',
    r'\btranslation:',
    r'\bword\s+for\s+word\b',
]

# Cross-reference patterns (informational, doesn't change classification)
CROSS_REFERENCE_PATTERNS = [
    r'\bsee\s+(chapter|section|page|note)\s+\d+\b',
    r'\bcf\.\s+',
    r'\bcompare\s+',
]

# Short foreign word pattern (translator gloss)
# Matches: 1-3 words, may have quotes/diacritics
# Case-insensitive to handle proper nouns like 'Dasein'
SHORT_FOREIGN_WORD = re.compile(
    r'^[\'\"\s]*'                             # Leading quotes/whitespace
    r'[a-zA-ZäöüßéèêàâçñÄÖÜ]+'                # First word (with accents)
    r'(\s+[a-zA-ZäöüßéèêàâçñÄÖÜ]+){0,2}'      # Optional 2 more words
    r'[\'\"\s]*$',                            # Trailing quotes/whitespace
    re.IGNORECASE
)


# =============================================================================
# Schema-Based Classification
# =============================================================================

def classify_by_schema(
    marker: str,
    schema_type: str,
    marker_info: Dict
) -> NoteSource:
    """
    Classify note source based on marker schema (primary classification).

    Classification Rules:
        - Alphabetic lowercase (a, b, c) → TRANSLATOR
          Rationale: Convention in academic texts for translator glosses

        - Numeric with superscript (1, 2, 3) → AUTHOR
          Rationale: Standard footnote markers for original content

        - Symbolic (*, †, ‡) → TRANSLATOR (modern convention)
          Exception: Single * with long content (>200 chars) → EDITOR
          Rationale: * often used for translator notes, but lengthy * notes
                     typically indicate editorial commentary

        - Alphabetic uppercase (A, B, C) → EDITOR
          Rationale: Rare but used for editorial apparatus

        - Roman numerals (i, ii, iii) → AUTHOR
          Rationale: Classical academic style for author's own notes

    Args:
        marker: The note marker string ("1", "a", "*", etc.)
        schema_type: Schema category ("numeric", "alphabetic", "symbolic", etc.)
        marker_info: Additional marker metadata (e.g., {'is_lowercase': True})

    Returns:
        NoteSource enum value representing preliminary classification

    Example:
        >>> classify_by_schema("a", "alphabetic", {"is_lowercase": True})
        NoteSource.TRANSLATOR

        >>> classify_by_schema("1", "numeric", {"is_superscript": True})
        NoteSource.AUTHOR

        >>> classify_by_schema("*", "symbolic", {"content_length": 250})
        NoteSource.EDITOR  # Long content overrides default TRANSLATOR
    """
    schema_type = schema_type.lower()
    marker_lower = marker.lower()

    # Alphabetic markers
    if schema_type == "alphabetic":
        is_lowercase = marker_info.get('is_lowercase', marker.islower())
        is_uppercase = marker_info.get('is_uppercase', marker.isupper())

        if is_lowercase:
            return NoteSource.TRANSLATOR  # Convention: a, b, c = translator
        elif is_uppercase:
            return NoteSource.EDITOR  # Convention: A, B, C = editor

    # Numeric markers (standard footnotes)
    elif schema_type == "numeric":
        is_superscript = marker_info.get('is_superscript', True)
        if is_superscript or marker.isdigit():
            return NoteSource.AUTHOR  # Standard author footnotes

    # Symbolic markers
    elif schema_type == "symbolic":
        content_length = marker_info.get('content_length', 0)

        # Single asterisk with long content → likely editor note
        if marker == "*" and content_length > 200:
            return NoteSource.EDITOR

        # Otherwise symbolic → translator (modern convention)
        return NoteSource.TRANSLATOR

    # Roman numerals (classical academic style)
    elif schema_type == "roman":
        return NoteSource.AUTHOR  # Classical author style

    # Default: cannot classify by schema alone
    return NoteSource.UNKNOWN


# =============================================================================
# Content-Based Validation
# =============================================================================

def validate_classification_by_content(
    note_text: str,
    preliminary_source: NoteSource
) -> Tuple[NoteSource, float]:
    """
    Validate and potentially override classification using content analysis.

    Content Analysis Rules:
        1. Short foreign word (≤3 words, lowercase) → TRANSLATOR (conf: 0.92)
           Example: "aufgegeben" or "être et temps"

        2. Editorial phrases → EDITOR (conf: 0.90)
           Examples: "as in the first edition", "Kant wrote", "we follow"

        3. Translation indicators → TRANSLATOR (conf: 0.88)
           Examples: "literal", "German:", "lat:", "in the original"

        4. Cross-references → informational only, keeps preliminary
           Examples: "see chapter 5", "cf. note 12"

    Confidence Interpretation:
        0.92: Very strong content signal (short foreign word)
        0.90: Strong editorial language detected
        0.88: Strong translation indicators
        0.70: Content provides some validation
        0.50: No strong content signals (neutral)

    Args:
        note_text: The full text content of the note
        preliminary_source: Initial classification from schema

    Returns:
        Tuple of (validated_source, confidence_score)

    Example:
        >>> validate_classification_by_content(
        ...     "German: 'Dasein' (being-there)",
        ...     NoteSource.TRANSLATOR
        ... )
        (NoteSource.TRANSLATOR, 0.88)

        >>> validate_classification_by_content(
        ...     "As in the first edition, we follow...",
        ...     NoteSource.TRANSLATOR
        ... )
        (NoteSource.EDITOR, 0.90)  # Override with high confidence
    """
    text_lower = note_text.lower().strip()
    text_stripped = note_text.strip()

    # Rule 1: Short foreign word (very high confidence translator gloss)
    if len(text_stripped) <= 50:  # Short notes only
        # Pattern handles quotes internally, just test directly
        if SHORT_FOREIGN_WORD.match(text_stripped):
            return (NoteSource.TRANSLATOR, 0.92)

    # Rule 2: Editorial phrases (high confidence editor)
    for pattern in EDITORIAL_PATTERNS:
        if re.search(pattern, text_lower):
            return (NoteSource.EDITOR, 0.90)

    # Rule 3: Translation indicators (high confidence translator)
    for pattern in TRANSLATION_PATTERNS:
        if re.search(pattern, text_lower):
            return (NoteSource.TRANSLATOR, 0.88)

    # Rule 4: Cross-references (informational, keep preliminary)
    has_cross_ref = any(
        re.search(pattern, text_lower)
        for pattern in CROSS_REFERENCE_PATTERNS
    )
    if has_cross_ref:
        # Cross-reference doesn't change classification, but provides context
        return (preliminary_source, 0.70)

    # No strong content signals, return preliminary with neutral confidence
    return (preliminary_source, 0.50)


# =============================================================================
# Comprehensive Classification
# =============================================================================

def classify_note_comprehensive(
    marker: str,
    content: str,
    schema_type: str,
    marker_info: Optional[Dict] = None
) -> Dict:
    """
    Perform comprehensive note classification with conflict resolution.

    Three-Stage Process:
        1. Schema-based primary classification (marker patterns)
        2. Content-based validation (linguistic analysis)
        3. Conflict resolution with confidence scoring

    Conflict Resolution Rules:
        - Schema=AUTHOR, Content=EDITOR/TRANSLATOR:
          Keep AUTHOR (schema wins, high confidence in numeric markers)
          Final confidence: 0.80

        - Schema=TRANSLATOR, Content=EDITOR:
          Use EDITOR (content wins, editorial language is explicit)
          Final confidence: content_confidence (0.90)

        - Schema=EDITOR, Content=TRANSLATOR:
          Use TRANSLATOR (content wins, translation markers explicit)
          Final confidence: content_confidence (0.88)

        - Agreement (schema == content):
          Boost confidence to 0.95 (mutual reinforcement)

    Args:
        marker: Note marker string ("1", "a", "*", etc.)
        content: Full text content of the note
        schema_type: Schema category ("numeric", "alphabetic", "symbolic")
        marker_info: Optional marker metadata dict

    Returns:
        Classification result dictionary:
        {
            'note_source': NoteSource enum value,
            'confidence': float (0.0-1.0),
            'evidence': {
                'schema_classification': NoteSource,
                'content_classification': NoteSource,
                'content_confidence': float,
                'agreement': bool,
                'marker': str,
                'content_preview': str (first 100 chars)
            },
            'method': str (classification method used)
        }

    Example:
        >>> result = classify_note_comprehensive(
        ...     marker="a",
        ...     content="German: 'Aufhebung' (sublation)",
        ...     schema_type="alphabetic",
        ...     marker_info={'is_lowercase': True}
        ... )
        >>> result['note_source']
        NoteSource.TRANSLATOR
        >>> result['confidence']
        0.95  # Schema and content agree
        >>> result['method']
        'schema+content_agreement'
    """
    # Default marker_info if not provided
    if marker_info is None:
        marker_info = {
            'is_lowercase': marker.islower(),
            'is_uppercase': marker.isupper(),
            'content_length': len(content)
        }
    else:
        # Ensure content_length is present
        marker_info['content_length'] = marker_info.get('content_length', len(content))

    # Stage 1: Schema-based classification
    schema_source = classify_by_schema(marker, schema_type, marker_info)

    # Stage 2: Content-based validation
    content_source, content_confidence = validate_classification_by_content(
        content, schema_source
    )

    # Stage 3: Conflict resolution
    agreement = (schema_source == content_source)

    if agreement:
        # Mutual reinforcement: boost confidence
        final_source = schema_source
        final_confidence = 0.95
        method = "schema+content_agreement"

    elif schema_source == NoteSource.AUTHOR:
        # Author classification from schema is strong signal
        # (numeric superscripts are reliable), keep it
        final_source = NoteSource.AUTHOR
        final_confidence = 0.80
        method = "schema_priority_author"

    elif content_source == NoteSource.EDITOR and content_confidence >= 0.85:
        # Strong editorial language overrides schema
        final_source = NoteSource.EDITOR
        final_confidence = content_confidence
        method = "content_override_editor"

    elif content_source == NoteSource.TRANSLATOR and content_confidence >= 0.85:
        # Strong translation markers override schema
        final_source = NoteSource.TRANSLATOR
        final_confidence = content_confidence
        method = "content_override_translator"

    elif schema_source != NoteSource.UNKNOWN:
        # Schema provides guidance but weak content signal
        final_source = schema_source
        final_confidence = 0.75
        method = "schema_with_weak_content"

    else:
        # No strong signals from either source
        final_source = NoteSource.UNKNOWN
        final_confidence = 0.50
        method = "insufficient_evidence"

    # Build evidence dictionary for debugging/validation
    evidence = {
        'schema_classification': schema_source,
        'content_classification': content_source,
        'content_confidence': content_confidence,
        'agreement': agreement,
        'marker': marker,
        'schema_type': schema_type,
        'content_preview': content[:100] if len(content) > 100 else content
    }

    return {
        'note_source': final_source,
        'confidence': final_confidence,
        'evidence': evidence,
        'method': method
    }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'classify_by_schema',
    'validate_classification_by_content',
    'classify_note_comprehensive',
]
