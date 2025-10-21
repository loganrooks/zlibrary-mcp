"""
Formatting Group Merger for RAG Pipeline.

This module provides production-ready span grouping logic to prevent malformed
markdown from per-word formatting. Groups consecutive spans with identical
formatting before applying markdown markers.

Problem Solved:
    PyMuPDF creates separate spans per word with formatting flags:
        [TextSpan("The ", {'italic'}), TextSpan("End ", {'bold', 'italic'})]

    Naive approach creates: "*The* ***End***" (wrong - separate markers)
    This module creates: "*The* ***End***" (correct - grouped formatting)

Design Philosophy:
    1. Group consecutive spans with identical formatting sets
    2. Apply formatting once per group (not per span)
    3. Preserve footnote detection (needs plain text for isdigit() checks)
    4. Handle edge cases: footnotes, whitespace, nested formats

Created: 2025-10-21 (Phase 2 RAG quality improvements)
Author: Production Python Expert
"""

from dataclasses import dataclass
from typing import List, Set, Tuple, Optional
import logging


@dataclass
class FormattingGroup:
    """
    A group of consecutive spans with identical formatting.

    Attributes:
        text: Combined text from all spans in group
        formatting: Shared formatting set for this group
        is_footnote: True if this group is a footnote marker
        footnote_id: Footnote marker if is_footnote=True
    """
    text: str
    formatting: Set[str]
    is_footnote: bool = False
    footnote_id: Optional[str] = None

    def __repr__(self) -> str:
        """Debug representation."""
        fmt_str = ','.join(sorted(self.formatting)) if self.formatting else 'none'
        if self.is_footnote:
            return f"FormattingGroup(footnote=[^{self.footnote_id}])"
        return f"FormattingGroup(text={self.text!r}, fmt={fmt_str})"


class FormattingGroupMerger:
    """
    Merges consecutive spans with identical formatting into groups.

    Strategy:
        1. Detect footnotes first (need plain text for isdigit() checks)
        2. Group consecutive non-footnote spans by formatting
        3. Apply formatting to groups (not individual spans)
        4. Preserve footnote markers at exact positions

    Example:
        spans = [
            {'text': 'The ', 'formatting': {'italic'}, 'flags': 0},
            {'text': 'End ', 'formatting': {'bold', 'italic'}, 'flags': 0},
            {'text': 'of ', 'formatting': {'bold', 'italic'}, 'flags': 0},
            {'text': '1', 'formatting': set(), 'flags': 1},  # Footnote
            {'text': ' Time', 'formatting': set(), 'flags': 0},
        ]

        merger = FormattingGroupMerger()
        groups = merger.create_groups(spans, is_first_block=False)
        # Returns:
        # [
        #     FormattingGroup(text='The ', formatting={'italic'}),
        #     FormattingGroup(text='End of ', formatting={'bold', 'italic'}),
        #     FormattingGroup(is_footnote=True, footnote_id='1'),
        #     FormattingGroup(text=' Time', formatting=set()),
        # ]
    """

    def __init__(self):
        """Initialize merger with logging."""
        self.logger = logging.getLogger(__name__)

    def create_groups(
        self,
        spans: List[dict],
        is_first_block: bool = False,
        block_text: str = ""
    ) -> List[FormattingGroup]:
        """
        Group consecutive spans with identical formatting.

        Args:
            spans: List of PyMuPDF span dicts with 'text', 'flags', 'formatting'
            is_first_block: True if this is first span in text block
            block_text: Full block text (for footnote definition detection)

        Returns:
            List of FormattingGroup objects ready for markdown conversion

        Algorithm:
            1. Iterate through spans
            2. Detect footnote markers (superscript + isdigit/isalpha)
            3. For regular text: check if formatting matches current group
            4. If match: append to current group
            5. If no match: finalize current group, start new group

        Performance:
            - O(n) single pass through spans
            - O(1) formatting comparison (set equality)
            - Minimal memory (groups created on-the-fly)
        """
        if not spans:
            return []

        groups: List[FormattingGroup] = []
        current_group_text: str = ""
        current_group_formatting: Optional[Set[str]] = None
        first_span_in_block = is_first_block

        for span in spans:
            span_text = span.get('text', '')
            flags = span.get('flags', 0)
            formatting = span.get('formatting', set())
            is_superscript = bool(flags & 1)

            # Detect footnote markers (needs plain text - no formatting applied yet)
            is_footnote_marker = (
                span_text.isdigit() or
                (len(span_text) == 1 and span_text.isalpha() and span_text.islower())
            )

            if is_superscript and is_footnote_marker:
                # Finalize current group before adding footnote
                if current_group_text:
                    groups.append(FormattingGroup(
                        text=current_group_text,
                        formatting=current_group_formatting or set()
                    ))
                    current_group_text = ""
                    current_group_formatting = None

                # Determine if this is definition (at block start) or reference
                footnote_id = span_text
                is_definition = (
                    first_span_in_block and
                    block_text and
                    block_text.lstrip().startswith(footnote_id)
                )

                # Add footnote group
                groups.append(FormattingGroup(
                    text=footnote_id if is_definition else f"[^{footnote_id}]",
                    formatting=set(),
                    is_footnote=True,
                    footnote_id=footnote_id
                ))

            else:
                # Regular text - check if we can merge with current group
                # Formatting sets are equal if they have same elements
                can_merge = (
                    current_group_formatting is not None and
                    formatting == current_group_formatting
                )

                if can_merge:
                    # Same formatting - append to current group
                    current_group_text += span_text
                else:
                    # Different formatting - finalize current group
                    if current_group_text:
                        groups.append(FormattingGroup(
                            text=current_group_text,
                            formatting=current_group_formatting or set()
                        ))

                    # Start new group
                    current_group_text = span_text
                    current_group_formatting = formatting

            first_span_in_block = False

        # Finalize last group
        if current_group_text:
            groups.append(FormattingGroup(
                text=current_group_text,
                formatting=current_group_formatting or set()
            ))

        self.logger.debug(
            f"Created {len(groups)} formatting groups from {len(spans)} spans"
        )
        return groups

    def apply_formatting_to_group(self, group: FormattingGroup) -> str:
        """
        Apply markdown formatting to a FormattingGroup.

        Args:
            group: FormattingGroup with text and formatting set

        Returns:
            Markdown-formatted text string

        Strategy:
            1. Footnotes: return as-is (already formatted)
            2. Empty formatting: return plain text
            3. Strip whitespace → Apply formatting → Restore whitespace
            4. Handle nested formats correctly (bold+italic = ***text***)

        Edge Cases:
            - Whitespace-only text: return as-is
            - Leading/trailing whitespace: preserve outside markers
            - Bold+italic: combine markers correctly
            - Multiple formats: apply in correct order
        """
        # Footnotes already formatted
        if group.is_footnote:
            return group.text

        # No formatting
        if not group.formatting:
            return group.text

        text = group.text

        # Handle empty or whitespace-only
        if not text or not text.strip():
            return text

        # Preserve leading/trailing whitespace (critical for correct markdown)
        leading_space = text[:len(text) - len(text.lstrip())]
        trailing_space = text[len(text.rstrip()):]
        text_stripped = text.strip()

        # Apply formatting to stripped text only
        formatted = text_stripped

        # Handle bold + italic together (must check before individual)
        # This prevents ***text*** being turned into ****text**** (wrong)
        if "bold" in group.formatting and "italic" in group.formatting:
            formatted = f"***{formatted}***"
        elif "bold" in group.formatting:
            formatted = f"**{formatted}**"
        elif "italic" in group.formatting:
            formatted = f"*{formatted}*"

        # Other formatting (can combine with bold/italic)
        if "strikethrough" in group.formatting:
            formatted = f"~~{formatted}~~"
        if "sous-erasure" in group.formatting and "strikethrough" not in group.formatting:
            # Derrida's sous rature (philosophical technique)
            formatted = f"~~{formatted}~~"
        if "underline" in group.formatting:
            # Markdown doesn't have native underline, use HTML
            formatted = f"<u>{formatted}</u>"
        if "superscript" in group.formatting:
            formatted = f"^{formatted}^"
        if "subscript" in group.formatting:
            formatted = f"~{formatted}~"

        # Restore whitespace OUTSIDE formatting markers
        # This ensures: "**word** " not "**word **" (malformed)
        return leading_space + formatted + trailing_space

    def process_spans_to_markdown(
        self,
        spans: List[dict],
        is_first_block: bool = False,
        block_text: str = ""
    ) -> Tuple[str, Optional[str]]:
        """
        High-level API: Convert spans to formatted markdown text.

        Args:
            spans: List of PyMuPDF span dicts
            is_first_block: True if first span in text block
            block_text: Full block text (for footnote definition detection)

        Returns:
            Tuple of (formatted_text, potential_footnote_def_id)
            - formatted_text: Markdown with proper formatting groups
            - potential_footnote_def_id: Footnote ID if this is a definition block

        Example:
            spans = [
                {'text': 'The ', 'formatting': {'italic'}, 'flags': 0},
                {'text': 'End ', 'formatting': {'bold', 'italic'}, 'flags': 0},
                {'text': 'of ', 'formatting': {'bold', 'italic'}, 'flags': 0},
                {'text': '1', 'formatting': set(), 'flags': 1},
            ]

            text, fn_id = merger.process_spans_to_markdown(spans)
            # text = "*The* ***End of***[^1]"
            # fn_id = None (not a definition)
        """
        groups = self.create_groups(spans, is_first_block, block_text)

        # Apply formatting to each group
        formatted_parts = []
        potential_def_id = None

        for i, group in enumerate(groups):
            formatted_text = self.apply_formatting_to_group(group)
            formatted_parts.append(formatted_text)

            # Check if first group is a footnote definition
            if i == 0 and group.is_footnote and is_first_block:
                potential_def_id = group.footnote_id

        # Join and clean up spacing
        result = ''.join(formatted_parts)

        return result, potential_def_id


# Convenience functions for backward compatibility
def create_formatting_groups(
    spans: List[dict],
    is_first_block: bool = False,
    block_text: str = ""
) -> List[FormattingGroup]:
    """
    Convenience function to create formatting groups.

    Args:
        spans: List of PyMuPDF span dicts
        is_first_block: True if first span in text block
        block_text: Full block text

    Returns:
        List of FormattingGroup objects
    """
    merger = FormattingGroupMerger()
    return merger.create_groups(spans, is_first_block, block_text)


def apply_grouped_formatting(
    spans: List[dict],
    is_first_block: bool = False,
    block_text: str = ""
) -> Tuple[str, Optional[str]]:
    """
    Convenience function to apply grouped formatting.

    Args:
        spans: List of PyMuPDF span dicts
        is_first_block: True if first span in text block
        block_text: Full block text

    Returns:
        Tuple of (formatted_text, potential_footnote_def_id)
    """
    merger = FormattingGroupMerger()
    return merger.process_spans_to_markdown(spans, is_first_block, block_text)


__all__ = [
    'FormattingGroup',
    'FormattingGroupMerger',
    'create_formatting_groups',
    'apply_grouped_formatting',
]
