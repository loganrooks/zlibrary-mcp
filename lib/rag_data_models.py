"""
Data models for RAG pipeline structured processing.

This module defines data classes for representing text with formatting metadata,
page regions with spatial and semantic information, and entities with relationships.

Design Philosophy:
    "Preserve as much information that a philosophy scholar would get from closely
    analyzing the PDF/book" - Information preservation > engineering convenience

Created: 2025-10-14 (Phase 1 of 9-week architectural refactoring)
See: claudedocs/RAG_ARCHITECTURE_REFACTORING_ONBOARDING.md

Key Design Decisions:
    1. Set[str] for formatting (human-readable, debuggable, JSON-friendly)
    2. Structured NoteInfo for footnotes vs endnotes distinction
    3. Semantic structure as first-class fields (not metadata dict)
    4. Runtime validation for data integrity
    5. Python 3.9+ compatible (no StrEnum)
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Set, Optional, List


# =============================================================================
# Constants
# =============================================================================

VALID_FORMATS: Set[str] = {
    "bold",          # Strong emphasis (flags & 16)
    "italic",        # Emphasis (flags & 2)
    "strikethrough", # Horizontal line through text (editorial deletion)
    "sous-erasure",  # X-mark/crossing - Derridean philosophical technique
    "underline",     # Line below text (text decoration)
    "superscript",   # Footnote markers (flags & 1)
    "subscript",     # Chemical formulas, mathematical notation
    "serifed",       # Font characteristic (flags & 4)
    "monospaced",    # Code blocks, technical text (flags & 8)
}


# =============================================================================
# Note Enums (for footnotes vs endnotes distinction)
# =============================================================================

class NoteType(Enum):
    """
    Type of note in scholarly texts.

    Critical distinction for philosophy texts where footnotes and endnotes
    serve different purposes and follow different formatting rules.

    Example: Heidegger's "Being and Time"
        - Footnotes: Translator notes (bottom of each page)
        - Endnotes: Heidegger's extensive citations (end of book)
    """
    FOOTNOTE = auto()    # Bottom of page, page-local numbering
    ENDNOTE = auto()     # End of chapter/book, sequential numbering
    SIDENOTE = auto()    # Margin notes (Tufte-style, rare)


class NoteRole(Enum):
    """Role within the note system."""
    REFERENCE = auto()   # In-text marker (e.g., superscript "1")
    DEFINITION = auto()  # The actual note content


class NoteScope(Enum):
    """
    Scope of note numbering and linking strategy.

    This determines how we link references to definitions:
        - PAGE: Match refs to defs within single page (footnotes)
        - CHAPTER: Match refs to defs within chapter (chapter endnotes)
        - DOCUMENT: Match refs to defs across entire book (book endnotes)
    """
    PAGE = auto()        # Footnote scope (page-local)
    CHAPTER = auto()     # Chapter-level endnotes
    DOCUMENT = auto()    # Document-level endnotes


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class NoteInfo:
    """
    Structured information about footnotes/endnotes.

    Philosophy: Footnotes vs endnotes are semantically different in scholarly
    texts. They have different locations, numbering schemes, and linking
    strategies. This structure preserves those distinctions.

    Attributes:
        note_type: FOOTNOTE (bottom of page) vs ENDNOTE (end section)
        role: REFERENCE (in-text marker) vs DEFINITION (note content)
        marker: The note identifier ("1", "23", "a", "†", "*")
        scope: Linking scope (PAGE, CHAPTER, DOCUMENT)
        chapter_number: For endnotes, which chapter they belong to
        section_title: e.g., "Notes to Chapter 3"
        is_continued: True if note continues on next page
        continued_from: Marker of previous part if multi-page note

    Example Usage:
        # Footnote reference in text
        footnote_ref = NoteInfo(
            note_type=NoteType.FOOTNOTE,
            role=NoteRole.REFERENCE,
            marker="1",
            scope=NoteScope.PAGE
        )

        # Endnote definition in notes section
        endnote_def = NoteInfo(
            note_type=NoteType.ENDNOTE,
            role=NoteRole.DEFINITION,
            marker="23",
            scope=NoteScope.CHAPTER,
            chapter_number=3,
            section_title="Notes to Chapter 3"
        )
    """
    note_type: NoteType
    role: NoteRole
    marker: str  # "1", "23", "a", "†", "*", etc.
    scope: NoteScope

    # For endnotes: chapter/section context
    chapter_number: Optional[int] = None
    section_title: Optional[str] = None

    # For multi-page notes (rare but exists)
    is_continued: bool = False
    continued_from: Optional[str] = None


@dataclass
class ListInfo:
    """
    Structured list information (first-class semantic property).

    Philosophy: For scholarly work, list structure IS semantic information
    (enumerated arguments, logical sequences), not just formatting metadata.

    Attributes:
        is_list_item: True if this region is a list item
        list_type: 'ul' (unordered) or 'ol' (ordered)
        marker: The actual marker text ('*', '1', 'a', '†', etc.)
        indent_level: Nesting depth (0 = top-level, 1 = nested, etc.)

    Example:
        # Ordered list item
        ListInfo(
            is_list_item=True,
            list_type='ol',
            marker='1',
            indent_level=0
        )
    """
    is_list_item: bool
    list_type: str  # 'ul' or 'ol'
    marker: str     # '*', '1', 'a', etc.
    indent_level: int = 0  # For nested lists (Phase 6)


@dataclass
class TextSpan:
    """
    A continuous run of text with consistent formatting properties.

    Philosophy: Preserve ALL information a scholar analyzing Derrida or
    Heidegger would need, including sous rature (strikethrough).

    A span is the smallest unit of text with uniform formatting. PyMuPDF
    creates separate spans when formatting changes.

    Example: "The **bold** word" creates 3 TextSpan objects:
        TextSpan("The ", formatting=set())
        TextSpan("bold", formatting={"bold"})
        TextSpan(" word", formatting=set())

    Attributes:
        text: The text content
        formatting: Set of formatting types (see VALID_FORMATS)
        font_size: Font size in points (for heading detection)
        font_name: Font family (changes may indicate voice shifts)
        bbox: Bounding box (x0, y0, x1, y1) in page coordinates

    Design Decision: Set[str] instead of boolean fields
        - Human-readable: {"bold", "italic"} vs is_bold=True, is_italic=True
        - Debuggable: Instantly clear when debugging Derrida PDFs
        - Compact: 1 field vs 8+ boolean fields
        - Fast: O(1) membership test ("bold" in span.formatting)
        - JSON-friendly: list(formatting) → ["bold", "italic"]
        - Extensible: Easy to add "small-caps" later

    PyMuPDF Flag Mappings (CORRECTED - current code has bug):
        flags & 16 (bit 4) = bold (NOT bit 1!)
        flags & 2  (bit 1) = italic (NOT bit 2!)
        flags & 1  (bit 0) = superscript
        flags & 8  (bit 3) = monospaced
        flags & 4  (bit 2) = serifed
    """
    text: str
    formatting: Set[str] = field(default_factory=set)
    font_size: float = 10.0
    font_name: str = ""
    bbox: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)

    def __post_init__(self):
        """Validate formatting values at runtime."""
        invalid = self.formatting - VALID_FORMATS
        if invalid:
            raise ValueError(
                f"Invalid formatting types: {invalid}. "
                f"Valid types are: {sorted(VALID_FORMATS)}"
            )

    def has_format(self, format_type: str) -> bool:
        """
        Check if span has a specific format.

        Example:
            if span.has_format("bold"):
                markdown = f"**{span.text}**"
        """
        return format_type in self.formatting

    def to_markdown(self) -> str:
        """
        Convert span to markdown with formatting.

        Handles multiple formats correctly:
            - Bold: **text**
            - Italic: *text*
            - Bold+Italic: ***text***
            - Strikethrough: ~~text~~ (Derrida's sous rature!)
            - Superscript: ^text^
            - Subscript: ~text~

        Returns:
            Formatted markdown string
        """
        text = self.text

        # Handle bold + italic together (must check before individual)
        if "bold" in self.formatting and "italic" in self.formatting:
            text = f"***{text}***"
        elif "bold" in self.formatting:
            text = f"**{text}**"
        elif "italic" in self.formatting:
            text = f"*{text}*"

        # Other formatting (can combine with bold/italic)
        if "strikethrough" in self.formatting:
            text = f"~~{text}~~"
        if "underline" in self.formatting:
            # Markdown doesn't have native underline, use HTML
            text = f"<u>{text}</u>"
        if "superscript" in self.formatting:
            text = f"^{text}^"
        if "subscript" in self.formatting:
            text = f"~{text}~"

        return text


@dataclass
class PageRegion:
    """
    A semantically meaningful region of a page.

    Philosophy: Structural information (headings, lists) is first-class,
    not secondary "metadata". For scholarly work, these ARE the structure.

    Design Decision: Semantic properties as first-class fields
        - heading_level: Optional[int] - NOT buried in metadata dict
        - list_info: Optional[ListInfo] - explicit list structure

        Why? For philosophy texts, "this is a heading" IS structural
        information that scholars need. Making it explicit:
            - Signals importance to future developers
            - Enables type checking (Optional[int] vs dict lookup)
            - Self-documenting code
            - Aligns with principle: "preserve information scholars need"

    Attributes:
        region_type: Classification ('header', 'body', 'footer', 'margin', 'footnote')
        spans: List of TextSpan objects (formatted text fragments)
        bbox: Bounding box (x0, y0, x1, y1) in page coordinates
        page_num: Page number (1-indexed), defaults to 0 in Phase 1
        heading_level: Argumentative organization (0=not heading, 1-6=H1-H6)
        list_info: Enumerated logic structure if this is a list item

    Example:
        # Heading region
        PageRegion(
            region_type='body',
            spans=[TextSpan("Introduction", formatting={"bold"})],
            bbox=(50, 100, 500, 120),
            page_num=5,
            heading_level=2  # H2 heading
        )

        # List item region
        PageRegion(
            region_type='body',
            spans=[TextSpan("First argument...")],
            bbox=(50, 200, 500, 220),
            page_num=5,
            list_info=ListInfo(
                is_list_item=True,
                list_type='ol',
                marker='1',
                indent_level=0
            )
        )
    """
    region_type: str  # 'header', 'body', 'footer', 'margin', 'footnote'
    spans: List[TextSpan] = field(default_factory=list)
    bbox: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    page_num: int = 0  # Default 0 in Phase 1, properly set in Phase 2+

    # Semantic structure (FIRST-CLASS, not metadata)
    heading_level: Optional[int] = None  # 0=not heading, 1-6=H1-H6
    list_info: Optional[ListInfo] = None  # List structure if applicable

    def get_text(self) -> str:
        """Get plain text from all spans."""
        return ''.join(span.text for span in self.spans)

    def get_markdown(self) -> str:
        """Get markdown text with all formatting applied."""
        return ''.join(span.to_markdown() for span in self.spans)

    def is_heading(self) -> bool:
        """Check if this region is a heading."""
        return self.heading_level is not None and self.heading_level > 0

    def is_list_item(self) -> bool:
        """Check if this region is a list item."""
        return self.list_info is not None and self.list_info.is_list_item


@dataclass
class Entity:
    """
    Document entity with relationships (Phase 4 linking).

    Philosophy: Entities represent semantic units that can be linked:
        - Footnote references ↔ definitions
        - Endnote references ↔ definitions
        - Citations ↔ bibliography entries
        - Block quotes ↔ sources

    Attributes:
        entity_type: Type of entity ('note', 'heading', 'citation', 'quote')
        content: Text content of the entity
        id: Unique identifier for linking (e.g., 'fn_page5_1', 'en_ch3_23')
        note_info: Structured note information (for notes only)
        position: PageRegion where entity is located (spatial context)
        metadata: Flexible dict for entity-specific data

    Example:
        # Footnote reference in text
        Entity(
            entity_type='note',
            content='1',  # The superscript number
            id='fn_page5_1',
            note_info=NoteInfo(
                note_type=NoteType.FOOTNOTE,
                role=NoteRole.REFERENCE,
                marker='1',
                scope=NoteScope.PAGE
            ),
            position=body_region
        )

        # Footnote definition at bottom
        Entity(
            entity_type='note',
            content='See Heidegger, Being and Time, p. 42.',
            id='fn_page5_1',  # Same ID for linking!
            note_info=NoteInfo(
                note_type=NoteType.FOOTNOTE,
                role=NoteRole.DEFINITION,
                marker='1',
                scope=NoteScope.PAGE
            ),
            position=footnote_region
        )
    """
    entity_type: str  # 'note', 'heading', 'citation', 'quote', 'block_quote'
    content: str
    id: Optional[str] = None
    note_info: Optional[NoteInfo] = None  # For notes only (Phase 4)
    position: Optional[PageRegion] = None
    metadata: dict = field(default_factory=dict)

    def is_note(self) -> bool:
        """Check if this entity is a note."""
        return self.entity_type == 'note' and self.note_info is not None

    def is_footnote(self) -> bool:
        """Check if this is specifically a footnote."""
        return (self.is_note() and
                self.note_info.note_type == NoteType.FOOTNOTE)

    def is_endnote(self) -> bool:
        """Check if this is specifically an endnote."""
        return (self.is_note() and
                self.note_info.note_type == NoteType.ENDNOTE)


# =============================================================================
# Utility Functions
# =============================================================================

def create_text_span_from_pymupdf(pymupdf_span: dict) -> TextSpan:
    """
    Create TextSpan from PyMuPDF span dict.

    CRITICAL: Uses CORRECTED flag mappings (current code has bug):
        - Bold: flags & 16 (bit 4) - NOT bit 1!
        - Italic: flags & 2 (bit 1) - NOT bit 2!
        - Superscript: flags & 1 (bit 0)
        - Monospaced: flags & 8 (bit 3)
        - Serifed: flags & 4 (bit 2)

    Args:
        pymupdf_span: Dict from PyMuPDF page.get_text("dict")

    Returns:
        TextSpan with formatting extracted from flags

    Example:
        span_dict = {
            'text': 'différance',
            'size': 12.0,
            'font': 'TimesNewRoman',
            'flags': 2,  # Italic
            'bbox': (100.0, 200.0, 150.0, 212.0)
        }
        text_span = create_text_span_from_pymupdf(span_dict)
        # text_span.formatting == {"italic"}
    """
    flags = pymupdf_span.get('flags', 0)
    formatting = set()

    # CORRECTED flag mappings (fixes current code bug)
    if flags & 16: formatting.add("bold")       # Bit 4
    if flags & 2:  formatting.add("italic")     # Bit 1
    if flags & 1:  formatting.add("superscript") # Bit 0
    if flags & 8:  formatting.add("monospaced")  # Bit 3
    if flags & 4:  formatting.add("serifed")     # Bit 2

    return TextSpan(
        text=pymupdf_span.get('text', ''),
        formatting=formatting,
        font_size=pymupdf_span.get('size', 10.0),
        font_name=pymupdf_span.get('font', ''),
        bbox=tuple(pymupdf_span.get('bbox', (0.0, 0.0, 0.0, 0.0)))
    )


__all__ = [
    # Constants
    'VALID_FORMATS',
    # Enums
    'NoteType',
    'NoteRole',
    'NoteScope',
    # Data classes
    'NoteInfo',
    'ListInfo',
    'TextSpan',
    'PageRegion',
    'Entity',
    # Utility functions
    'create_text_span_from_pymupdf',
]
