"""
PDF page-level formatting and markdown generation.

Contains _format_pdf_markdown and PDF-specific formatting helpers.
"""
import logging
import re
from pathlib import Path

from lib.rag.quality.analysis import _analyze_pdf_block
from lib.rag.quality.pipeline import QualityPipelineConfig, _apply_quality_pipeline
from lib.rag_data_models import PageRegion
from lib.formatting_group_merger import FormattingGroupMerger

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None

__all__ = [
    '_format_pdf_markdown',
]


def _format_pdf_markdown(
    page: 'fitz.Page',
    preserve_linebreaks: bool = False,
    toc_entries: list = None,
    pdf_page_num: int = None,
    written_page_num: str = None,
    written_page_position: str = None,
    written_page_text: str = None,
    use_toc_headings: bool = True,
    pdf_path: Path = None,
    quality_config: QualityPipelineConfig = None,
    xmark_cache: dict = None
) -> str:
    """
    Generates a Markdown string from a PyMuPDF page object.

    Extracts text blocks, analyzes structure using _analyze_pdf_block,
    and formats the output as Markdown, including basic headings, lists,
    and footnote definitions.

    Args:
        page: A fitz.Page object.
        preserve_linebreaks: If True, preserve original line breaks from PDF (for citation accuracy).
        toc_entries: List of (level, title) tuples for ToC entries on this page (from PDF metadata)
        pdf_page_num: PDF page number (1-indexed) for page markers
        written_page_num: Written page number (e.g., "xxiii", "15") if detected
        written_page_position: Position of written page number ('first' or 'last')
        written_page_text: Exact text of written page number to remove from content
        use_toc_headings: If True, use ToC for headings instead of font-size heuristics

    Returns:
        A string containing the generated Markdown.
    """
    fn_id = None # Initialize to prevent UnboundLocalError
    cleaned_fn_text = "" # Initialize to prevent UnboundLocalError
    blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT).get("blocks", [])
    markdown_lines = []
    footnote_defs = {} # Store footnote definitions [^id]: content
    current_list_type = None
    list_marker = None # Initialize list_marker

    # --- Page Markers (at the very start) ---
    page_markers = []

    # Always add PDF page number
    if pdf_page_num:
        page_markers.append(f"[[PDF_page_{pdf_page_num}]]")

    # Add written page number if available
    if written_page_num:
        page_markers.append(f"((p.{written_page_num}))")

    # Add page markers to output
    if page_markers:
        markdown_lines.append(" ".join(page_markers))
        markdown_lines.append("")  # Blank line after markers

    # --- ToC Headings (if this page has ToC entries) ---
    if use_toc_headings and toc_entries:
        for level, title in toc_entries:
            # Shift ToC levels down by 1 (document title is H1, so ToC entries start at H2)
            adjusted_level = level + 1
            heading_marker = '#' * adjusted_level
            markdown_lines.append(f"{heading_marker} {title}")
        markdown_lines.append("")  # Blank line after ToC headings

    # --- Extract and format blocks ---
    # Count only text blocks for position tracking
    text_blocks = [b for b in blocks if b.get("type") == 0]
    text_block_idx = 0

    for block_idx, block in enumerate(blocks):
        # Skip non-text blocks
        if block.get("type") != 0:
            continue

        # Pass use_toc_headings flag to disable font-size heading detection
        # Phase 2: Get structured PageRegion if quality pipeline enabled
        use_quality_pipeline = (quality_config is not None and quality_config.enable_pipeline)
        analysis = _analyze_pdf_block(
            block,
            preserve_linebreaks=preserve_linebreaks,
            detect_headings=not use_toc_headings,
            return_structured=use_quality_pipeline
        )

        # Phase 2: Apply quality pipeline if enabled and got PageRegion
        if use_quality_pipeline and isinstance(analysis, PageRegion):
            # Apply quality pipeline (garbled detection, X-marks, OCR recovery)
            # Pass xmark_cache for page-level caching
            analysis = _apply_quality_pipeline(analysis, pdf_path, (pdf_page_num - 1) if pdf_page_num else 0, quality_config, xmark_cache)

            # Convert PageRegion to dict for existing code (temporary until full migration)
            text = analysis.get_text()
            spans = analysis.spans  # List[TextSpan] objects
            heading_level = analysis.heading_level or 0
            is_list_item_region = analysis.is_list_item()

            # Create dict for existing code
            formatted_count = sum(1 for s in spans if s.formatting)
            if formatted_count > 0:
                logging.debug("Block has %d/%d spans with formatting", formatted_count, len(spans))

            analysis = {
                'text': text,
                'spans': [{'text': span.text, 'flags': 0, 'formatting': span.formatting} for span in spans],
                'heading_level': heading_level,
                'is_list_item': is_list_item_region,
                'list_type': analysis.list_info.list_type if analysis.list_info else None,
                'list_marker': analysis.list_info.marker if analysis.list_info else None,
                'list_indent': analysis.list_info.indent_level if analysis.list_info else 0,
                'quality_flags': analysis.quality_flags,
                'quality_score': analysis.quality_score
            }

        # Extract from dict (works for both legacy and converted PageRegion)
        text = analysis['text']
        spans = analysis['spans']

        # Cleaning is now done in _analyze_pdf_block
        if not text:
            text_block_idx += 1
            continue

        # --- Remove written page number duplication ---
        # If this is the first or last text block and contains the written page number, remove it
        is_first_block = (text_block_idx == 0)
        is_last_block = (text_block_idx == len(text_blocks) - 1)

        if written_page_text and written_page_position:
            should_filter = (
                (written_page_position == 'first' and is_first_block) or
                (written_page_position == 'last' and is_last_block)
            )

            if should_filter:
                # Check if this block's text matches or contains the written page number
                text_stripped = text.strip()

                # If the entire block is just the page number, skip it entirely
                if text_stripped == written_page_text.strip():
                    logging.debug(f"Skipping block containing only written page number: '{text_stripped}'")
                    text_block_idx += 1
                    continue

                # If the page number appears at start or end of the block, remove it
                if text_stripped.startswith(written_page_text.strip()):
                    # Remove from start and clean up any trailing whitespace
                    text = text_stripped[len(written_page_text.strip()):].strip()
                    logging.debug(f"Removed written page number from start of block: '{written_page_text}'")
                elif text_stripped.endswith(written_page_text.strip()):
                    # Remove from end and clean up any leading whitespace
                    text = text_stripped[:-len(written_page_text.strip())].strip()
                    logging.debug(f"Removed written page number from end of block: '{written_page_text}'")

        # Re-check if text is empty after page number removal
        if not text:
            text_block_idx += 1
            continue

        # Apply formatting group merger for correct markdown generation
        # Groups consecutive spans with identical formatting to prevent malformed markdown
        merger = FormattingGroupMerger()
        processed_text, potential_def_id = merger.process_spans_to_markdown(
            spans=spans,
            is_first_block=(text_block_idx == 0),
            block_text=text
        )

        # Clean up multiple spaces
        processed_text = re.sub(r'\s+', ' ', processed_text).strip()

        # Store definition if found, otherwise format content
        if potential_def_id:
            # Store potentially uncleaned text (cleaning moved to final formatting)
            footnote_defs[potential_def_id] = processed_text # Store raw processed text
            text_block_idx += 1
            continue # Don't add definition block as regular content

        # Format based on analysis (only if not using ToC headings)
        if analysis['heading_level'] > 0 and not use_toc_headings:
            markdown_lines.append(f"{'#' * analysis['heading_level']} {processed_text}")
            current_list_type = None # Reset list context after heading
        elif analysis['is_list_item']:
            # Basic list handling (needs refinement for nesting based on indent)
            # Remove original list marker from text if present
            list_marker = analysis.get('list_marker')
            clean_text = processed_text # Start with original processed text

            if analysis['list_type'] == 'ul' and list_marker:
                # Use regex to remove the specific marker found
                clean_text = re.sub(r"^" + re.escape(list_marker) + r"\s*", "", processed_text).strip()
                markdown_lines.append(f"* {clean_text}")
            elif analysis['list_type'] == 'ol' and list_marker:
                 # Use regex to remove the specific marker found (number/letter/roman + ./))
                clean_text = re.sub(r"^" + re.escape(list_marker) + r"[\.\)]\s*", "", processed_text, flags=re.IGNORECASE).strip()
                # Use the detected marker for the Markdown list item
                markdown_lines.append(f"{list_marker}. {clean_text}")
            current_list_type = analysis['list_type']
        else: # Regular paragraph
            # Only add if it's not empty after processing (e.g., after footnote extraction)
            if processed_text:
                markdown_lines.append(processed_text)
            current_list_type = None # Reset list context

        # Increment text block counter at the end of each iteration
        text_block_idx += 1

    # Join main content lines with double newlines
    main_content = "\n\n".join(md_line for md_line in markdown_lines if not md_line.startswith("[^")) # Exclude footnote defs for now
    main_content_stripped = main_content.strip() # Store stripped version for checks

    # Format footnote section separately, joining with single newlines
    footnote_block = ""
    if footnote_defs:
        footnote_lines = []
        for fn_id, fn_text in sorted(footnote_defs.items()):
            # Apply regex cleaning directly here
            cleaned_fn_text = re.sub(r"^[^\w]+", "", fn_text).strip()
            footnote_lines.append(f"[^{fn_id}]: {cleaned_fn_text}")
        # Construct the footnote block with correct spacing
        footnote_block = "---\n" + "\n".join(footnote_lines) # Definitions joined by single newline

    # Combine main content and footnote section
    if footnote_block:
        # Add double newline separator only if main content exists and is not empty
        separator = "\n\n" if main_content_stripped else ""
        # Ensure no leading/trailing whitespace on the final combined string
        return (main_content_stripped + separator + footnote_block).strip()
    else:
        # Return only the stripped main content if no footnotes
        return main_content_stripped
