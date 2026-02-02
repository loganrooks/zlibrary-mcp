"""Output writer: routes classified blocks to separated content streams.

Consumes classified pages from the compositor and document-level context
from detector pre-pass to build the final DocumentOutput.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from lib.rag.pipeline.models import (
    BlockClassification,
    ContentType,
    DocumentOutput,
)


def build_document_output(
    classified_pages: Dict[int, List[BlockClassification]],
    context: dict,
    include_metadata: bool = False,
) -> DocumentOutput:
    """Build final document output from classified blocks and context.

    Routes blocks by ContentType to appropriate output streams.
    Uses context from document-level detectors to exclude front matter,
    TOC pages, and page numbers from body text.

    Args:
        classified_pages: Dict mapping page_num (1-indexed) to classified blocks.
        context: Shared context from detector pre-pass.
        include_metadata: If True, include per-block classification details.

    Returns:
        DocumentOutput with separated content streams.
    """
    # Extract context values from detector pre-pass
    page_number_map: Dict[int, str] = context.get("page_number_map", {})
    toc_map: Dict[str, Any] = context.get("toc_map", {})
    front_matter: Dict[str, Any] = context.get("front_matter", {})

    # Determine pages to exclude from body text
    excluded_pages: set = set()

    # Exclude front matter pages
    fm_pages = front_matter.get("pages", [])
    if isinstance(fm_pages, (list, set)):
        excluded_pages.update(fm_pages)
    elif isinstance(fm_pages, dict) and "start" in fm_pages and "end" in fm_pages:
        excluded_pages.update(range(fm_pages["start"], fm_pages["end"] + 1))

    # Exclude TOC pages
    toc_pages = toc_map.get("pages", [])
    if isinstance(toc_pages, (list, set)):
        excluded_pages.update(toc_pages)

    # Collect blocks by type
    body_blocks: List[BlockClassification] = []
    margin_blocks: List[BlockClassification] = []
    footnote_blocks: List[BlockClassification] = []
    endnote_blocks: List[BlockClassification] = []
    citation_blocks: List[BlockClassification] = []
    all_classifications: List[Dict[str, Any]] = []

    for page_num in sorted(classified_pages.keys()):
        blocks = classified_pages[page_num]
        page_excluded = page_num in excluded_pages
        mapped_page_str = page_number_map.get(page_num, "")

        for block in blocks:
            # Track for processing metadata
            if include_metadata:
                all_classifications.append(
                    {
                        "page": page_num,
                        "bbox": block.bbox,
                        "type": block.content_type.value,
                        "confidence": block.confidence,
                        "detector": block.detector_name,
                    }
                )

            # Skip page numbers entirely
            if block.content_type == ContentType.PAGE_NUMBER:
                continue

            # Strip page number text from body blocks
            if (
                block.content_type == ContentType.BODY
                and mapped_page_str
                and block.text.strip() == mapped_page_str.strip()
            ):
                continue

            # Route TOC blocks to metadata, not body
            if block.content_type == ContentType.TOC:
                continue

            # Route front matter blocks to metadata, not body
            if block.content_type == ContentType.FRONT_MATTER:
                continue

            # Skip body/heading blocks on excluded pages
            if page_excluded and block.content_type in (
                ContentType.BODY,
                ContentType.HEADING,
            ):
                continue

            # Route by content type
            if block.content_type == ContentType.FOOTNOTE:
                footnote_blocks.append(block)
            elif block.content_type == ContentType.ENDNOTE:
                endnote_blocks.append(block)
            elif block.content_type == ContentType.MARGIN:
                margin_blocks.append(block)
            elif block.content_type == ContentType.CITATION:
                citation_blocks.append(block)
            elif block.content_type == ContentType.HEADING:
                body_blocks.append(block)
            elif block.content_type == ContentType.BODY:
                body_blocks.append(block)
            # HEADER/FOOTER: silently dropped from output

    # Build output
    body_text = format_body_text(body_blocks, margin_blocks)
    footnotes = format_footnotes(footnote_blocks)
    endnotes = format_footnotes(endnote_blocks) if endnote_blocks else None
    citations = _format_citations(citation_blocks) if citation_blocks else None

    # Build document metadata
    document_metadata: dict = {}
    if toc_map:
        document_metadata["toc"] = toc_map
    if front_matter:
        document_metadata["front_matter"] = front_matter
    if page_number_map:
        document_metadata["page_count"] = len(page_number_map)
    title = context.get("title", "")
    if title:
        document_metadata["title"] = title

    # Build processing metadata
    processing_metadata: Optional[dict] = None
    if include_metadata:
        processing_metadata = {
            "total_blocks": len(all_classifications),
            "classifications": all_classifications,
        }

    return DocumentOutput(
        body_text=body_text,
        footnotes=footnotes,
        endnotes=endnotes,
        citations=citations,
        document_metadata=document_metadata if document_metadata else None,
        processing_metadata=processing_metadata,
    )


def format_body_text(
    body_blocks: List[BlockClassification],
    margin_blocks: List[BlockClassification],
) -> str:
    """Format body blocks as continuous text with inline margin annotations.

    Args:
        body_blocks: Classified body and heading blocks in page order.
        margin_blocks: Margin blocks to insert inline.

    Returns:
        Formatted body text string.
    """
    if not body_blocks and not margin_blocks:
        return ""

    # Group margins by page for inline insertion
    margins_by_page: Dict[int, List[BlockClassification]] = defaultdict(list)
    for m in margin_blocks:
        margins_by_page[m.page_num].append(m)

    # Sort margins by y-position within each page
    for page_margins in margins_by_page.values():
        page_margins.sort(key=lambda b: b.bbox[1])

    pages_output: List[str] = []
    current_page = -1
    page_lines: List[str] = []

    for block in body_blocks:
        if block.page_num != current_page:
            # Flush previous page
            if page_lines:
                # Insert margins for previous page before flushing
                if current_page in margins_by_page:
                    for m in margins_by_page.pop(current_page):
                        page_lines.append(f"[margin: {m.text.strip()}]")
                pages_output.append("\n".join(page_lines))
            page_lines = []
            current_page = block.page_num

        # Format headings as markdown
        if block.content_type == ContentType.HEADING:
            level = block.metadata.get("level", 2)
            prefix = "#" * level
            page_lines.append(f"{prefix} {block.text.strip()}")
        else:
            page_lines.append(block.text.strip())

    # Flush last page
    if page_lines:
        if current_page in margins_by_page:
            for m in margins_by_page.pop(current_page):
                page_lines.append(f"[margin: {m.text.strip()}]")
        pages_output.append("\n".join(page_lines))

    # Any remaining margins on pages with no body blocks
    for page_num in sorted(margins_by_page.keys()):
        margin_lines = [
            f"[margin: {m.text.strip()}]" for m in margins_by_page[page_num]
        ]
        pages_output.append("\n".join(margin_lines))

    return "\n\n".join(pages_output)


def format_footnotes(
    footnote_blocks: List[BlockClassification],
) -> Optional[str]:
    """Format footnotes grouped by page.

    Args:
        footnote_blocks: Classified footnote blocks.

    Returns:
        Formatted footnotes string, or None if empty.
    """
    if not footnote_blocks:
        return None

    by_page: Dict[int, List[BlockClassification]] = defaultdict(list)
    for fn in footnote_blocks:
        by_page[fn.page_num].append(fn)

    sections: List[str] = []
    for page_num in sorted(by_page.keys()):
        blocks = by_page[page_num]
        # Sort by y-position
        blocks.sort(key=lambda b: b.bbox[1])
        lines = [f"## Page {page_num}", ""]
        for i, block in enumerate(blocks, 1):
            lines.append(f"{i}. {block.text.strip()}")
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def _format_citations(
    citation_blocks: List[BlockClassification],
) -> Optional[str]:
    """Format citation blocks."""
    if not citation_blocks:
        return None

    lines: List[str] = []
    for block in citation_blocks:
        lines.append(f"- {block.text.strip()}")
    return "\n".join(lines)


def format_metadata_sidecar(
    document_metadata: dict,
    processing_metadata: Optional[dict] = None,
) -> dict:
    """Build the JSON structure for _meta.json sidecar file.

    Args:
        document_metadata: Document-level metadata (TOC, front matter, etc).
        processing_metadata: Optional per-block classification details.

    Returns:
        Dict suitable for JSON serialization.
    """
    sidecar: dict = {
        "title": document_metadata.get("title", ""),
        "toc": document_metadata.get("toc"),
        "front_matter": document_metadata.get("front_matter"),
        "page_count": document_metadata.get("page_count"),
    }

    if processing_metadata:
        sidecar["processing"] = processing_metadata

    return sidecar
