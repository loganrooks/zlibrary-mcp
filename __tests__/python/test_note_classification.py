"""
Unit tests for note classification logic.

Tests multi-factor classification for distinguishing author, translator,
and editor notes in scholarly documents.

Created: 2025-10-27
"""

import pytest
from lib.note_classification import (
    classify_by_schema,
    validate_classification_by_content,
    classify_note_comprehensive,
)

pytestmark = pytest.mark.unit
from lib.rag_data_models import NoteSource


# =============================================================================
# Schema Classification Tests
# =============================================================================


class TestClassifyBySchema:
    """Test schema-based note classification."""

    def test_alphabetic_lowercase_translator(self):
        """Alphabetic lowercase markers indicate translator notes."""
        result = classify_by_schema("a", "alphabetic", {"is_lowercase": True})
        assert result == NoteSource.TRANSLATOR

        result = classify_by_schema("z", "alphabetic", {"is_lowercase": True})
        assert result == NoteSource.TRANSLATOR

    def test_alphabetic_uppercase_editor(self):
        """Alphabetic uppercase markers indicate editor notes."""
        result = classify_by_schema("A", "alphabetic", {"is_uppercase": True})
        assert result == NoteSource.EDITOR

        result = classify_by_schema("Z", "alphabetic", {"is_uppercase": True})
        assert result == NoteSource.EDITOR

    def test_numeric_author(self):
        """Numeric markers indicate author notes."""
        result = classify_by_schema("1", "numeric", {"is_superscript": True})
        assert result == NoteSource.AUTHOR

        result = classify_by_schema("42", "numeric", {"is_superscript": True})
        assert result == NoteSource.AUTHOR

    def test_symbolic_short_content_translator(self):
        """Symbolic markers with short content indicate translator notes."""
        result = classify_by_schema("*", "symbolic", {"content_length": 50})
        assert result == NoteSource.TRANSLATOR

        result = classify_by_schema("†", "symbolic", {"content_length": 100})
        assert result == NoteSource.TRANSLATOR

    def test_symbolic_long_content_editor(self):
        """Symbolic markers with long content indicate editor notes."""
        result = classify_by_schema("*", "symbolic", {"content_length": 250})
        assert result == NoteSource.EDITOR

        result = classify_by_schema("*", "symbolic", {"content_length": 500})
        assert result == NoteSource.EDITOR

    def test_roman_numerals_author(self):
        """Roman numeral markers indicate author notes (classical style)."""
        result = classify_by_schema("i", "roman", {})
        assert result == NoteSource.AUTHOR

        result = classify_by_schema("iii", "roman", {})
        assert result == NoteSource.AUTHOR

    def test_unknown_schema_type(self):
        """Unknown schema types return UNKNOWN."""
        result = classify_by_schema("?", "unknown", {})
        assert result == NoteSource.UNKNOWN


# =============================================================================
# Content Validation Tests
# =============================================================================


class TestValidateClassificationByContent:
    """Test content-based classification validation."""

    def test_short_foreign_word_translator(self):
        """Short foreign words indicate translator glosses."""
        result, conf = validate_classification_by_content(
            "aufgegeben", NoteSource.TRANSLATOR
        )
        assert result == NoteSource.TRANSLATOR
        assert conf == 0.92

    def test_multi_word_foreign_phrase_translator(self):
        """Multi-word foreign phrases (≤3 words) indicate translator glosses."""
        result, conf = validate_classification_by_content(
            "être et temps", NoteSource.TRANSLATOR
        )
        assert result == NoteSource.TRANSLATOR
        assert conf == 0.92

    def test_foreign_word_with_quotes_translator(self):
        """Foreign words with quotes are recognized."""
        result, conf = validate_classification_by_content(
            "'Dasein'", NoteSource.TRANSLATOR
        )
        assert result == NoteSource.TRANSLATOR
        assert conf == 0.92

    def test_editorial_phrase_first_edition(self):
        """Editorial phrase 'as in the first edition' indicates editor."""
        result, conf = validate_classification_by_content(
            "As in the first edition, Kant argues...", NoteSource.TRANSLATOR
        )
        assert result == NoteSource.EDITOR
        assert conf == 0.90

    def test_editorial_phrase_author_wrote(self):
        """Editorial phrase with author name indicates editor."""
        result, conf = validate_classification_by_content(
            "Heidegger wrote this in 1927", NoteSource.TRANSLATOR
        )
        assert result == NoteSource.EDITOR
        assert conf == 0.90

    def test_editorial_phrase_we_follow(self):
        """Editorial phrase 'we follow' indicates editor."""
        result, conf = validate_classification_by_content(
            "We follow the reading of the second edition", NoteSource.TRANSLATOR
        )
        assert result == NoteSource.EDITOR
        assert conf == 0.90

    def test_translation_indicator_german(self):
        """Translation indicator 'German:' indicates translator."""
        result, conf = validate_classification_by_content(
            "German: Aufhebung (sublation)", NoteSource.TRANSLATOR
        )
        assert result == NoteSource.TRANSLATOR
        assert conf == 0.88

    def test_translation_indicator_latin(self):
        """Translation indicator 'lat:' indicates translator."""
        result, conf = validate_classification_by_content(
            "lat: cogito ergo sum", NoteSource.TRANSLATOR
        )
        assert result == NoteSource.TRANSLATOR
        assert conf == 0.88

    def test_translation_indicator_literally(self):
        """Translation indicator 'literally' indicates translator."""
        result, conf = validate_classification_by_content(
            "literally: being-in-the-world", NoteSource.TRANSLATOR
        )
        assert result == NoteSource.TRANSLATOR
        assert conf == 0.88

    def test_cross_reference_keeps_preliminary(self):
        """Cross-references don't change classification."""
        result, conf = validate_classification_by_content(
            "See chapter 5 for details", NoteSource.TRANSLATOR
        )
        assert result == NoteSource.TRANSLATOR
        assert conf == 0.70

    def test_neutral_content_keeps_preliminary(self):
        """Neutral content returns preliminary classification."""
        result, conf = validate_classification_by_content(
            "This is an important point", NoteSource.TRANSLATOR
        )
        assert result == NoteSource.TRANSLATOR
        assert conf == 0.50

    def test_case_insensitive_patterns(self):
        """Pattern matching is case-insensitive."""
        result, conf = validate_classification_by_content(
            "GERMAN: DASEIN", NoteSource.TRANSLATOR
        )
        assert result == NoteSource.TRANSLATOR
        assert conf == 0.88


# =============================================================================
# Comprehensive Classification Tests
# =============================================================================


class TestClassifyNoteComprehensive:
    """Test comprehensive classification with conflict resolution."""

    def test_agreement_boosts_confidence(self):
        """Schema and content agreement boosts confidence to 0.95."""
        result = classify_note_comprehensive(
            marker="a",
            content="German: aufgegeben",
            schema_type="alphabetic",
            marker_info={"is_lowercase": True},
        )
        assert result["note_source"] == NoteSource.TRANSLATOR
        assert result["confidence"] == 0.95
        assert result["method"] == "schema+content_agreement"

    def test_content_override_editor(self):
        """Strong editorial content overrides schema."""
        result = classify_note_comprehensive(
            marker="a",
            content="As in the first edition, we follow...",
            schema_type="alphabetic",
            marker_info={"is_lowercase": True},
        )
        assert result["note_source"] == NoteSource.EDITOR
        assert result["confidence"] == 0.90
        assert result["method"] == "content_override_editor"

    def test_schema_priority_author(self):
        """Author schema has priority even with editorial content."""
        result = classify_note_comprehensive(
            marker="2",
            content="We follow the second edition here",
            schema_type="numeric",
            marker_info={"is_superscript": True},
        )
        assert result["note_source"] == NoteSource.AUTHOR
        assert result["confidence"] == 0.80
        assert result["method"] == "schema_priority_author"

    def test_schema_with_weak_content(self):
        """Schema guides classification with weak content signals."""
        result = classify_note_comprehensive(
            marker="b",
            content="Important philosophical point",
            schema_type="alphabetic",
            marker_info={"is_lowercase": True},
        )
        assert result["note_source"] == NoteSource.TRANSLATOR
        assert result["confidence"] >= 0.75
        assert result["method"] in [
            "schema+content_agreement",
            "schema_with_weak_content",
        ]

    def test_uppercase_alphabetic_editor(self):
        """Uppercase alphabetic markers indicate editor notes."""
        result = classify_note_comprehensive(
            marker="A",
            content="Editorial note about the text",
            schema_type="alphabetic",
            marker_info={"is_uppercase": True},
        )
        assert result["note_source"] == NoteSource.EDITOR

    def test_roman_numeral_author(self):
        """Roman numerals indicate author notes."""
        result = classify_note_comprehensive(
            marker="iii", content="My philosophical argument", schema_type="roman"
        )
        assert result["note_source"] == NoteSource.AUTHOR

    def test_long_symbolic_editorial(self):
        """Long symbolic notes are classified as editor."""
        content = (
            "As in the first edition, we follow Kant's original text. "
            "This passage represents an important philosophical point about "
            "the nature of categories that was omitted in later editions."
        )
        result = classify_note_comprehensive(
            marker="*",
            content=content,
            schema_type="symbolic",
            marker_info={"content_length": len(content)},
        )
        assert result["note_source"] == NoteSource.EDITOR

    def test_missing_marker_info(self):
        """Handles missing marker_info gracefully."""
        result = classify_note_comprehensive(
            marker="c", content="Translation note", schema_type="alphabetic"
        )
        assert result["note_source"] == NoteSource.TRANSLATOR
        assert "evidence" in result
        assert "confidence" in result

    def test_evidence_dictionary_complete(self):
        """Evidence dictionary contains all expected fields."""
        result = classify_note_comprehensive(
            marker="d",
            content="Latin: cogito",
            schema_type="alphabetic",
            marker_info={"is_lowercase": True},
        )
        evidence = result["evidence"]
        assert "schema_classification" in evidence
        assert "content_classification" in evidence
        assert "content_confidence" in evidence
        assert "agreement" in evidence
        assert "marker" in evidence
        assert "schema_type" in evidence
        assert "content_preview" in evidence

    def test_content_preview_truncation(self):
        """Long content is truncated in evidence preview."""
        long_content = "x" * 200
        result = classify_note_comprehensive(
            marker="e",
            content=long_content,
            schema_type="alphabetic",
            marker_info={"is_lowercase": True},
        )
        assert len(result["evidence"]["content_preview"]) == 100


# =============================================================================
# Real-World Scholarly Examples
# =============================================================================


class TestRealWorldExamples:
    """Test classification on realistic scholarly note examples."""

    def test_kant_translator_note(self):
        """Translator note from Kant's Critique."""
        result = classify_note_comprehensive(
            marker="a",
            content='German: "Verstand" (understanding)',
            schema_type="alphabetic",
            marker_info={"is_lowercase": True},
        )
        assert result["note_source"] == NoteSource.TRANSLATOR
        assert result["confidence"] == 0.95

    def test_kant_author_footnote(self):
        """Author's own footnote in Kant."""
        result = classify_note_comprehensive(
            marker="2",
            content="This distinction is crucial for understanding the synthetic a priori.",
            schema_type="numeric",
            marker_info={"is_superscript": True},
        )
        assert result["note_source"] == NoteSource.AUTHOR
        assert result["confidence"] == 0.95

    def test_heidegger_editor_note(self):
        """Editor note in Heidegger's Being and Time."""
        result = classify_note_comprehensive(
            marker="*",
            content='As in the first edition, Heidegger uses "Dasein" to refer to human existence.',
            schema_type="symbolic",
            marker_info={"content_length": 200},
        )
        assert result["note_source"] == NoteSource.EDITOR
        assert result["confidence"] >= 0.85

    def test_derrida_translator_gloss(self):
        """Translator gloss in Derrida."""
        result = classify_note_comprehensive(
            marker="b",
            content="différance",
            schema_type="alphabetic",
            marker_info={"is_lowercase": True},
        )
        assert result["note_source"] == NoteSource.TRANSLATOR
        assert result["confidence"] == 0.95

    def test_mixed_translation_reference(self):
        """Translation note with cross-reference."""
        result = classify_note_comprehensive(
            marker="c",
            content='German: "Ereignis" (event, appropriation). See also chapter 3.',
            schema_type="alphabetic",
            marker_info={"is_lowercase": True},
        )
        assert result["note_source"] == NoteSource.TRANSLATOR
        assert result["confidence"] >= 0.85


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_content(self):
        """Handles empty content gracefully."""
        result = classify_note_comprehensive(
            marker="a",
            content="",
            schema_type="alphabetic",
            marker_info={"is_lowercase": True},
        )
        assert result["note_source"] == NoteSource.TRANSLATOR
        assert result["confidence"] > 0.0

    def test_whitespace_only_content(self):
        """Handles whitespace-only content."""
        result = classify_note_comprehensive(
            marker="a",
            content="   \n\t  ",
            schema_type="alphabetic",
            marker_info={"is_lowercase": True},
        )
        assert result["note_source"] == NoteSource.TRANSLATOR

    def test_very_long_content(self):
        """Handles very long content without errors."""
        long_content = "word " * 500
        result = classify_note_comprehensive(
            marker="1",
            content=long_content,
            schema_type="numeric",
            marker_info={"is_superscript": True},
        )
        assert result["note_source"] == NoteSource.AUTHOR
        assert len(result["evidence"]["content_preview"]) <= 100

    def test_unicode_foreign_words(self):
        """Handles Unicode characters in foreign words."""
        result = classify_note_comprehensive(
            marker="a",
            content="Müller über Übermut",
            schema_type="alphabetic",
            marker_info={"is_lowercase": True},
        )
        assert result["note_source"] == NoteSource.TRANSLATOR

    def test_multiple_patterns_in_content(self):
        """Handles content with multiple classification patterns."""
        result = classify_note_comprehensive(
            marker="a",
            content="German: Dasein. As in the first edition, this term is central.",
            schema_type="alphabetic",
            marker_info={"is_lowercase": True},
        )
        # Translation indicator should be detected first
        assert result["note_source"] in [NoteSource.TRANSLATOR, NoteSource.EDITOR]
        assert result["confidence"] >= 0.85


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
