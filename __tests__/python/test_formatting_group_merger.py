"""
Tests for formatting group merger.

Verifies that consecutive spans with identical formatting are grouped
correctly before applying markdown markers, preventing malformed output.

Test Strategy:
    1. Unit tests for FormattingGroupMerger.create_groups()
    2. Unit tests for FormattingGroupMerger.apply_formatting_to_group()
    3. Integration tests for process_spans_to_markdown()
    4. Edge case tests (footnotes, whitespace, nested formats)

Run with: pytest __tests__/python/test_formatting_group_merger.py -v
"""

import pytest
from lib.formatting_group_merger import (
    FormattingGroup,
    FormattingGroupMerger,
    create_formatting_groups,
    apply_grouped_formatting,
)

pytestmark = pytest.mark.unit


class TestFormattingGroupCreation:
    """Test FormattingGroupMerger.create_groups() logic."""

    def test_single_span_no_formatting(self):
        """Single span with no formatting creates one group."""
        spans = [{"text": "Hello world", "formatting": set(), "flags": 0}]
        merger = FormattingGroupMerger()
        groups = merger.create_groups(spans)

        assert len(groups) == 1
        assert groups[0].text == "Hello world"
        assert groups[0].formatting == set()
        assert not groups[0].is_footnote

    def test_consecutive_same_formatting_merged(self):
        """Consecutive spans with same formatting are merged."""
        spans = [
            {"text": "End ", "formatting": {"bold", "italic"}, "flags": 0},
            {"text": "of ", "formatting": {"bold", "italic"}, "flags": 0},
            {"text": "Time", "formatting": {"bold", "italic"}, "flags": 0},
        ]
        merger = FormattingGroupMerger()
        groups = merger.create_groups(spans)

        assert len(groups) == 1
        assert groups[0].text == "End of Time"
        assert groups[0].formatting == {"bold", "italic"}

    def test_different_formatting_creates_separate_groups(self):
        """Different formatting creates separate groups."""
        spans = [
            {"text": "The ", "formatting": {"italic"}, "flags": 0},
            {"text": "End ", "formatting": {"bold", "italic"}, "flags": 0},
            {"text": "of ", "formatting": {"bold", "italic"}, "flags": 0},
        ]
        merger = FormattingGroupMerger()
        groups = merger.create_groups(spans)

        assert len(groups) == 2
        assert groups[0].text == "The "
        assert groups[0].formatting == {"italic"}
        assert groups[1].text == "End of "
        assert groups[1].formatting == {"bold", "italic"}

    def test_footnote_reference_creates_separate_group(self):
        """Footnote reference creates separate footnote group."""
        spans = [
            {"text": "Hello", "formatting": set(), "flags": 0},
            {"text": "1", "formatting": set(), "flags": 1},  # Superscript
            {"text": " world", "formatting": set(), "flags": 0},
        ]
        merger = FormattingGroupMerger()
        groups = merger.create_groups(spans, is_first_block=False)

        assert len(groups) == 3
        assert groups[0].text == "Hello"
        assert groups[1].is_footnote
        assert groups[1].footnote_id == "1"
        assert groups[1].text == "[^1]"  # Reference format
        assert groups[2].text == " world"

    def test_footnote_definition_at_block_start(self):
        """Footnote at block start is treated as definition."""
        spans = [
            {"text": "1", "formatting": set(), "flags": 1},  # Superscript
            {"text": ". ", "formatting": set(), "flags": 0},
            {"text": "See page 42.", "formatting": set(), "flags": 0},
        ]
        block_text = "1. See page 42."
        merger = FormattingGroupMerger()
        groups = merger.create_groups(spans, is_first_block=True, block_text=block_text)

        # First group should be footnote definition (plain "1", not "[^1]")
        assert groups[0].is_footnote
        assert groups[0].footnote_id == "1"
        assert groups[0].text == "1"  # Definition format (no [^ ])

    def test_alternating_formatting(self):
        """Alternating formatting creates multiple groups."""
        spans = [
            {"text": "bold ", "formatting": {"bold"}, "flags": 0},
            {"text": "italic ", "formatting": {"italic"}, "flags": 0},
            {"text": "bold ", "formatting": {"bold"}, "flags": 0},
            {"text": "plain", "formatting": set(), "flags": 0},
        ]
        merger = FormattingGroupMerger()
        groups = merger.create_groups(spans)

        assert len(groups) == 4
        assert groups[0].formatting == {"bold"}
        assert groups[1].formatting == {"italic"}
        assert groups[2].formatting == {"bold"}
        assert groups[3].formatting == set()

    def test_empty_spans_list(self):
        """Empty spans list returns empty groups list."""
        merger = FormattingGroupMerger()
        groups = merger.create_groups([])
        assert groups == []

    def test_letter_footnote_markers(self):
        """Letter footnote markers (a, b, c) are detected correctly."""
        spans = [
            {"text": "Text", "formatting": set(), "flags": 0},
            {"text": "a", "formatting": set(), "flags": 1},  # Letter footnote
            {"text": " more", "formatting": set(), "flags": 0},
        ]
        merger = FormattingGroupMerger()
        groups = merger.create_groups(spans, is_first_block=False)

        assert len(groups) == 3
        assert groups[1].is_footnote
        assert groups[1].footnote_id == "a"
        assert groups[1].text == "[^a]"


class TestFormattingApplication:
    """Test FormattingGroupMerger.apply_formatting_to_group() logic."""

    def test_no_formatting_returns_plain_text(self):
        """Group with no formatting returns plain text."""
        group = FormattingGroup(text="Hello world", formatting=set())
        merger = FormattingGroupMerger()
        result = merger.apply_formatting_to_group(group)
        assert result == "Hello world"

    def test_bold_formatting(self):
        """Bold formatting applies **markers**."""
        group = FormattingGroup(text="bold text", formatting={"bold"})
        merger = FormattingGroupMerger()
        result = merger.apply_formatting_to_group(group)
        assert result == "**bold text**"

    def test_italic_formatting(self):
        """Italic formatting applies *markers*."""
        group = FormattingGroup(text="italic text", formatting={"italic"})
        merger = FormattingGroupMerger()
        result = merger.apply_formatting_to_group(group)
        assert result == "*italic text*"

    def test_bold_italic_formatting(self):
        """Bold+italic formatting applies ***markers***."""
        group = FormattingGroup(text="bold italic", formatting={"bold", "italic"})
        merger = FormattingGroupMerger()
        result = merger.apply_formatting_to_group(group)
        assert result == "***bold italic***"

    def test_strikethrough_formatting(self):
        """Strikethrough formatting applies ~~markers~~."""
        group = FormattingGroup(text="deleted", formatting={"strikethrough"})
        merger = FormattingGroupMerger()
        result = merger.apply_formatting_to_group(group)
        assert result == "~~deleted~~"

    def test_whitespace_preserved_outside_markers(self):
        """Leading/trailing whitespace stays outside formatting markers."""
        group = FormattingGroup(text="  bold  ", formatting={"bold"})
        merger = FormattingGroupMerger()
        result = merger.apply_formatting_to_group(group)
        assert result == "  **bold**  "

    def test_leading_whitespace_preserved(self):
        """Leading whitespace preserved."""
        group = FormattingGroup(text="  text", formatting={"italic"})
        merger = FormattingGroupMerger()
        result = merger.apply_formatting_to_group(group)
        assert result == "  *text*"

    def test_trailing_whitespace_preserved(self):
        """Trailing whitespace preserved."""
        group = FormattingGroup(text="text  ", formatting={"italic"})
        merger = FormattingGroupMerger()
        result = merger.apply_formatting_to_group(group)
        assert result == "*text*  "

    def test_whitespace_only_unchanged(self):
        """Whitespace-only text returns unchanged."""
        group = FormattingGroup(text="   ", formatting={"bold"})
        merger = FormattingGroupMerger()
        result = merger.apply_formatting_to_group(group)
        assert result == "   "

    def test_empty_text_unchanged(self):
        """Empty text returns unchanged."""
        group = FormattingGroup(text="", formatting={"bold"})
        merger = FormattingGroupMerger()
        result = merger.apply_formatting_to_group(group)
        assert result == ""

    def test_footnote_group_returns_as_is(self):
        """Footnote groups return text as-is (already formatted)."""
        group = FormattingGroup(
            text="[^1]", formatting=set(), is_footnote=True, footnote_id="1"
        )
        merger = FormattingGroupMerger()
        result = merger.apply_formatting_to_group(group)
        assert result == "[^1]"

    def test_sous_erasure_formatting(self):
        """Sous-erasure (Derrida) applies ~~markers~~."""
        group = FormattingGroup(text="differance", formatting={"sous-erasure"})
        merger = FormattingGroupMerger()
        result = merger.apply_formatting_to_group(group)
        assert result == "~~differance~~"

    def test_underline_formatting(self):
        """Underline formatting applies <u>tags</u>."""
        group = FormattingGroup(text="underlined", formatting={"underline"})
        merger = FormattingGroupMerger()
        result = merger.apply_formatting_to_group(group)
        assert result == "<u>underlined</u>"

    def test_superscript_formatting(self):
        """Superscript formatting applies ^markers^."""
        group = FormattingGroup(text="super", formatting={"superscript"})
        merger = FormattingGroupMerger()
        result = merger.apply_formatting_to_group(group)
        assert result == "^super^"

    def test_subscript_formatting(self):
        """Subscript formatting applies ~markers~."""
        group = FormattingGroup(text="sub", formatting={"subscript"})
        merger = FormattingGroupMerger()
        result = merger.apply_formatting_to_group(group)
        assert result == "~sub~"


class TestIntegration:
    """Integration tests for full span-to-markdown conversion."""

    def test_basic_sentence_with_formatting(self):
        """Basic sentence with mixed formatting."""
        spans = [
            {"text": "The ", "formatting": {"italic"}, "flags": 0},
            {"text": "End ", "formatting": {"bold", "italic"}, "flags": 0},
            {"text": "of ", "formatting": {"bold", "italic"}, "flags": 0},
            {"text": "Time", "formatting": set(), "flags": 0},
        ]
        merger = FormattingGroupMerger()
        text, fn_id = merger.process_spans_to_markdown(spans)

        assert text == "*The* ***End of*** Time"
        assert fn_id is None

    def test_sentence_with_footnote_reference(self):
        """Sentence with footnote reference mid-sentence."""
        spans = [
            {"text": "Text", "formatting": set(), "flags": 0},
            {"text": "1", "formatting": set(), "flags": 1},  # Footnote
            {"text": " continues", "formatting": set(), "flags": 0},
        ]
        merger = FormattingGroupMerger()
        text, fn_id = merger.process_spans_to_markdown(spans, is_first_block=False)

        assert text == "Text[^1] continues"
        assert fn_id is None

    def test_footnote_definition_block(self):
        """Footnote definition at block start."""
        spans = [
            {"text": "1", "formatting": set(), "flags": 1},
            {"text": ". See page 42.", "formatting": set(), "flags": 0},
        ]
        block_text = "1. See page 42."
        merger = FormattingGroupMerger()
        text, fn_id = merger.process_spans_to_markdown(
            spans, is_first_block=True, block_text=block_text
        )

        assert text == "1. See page 42."
        assert fn_id == "1"

    def test_complex_formatting_mix(self):
        """Complex mix of formatting types."""
        spans = [
            {"text": "Regular ", "formatting": set(), "flags": 0},
            {"text": "bold ", "formatting": {"bold"}, "flags": 0},
            {"text": "and ", "formatting": {"bold"}, "flags": 0},
            {"text": "italic ", "formatting": {"italic"}, "flags": 0},
            {"text": "text", "formatting": set(), "flags": 0},
        ]
        merger = FormattingGroupMerger()
        text, fn_id = merger.process_spans_to_markdown(spans)

        assert text == "Regular **bold and** *italic* text"
        assert fn_id is None

    def test_multiple_consecutive_footnotes(self):
        """Multiple footnotes in sequence."""
        spans = [
            {"text": "Text", "formatting": set(), "flags": 0},
            {"text": "1", "formatting": set(), "flags": 1},
            {"text": "2", "formatting": set(), "flags": 1},
            {"text": " end", "formatting": set(), "flags": 0},
        ]
        merger = FormattingGroupMerger()
        text, fn_id = merger.process_spans_to_markdown(spans, is_first_block=False)

        assert text == "Text[^1][^2] end"
        assert fn_id is None

    def test_formatted_text_with_footnote(self):
        """Formatted text interrupted by footnote."""
        spans = [
            {"text": "Bold ", "formatting": {"bold"}, "flags": 0},
            {"text": "text", "formatting": {"bold"}, "flags": 0},
            {"text": "1", "formatting": set(), "flags": 1},  # Footnote breaks group
            {"text": " more ", "formatting": {"bold"}, "flags": 0},
            {"text": "bold", "formatting": {"bold"}, "flags": 0},
        ]
        merger = FormattingGroupMerger()
        text, fn_id = merger.process_spans_to_markdown(spans, is_first_block=False)

        # Footnote breaks the bold group into two separate groups
        assert text == "**Bold text**[^1] **more bold**"
        assert fn_id is None

    def test_whitespace_handling(self):
        """Whitespace preserved correctly across groups."""
        spans = [
            {"text": "  Leading ", "formatting": {"bold"}, "flags": 0},
            {"text": "bold  ", "formatting": {"bold"}, "flags": 0},
            {"text": "  trailing  ", "formatting": set(), "flags": 0},
        ]
        merger = FormattingGroupMerger()
        text, fn_id = merger.process_spans_to_markdown(spans)

        assert text == "  **Leading bold**    trailing  "
        assert fn_id is None

    def test_empty_spans_list(self):
        """Empty spans list returns empty string."""
        merger = FormattingGroupMerger()
        text, fn_id = merger.process_spans_to_markdown([])

        assert text == ""
        assert fn_id is None


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_single_character_spans(self):
        """Single character spans with formatting."""
        spans = [
            {"text": "a", "formatting": {"bold"}, "flags": 0},
            {"text": "b", "formatting": {"bold"}, "flags": 0},
            {"text": "c", "formatting": {"italic"}, "flags": 0},
        ]
        merger = FormattingGroupMerger()
        text, fn_id = merger.process_spans_to_markdown(spans)

        assert text == "**ab***c*"
        assert fn_id is None

    def test_only_whitespace_spans(self):
        """Spans containing only whitespace."""
        spans = [
            {"text": "   ", "formatting": set(), "flags": 0},
            {"text": "\t", "formatting": set(), "flags": 0},
        ]
        merger = FormattingGroupMerger()
        text, fn_id = merger.process_spans_to_markdown(spans)

        assert text == "   \t"
        assert fn_id is None

    def test_unicode_text(self):
        """Unicode text with formatting."""
        spans = [
            {"text": "différance ", "formatting": {"italic"}, "flags": 0},
            {"text": "über ", "formatting": {"bold"}, "flags": 0},
            {"text": "漢字", "formatting": {"bold"}, "flags": 0},
        ]
        merger = FormattingGroupMerger()
        text, fn_id = merger.process_spans_to_markdown(spans)

        assert text == "*différance* **über 漢字**"
        assert fn_id is None

    def test_special_markdown_characters(self):
        """Special markdown characters in text."""
        spans = [
            {"text": "Text with * and _ and ** chars", "formatting": set(), "flags": 0},
        ]
        merger = FormattingGroupMerger()
        text, fn_id = merger.process_spans_to_markdown(spans)

        # Should not double-escape - just preserve as-is
        assert text == "Text with * and _ and ** chars"
        assert fn_id is None

    def test_nested_formatting_attempt(self):
        """Attempt at nested formatting (not supported by markdown)."""
        spans = [
            {"text": "outer ", "formatting": {"bold"}, "flags": 0},
            {"text": "inner ", "formatting": {"bold", "italic"}, "flags": 0},
            {"text": "outer", "formatting": {"bold"}, "flags": 0},
        ]
        merger = FormattingGroupMerger()
        text, fn_id = merger.process_spans_to_markdown(spans)

        # Should create separate groups for different formatting
        assert text == "**outer** ***inner*** **outer**"
        assert fn_id is None


class TestConvenienceFunctions:
    """Test convenience functions for backward compatibility."""

    def test_create_formatting_groups_function(self):
        """Convenience function creates groups correctly."""
        spans = [
            {"text": "Hello ", "formatting": {"bold"}, "flags": 0},
            {"text": "world", "formatting": {"bold"}, "flags": 0},
        ]
        groups = create_formatting_groups(spans)

        assert len(groups) == 1
        assert groups[0].text == "Hello world"
        assert groups[0].formatting == {"bold"}

    def test_apply_grouped_formatting_function(self):
        """Convenience function applies formatting correctly."""
        spans = [
            {"text": "Bold ", "formatting": {"bold"}, "flags": 0},
            {"text": "text", "formatting": {"bold"}, "flags": 0},
        ]
        text, fn_id = apply_grouped_formatting(spans)

        assert text == "**Bold text**"
        assert fn_id is None


class TestPerformance:
    """Performance-related tests."""

    def test_large_number_of_spans(self):
        """Performance with large number of spans (100+)."""
        # Create 100 spans with alternating formatting
        spans = []
        for i in range(100):
            fmt = {"bold"} if i % 2 == 0 else {"italic"}
            spans.append({"text": f"word{i} ", "formatting": fmt, "flags": 0})

        merger = FormattingGroupMerger()
        groups = merger.create_groups(spans)

        # Should create 100 groups (each has different formatting)
        assert len(groups) == 100

    def test_very_long_consecutive_group(self):
        """Performance with very long consecutive group (1000 spans)."""
        # Create 1000 spans all with same formatting
        spans = [
            {"text": f"word{i} ", "formatting": {"bold"}, "flags": 0}
            for i in range(1000)
        ]

        merger = FormattingGroupMerger()
        groups = merger.create_groups(spans)

        # Should merge into single group
        assert len(groups) == 1
        assert len(groups[0].text) > 0
