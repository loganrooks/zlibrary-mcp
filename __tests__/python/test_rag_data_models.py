"""
Unit tests for RAG data models.

Tests the Phase 1 data model foundation:
    - TextSpan with Set[str] formatting and validation
    - PageRegion with semantic structure
    - Entity with NoteInfo support
    - Enums for note types

Created: 2025-10-14
"""

import pytest
from lib.rag_data_models import (
    # Constants
    VALID_FORMATS,
    # Enums
    NoteType,
    NoteRole,
    NoteScope,
    # Data classes
    NoteInfo,
    ListInfo,
    TextSpan,
    PageRegion,
    Entity,
    # Utility
    create_text_span_from_pymupdf,
)

pytestmark = pytest.mark.unit


class TestValidFormats:
    """Test VALID_FORMATS constant."""

    def test_valid_formats_is_set(self):
        """VALID_FORMATS should be a set for O(1) membership tests."""
        assert isinstance(VALID_FORMATS, set)

    def test_valid_formats_contains_expected(self):
        """VALID_FORMATS should contain all expected formatting types."""
        expected = {
            "bold",
            "italic",
            "strikethrough",
            "sous-erasure",
            "underline",
            "superscript",
            "subscript",
            "serifed",
            "monospaced",
        }
        assert VALID_FORMATS == expected

    def test_valid_formats_membership(self):
        """Test fast membership checks."""
        assert "bold" in VALID_FORMATS
        assert "italic" in VALID_FORMATS
        assert "strikethrough" in VALID_FORMATS  # Horizontal line (editorial)
        assert "sous-erasure" in VALID_FORMATS  # X-mark (Derridean technique)
        assert "invalid_format" not in VALID_FORMATS


class TestNoteEnums:
    """Test note-related enums."""

    def test_note_type_values(self):
        """Test NoteType enum values."""
        assert NoteType.FOOTNOTE
        assert NoteType.ENDNOTE
        assert NoteType.SIDENOTE

    def test_note_role_values(self):
        """Test NoteRole enum values."""
        assert NoteRole.REFERENCE
        assert NoteRole.DEFINITION

    def test_note_scope_values(self):
        """Test NoteScope enum values."""
        assert NoteScope.PAGE
        assert NoteScope.CHAPTER
        assert NoteScope.DOCUMENT

    def test_enum_comparison(self):
        """Enums should be comparable by identity."""
        assert NoteType.FOOTNOTE == NoteType.FOOTNOTE
        assert NoteType.FOOTNOTE != NoteType.ENDNOTE


class TestNoteInfo:
    """Test NoteInfo dataclass."""

    def test_footnote_reference_creation(self):
        """Test creating a footnote reference."""
        note_info = NoteInfo(
            note_type=NoteType.FOOTNOTE,
            role=NoteRole.REFERENCE,
            marker="1",
            scope=NoteScope.PAGE,
        )

        assert note_info.note_type == NoteType.FOOTNOTE
        assert note_info.role == NoteRole.REFERENCE
        assert note_info.marker == "1"
        assert note_info.scope == NoteScope.PAGE
        assert note_info.chapter_number is None
        assert not note_info.is_continued

    def test_endnote_definition_creation(self):
        """Test creating an endnote definition with chapter context."""
        note_info = NoteInfo(
            note_type=NoteType.ENDNOTE,
            role=NoteRole.DEFINITION,
            marker="23",
            scope=NoteScope.CHAPTER,
            chapter_number=3,
            section_title="Notes to Chapter 3",
        )

        assert note_info.note_type == NoteType.ENDNOTE
        assert note_info.role == NoteRole.DEFINITION
        assert note_info.marker == "23"
        assert note_info.scope == NoteScope.CHAPTER
        assert note_info.chapter_number == 3
        assert note_info.section_title == "Notes to Chapter 3"

    def test_continued_note(self):
        """Test multi-page note tracking."""
        note_info = NoteInfo(
            note_type=NoteType.FOOTNOTE,
            role=NoteRole.DEFINITION,
            marker="1",
            scope=NoteScope.PAGE,
            is_continued=True,
            continued_from="1",
        )

        assert note_info.is_continued
        assert note_info.continued_from == "1"


class TestListInfo:
    """Test ListInfo dataclass."""

    def test_ordered_list_creation(self):
        """Test creating ordered list info."""
        list_info = ListInfo(
            is_list_item=True, list_type="ol", marker="1", indent_level=0
        )

        assert list_info.is_list_item
        assert list_info.list_type == "ol"
        assert list_info.marker == "1"
        assert list_info.indent_level == 0

    def test_unordered_list_creation(self):
        """Test creating unordered list info."""
        list_info = ListInfo(
            is_list_item=True, list_type="ul", marker="*", indent_level=0
        )

        assert list_info.is_list_item
        assert list_info.list_type == "ul"
        assert list_info.marker == "*"

    def test_nested_list(self):
        """Test nested list with indent level."""
        list_info = ListInfo(
            is_list_item=True, list_type="ul", marker="*", indent_level=2
        )

        assert list_info.indent_level == 2


class TestTextSpan:
    """Test TextSpan dataclass."""

    def test_simple_text_span(self):
        """Test creating a simple text span without formatting."""
        span = TextSpan(
            text="example text",
            formatting=set(),
            font_size=12.0,
            font_name="Arial",
            bbox=(10.0, 20.0, 100.0, 32.0),
        )

        assert span.text == "example text"
        assert span.formatting == set()
        assert span.font_size == 12.0
        assert span.font_name == "Arial"
        assert span.bbox == (10.0, 20.0, 100.0, 32.0)

    def test_bold_text_span(self):
        """Test text span with bold formatting."""
        span = TextSpan(
            text="bold text",
            formatting={"bold"},
            font_size=12.0,
            font_name="Arial-Bold",
        )

        assert "bold" in span.formatting
        assert span.has_format("bold")
        assert not span.has_format("italic")

    def test_multiple_formats(self):
        """Test text span with multiple formats."""
        span = TextSpan(text="emphasis", formatting={"bold", "italic"}, font_size=12.0)

        assert "bold" in span.formatting
        assert "italic" in span.formatting
        assert span.has_format("bold")
        assert span.has_format("italic")

    def test_derrida_sous_rature(self):
        """Test sous-erasure (X-mark) for Derrida's philosophical technique."""
        span = TextSpan(text="Being", formatting={"sous-erasure"}, font_size=12.0)

        assert "sous-erasure" in span.formatting
        assert span.has_format("sous-erasure")

    def test_regular_strikethrough(self):
        """Test regular strikethrough (horizontal line) for editorial deletion."""
        span = TextSpan(
            text="deleted text", formatting={"strikethrough"}, font_size=12.0
        )

        assert "strikethrough" in span.formatting
        assert span.has_format("strikethrough")
        assert "sous-erasure" not in span.formatting  # These are distinct

    def test_validation_rejects_invalid_format(self):
        """Test that invalid formatting types raise ValueError."""
        with pytest.raises(ValueError, match="Invalid formatting types"):
            TextSpan(
                text="invalid",
                formatting={"blod", "itlalic"},  # Typos!
                font_size=12.0,
            )

    def test_validation_allows_valid_formats(self):
        """Test that all valid formats are accepted."""
        # Should not raise
        span = TextSpan(
            text="all formats", formatting=VALID_FORMATS.copy(), font_size=12.0
        )

        assert span.formatting == VALID_FORMATS

    def test_default_factory(self):
        """Test that formatting defaults to empty set."""
        span = TextSpan(text="plain", font_size=10.0)

        assert span.formatting == set()
        assert not span.has_format("bold")

    def test_to_markdown_bold(self):
        """Test markdown conversion for bold text."""
        span = TextSpan(text="bold", formatting={"bold"})
        assert span.to_markdown() == "**bold**"

    def test_to_markdown_italic(self):
        """Test markdown conversion for italic text."""
        span = TextSpan(text="italic", formatting={"italic"})
        assert span.to_markdown() == "*italic*"

    def test_to_markdown_bold_and_italic(self):
        """Test markdown conversion for bold+italic."""
        span = TextSpan(text="both", formatting={"bold", "italic"})
        assert span.to_markdown() == "***both***"

    def test_to_markdown_strikethrough(self):
        """Test markdown conversion for strikethrough."""
        span = TextSpan(text="crossed", formatting={"strikethrough"})
        assert span.to_markdown() == "~~crossed~~"

    def test_to_markdown_superscript(self):
        """Test markdown conversion for superscript (footnotes)."""
        span = TextSpan(text="1", formatting={"superscript"})
        assert span.to_markdown() == "^1^"

    def test_to_markdown_plain(self):
        """Test markdown conversion for plain text."""
        span = TextSpan(text="plain")
        assert span.to_markdown() == "plain"


class TestPageRegion:
    """Test PageRegion dataclass."""

    def test_simple_body_region(self):
        """Test creating a simple body region."""
        span = TextSpan(text="body text", font_size=10.0)
        region = PageRegion(
            region_type="body",
            spans=[span],
            bbox=(50.0, 100.0, 500.0, 700.0),
            page_num=1,
        )

        assert region.region_type == "body"
        assert len(region.spans) == 1
        assert region.bbox == (50.0, 100.0, 500.0, 700.0)
        assert region.page_num == 1
        assert region.heading_level is None
        assert region.list_info is None

    def test_heading_region(self):
        """Test region with heading level (first-class field)."""
        span = TextSpan(text="Introduction", formatting={"bold"}, font_size=14.0)
        region = PageRegion(
            region_type="body",
            spans=[span],
            bbox=(50.0, 100.0, 500.0, 120.0),
            page_num=5,
            heading_level=2,  # H2
        )

        assert region.heading_level == 2
        assert region.is_heading()

    def test_list_region(self):
        """Test region with list info (first-class field)."""
        span = TextSpan(text="First point", font_size=10.0)
        list_info = ListInfo(
            is_list_item=True, list_type="ol", marker="1", indent_level=0
        )
        region = PageRegion(
            region_type="body",
            spans=[span],
            bbox=(50.0, 200.0, 500.0, 220.0),
            page_num=5,
            list_info=list_info,
        )

        assert region.list_info is not None
        assert region.list_info.marker == "1"
        assert region.is_list_item()

    def test_get_text(self):
        """Test getting plain text from region."""
        spans = [
            TextSpan(text="Hello ", formatting=set()),
            TextSpan(text="world", formatting={"bold"}),
            TextSpan(text="!", formatting=set()),
        ]
        region = PageRegion(region_type="body", spans=spans)

        assert region.get_text() == "Hello world!"

    def test_get_markdown(self):
        """Test getting markdown from region with formatting."""
        spans = [
            TextSpan(text="The ", formatting=set()),
            TextSpan(text="bold", formatting={"bold"}),
            TextSpan(text=" word.", formatting=set()),
        ]
        region = PageRegion(region_type="body", spans=spans)

        assert region.get_markdown() == "The **bold** word."

    def test_default_page_num(self):
        """Test that page_num defaults to 0 in Phase 1."""
        region = PageRegion(region_type="body")
        assert region.page_num == 0


class TestEntity:
    """Test Entity dataclass."""

    def test_simple_entity(self):
        """Test creating a simple entity."""
        entity = Entity(entity_type="heading", content="Chapter 1", id="h_ch1")

        assert entity.entity_type == "heading"
        assert entity.content == "Chapter 1"
        assert entity.id == "h_ch1"
        assert entity.note_info is None
        assert not entity.is_note()

    def test_footnote_reference(self):
        """Test footnote reference entity."""
        note_info = NoteInfo(
            note_type=NoteType.FOOTNOTE,
            role=NoteRole.REFERENCE,
            marker="1",
            scope=NoteScope.PAGE,
        )
        entity = Entity(
            entity_type="note", content="1", id="fn_page5_1", note_info=note_info
        )

        assert entity.is_note()
        assert entity.is_footnote()
        assert not entity.is_endnote()
        assert entity.note_info.marker == "1"

    def test_endnote_definition(self):
        """Test endnote definition entity."""
        note_info = NoteInfo(
            note_type=NoteType.ENDNOTE,
            role=NoteRole.DEFINITION,
            marker="23",
            scope=NoteScope.CHAPTER,
            chapter_number=3,
        )
        entity = Entity(
            entity_type="note",
            content="See Heidegger, Being and Time, p. 42.",
            id="en_ch3_23",
            note_info=note_info,
        )

        assert entity.is_note()
        assert entity.is_endnote()
        assert not entity.is_footnote()
        assert entity.note_info.chapter_number == 3

    def test_entity_with_position(self):
        """Test entity with spatial position."""
        region = PageRegion(
            region_type="body",
            spans=[TextSpan(text="text", font_size=10.0)],
            page_num=5,
        )
        entity = Entity(
            entity_type="citation", content="Derrida 1967", id="cite_1", position=region
        )

        assert entity.position is not None
        assert entity.position.page_num == 5

    def test_entity_metadata(self):
        """Test entity with metadata dict."""
        entity = Entity(
            entity_type="block_quote",
            content="Quote text",
            metadata={"source": "Being and Time", "page": 42},
        )

        assert entity.metadata["source"] == "Being and Time"
        assert entity.metadata["page"] == 42


class TestPyMuPDFConversion:
    """Test utility function for PyMuPDF conversion."""

    def test_create_text_span_bold(self):
        """Test creating TextSpan from PyMuPDF span with bold (CORRECTED)."""
        pymupdf_span = {
            "text": "bold text",
            "size": 12.0,
            "font": "Arial-Bold",
            "flags": 16,  # Bit 4 = bold (CORRECTED from bit 1!)
            "bbox": (10.0, 20.0, 100.0, 32.0),
        }

        span = create_text_span_from_pymupdf(pymupdf_span)

        assert span.text == "bold text"
        assert "bold" in span.formatting
        assert span.font_size == 12.0
        assert span.font_name == "Arial-Bold"
        assert span.bbox == (10.0, 20.0, 100.0, 32.0)

    def test_create_text_span_italic(self):
        """Test creating TextSpan with italic (CORRECTED)."""
        pymupdf_span = {
            "text": "italic text",
            "size": 12.0,
            "font": "Arial-Italic",
            "flags": 2,  # Bit 1 = italic (CORRECTED from bit 2!)
            "bbox": (10.0, 20.0, 100.0, 32.0),
        }

        span = create_text_span_from_pymupdf(pymupdf_span)

        assert "italic" in span.formatting
        assert "bold" not in span.formatting

    def test_create_text_span_superscript(self):
        """Test creating TextSpan with superscript (footnote marker)."""
        pymupdf_span = {
            "text": "1",
            "size": 8.0,
            "font": "Arial",
            "flags": 1,  # Bit 0 = superscript
            "bbox": (10.0, 20.0, 15.0, 26.0),
        }

        span = create_text_span_from_pymupdf(pymupdf_span)

        assert "superscript" in span.formatting

    def test_create_text_span_multiple_flags(self):
        """Test creating TextSpan with multiple flags."""
        pymupdf_span = {
            "text": "bold italic",
            "size": 12.0,
            "font": "Arial-BoldItalic",
            "flags": 18,  # 16 (bold) + 2 (italic) = 18
            "bbox": (10.0, 20.0, 100.0, 32.0),
        }

        span = create_text_span_from_pymupdf(pymupdf_span)

        assert "bold" in span.formatting
        assert "italic" in span.formatting

    def test_create_text_span_monospaced(self):
        """Test creating TextSpan with monospaced flag."""
        pymupdf_span = {
            "text": "code",
            "size": 10.0,
            "font": "Courier",
            "flags": 8,  # Bit 3 = monospaced
            "bbox": (10.0, 20.0, 40.0, 30.0),
        }

        span = create_text_span_from_pymupdf(pymupdf_span)

        assert "monospaced" in span.formatting

    def test_create_text_span_no_flags(self):
        """Test creating TextSpan with no flags (plain text)."""
        pymupdf_span = {
            "text": "plain text",
            "size": 10.0,
            "font": "Arial",
            "flags": 0,
            "bbox": (10.0, 20.0, 100.0, 30.0),
        }

        span = create_text_span_from_pymupdf(pymupdf_span)

        assert span.formatting == set()

    def test_create_text_span_missing_fields(self):
        """Test creating TextSpan with missing optional fields."""
        pymupdf_span = {
            "text": "minimal",
            # Missing: size, font, flags, bbox
        }

        span = create_text_span_from_pymupdf(pymupdf_span)

        assert span.text == "minimal"
        assert span.font_size == 10.0  # Default
        assert span.font_name == ""  # Default
        assert span.formatting == set()  # No flags
        assert span.bbox == (0.0, 0.0, 0.0, 0.0)  # Default


class TestIntegrationScenarios:
    """Test real-world integration scenarios."""

    def test_philosophy_text_with_sous_rature(self):
        """Test Derrida-style text with strikethrough (sous rature)."""
        # Create spans for: "Being ~~is~~ neither present nor absent"
        spans = [
            TextSpan(text="Being ", formatting=set()),
            TextSpan(text="is", formatting={"strikethrough"}),  # sous rature!
            TextSpan(text=" neither present nor absent", formatting=set()),
        ]

        region = PageRegion(region_type="body", spans=spans, page_num=42)
        markdown = region.get_markdown()

        assert "~~is~~" in markdown
        assert "Being" in markdown
        assert "neither present nor absent" in markdown

    def test_footnote_endnote_distinction(self):
        """Test distinguishing footnotes from endnotes."""
        # Footnote (page-local)
        footnote = Entity(
            entity_type="note",
            content="Translator note",
            id="fn_p5_1",
            note_info=NoteInfo(
                note_type=NoteType.FOOTNOTE,
                role=NoteRole.DEFINITION,
                marker="*",
                scope=NoteScope.PAGE,
            ),
        )

        # Endnote (document-global)
        endnote = Entity(
            entity_type="note",
            content="See Heidegger...",
            id="en_ch3_23",
            note_info=NoteInfo(
                note_type=NoteType.ENDNOTE,
                role=NoteRole.DEFINITION,
                marker="23",
                scope=NoteScope.CHAPTER,
                chapter_number=3,
            ),
        )

        # Should be distinguishable
        assert footnote.is_footnote()
        assert not footnote.is_endnote()
        assert endnote.is_endnote()
        assert not endnote.is_footnote()

        # Different scopes for linking
        assert footnote.note_info.scope == NoteScope.PAGE
        assert endnote.note_info.scope == NoteScope.CHAPTER

    def test_heading_with_bold_formatting(self):
        """Test heading region with bold formatting."""
        span = TextSpan(text="Introduction", formatting={"bold"}, font_size=18.0)

        region = PageRegion(
            region_type="body",
            spans=[span],
            page_num=1,
            heading_level=1,  # H1
        )

        assert region.is_heading()
        assert region.heading_level == 1
        assert region.get_markdown() == "**Introduction**"

    def test_nested_list_structure(self):
        """Test nested list with indent levels."""
        list_info = ListInfo(
            is_list_item=True,
            list_type="ul",
            marker="*",
            indent_level=2,  # Nested 2 levels deep
        )

        region = PageRegion(
            region_type="body",
            spans=[TextSpan(text="Nested point", font_size=10.0)],
            page_num=5,
            list_info=list_info,
        )

        assert region.is_list_item()
        assert region.list_info.indent_level == 2
