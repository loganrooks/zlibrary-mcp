"""
Table of contents extraction and formatting.

Contains PDF ToC extraction (embedded + font-based fallback),
text-based ToC extraction, front matter identification, and markdown formatting.
"""

import logging
import re
from typing import Any, Dict, List

try:
    import fitz  # noqa: F811
except ImportError:
    fitz = None  # type: ignore[assignment]

from lib.rag.detection.registry import register_detector
from lib.rag.pipeline.models import (
    BlockClassification,
    ContentType,
    DetectionResult,
    DetectorScope,
)

logger = logging.getLogger(__name__)

# Import heading detection for fallback ToC
from lib.rag.detection.headings import (
    _analyze_font_distribution,
    _detect_headings_from_fonts,
)

__all__ = [
    "_extract_toc_from_pdf",
    "_identify_and_remove_front_matter",
    "_format_toc_lines_as_markdown",
    "_extract_and_format_toc",
]


@register_detector("toc", priority=15, scope=DetectorScope.DOCUMENT)
def detect_toc_pipeline(doc: Any, context: Dict[str, Any]) -> DetectionResult:
    """Pipeline adapter for table of contents detection."""
    toc_map = _extract_toc_from_pdf(doc)
    classifications: List[BlockClassification] = []
    for page_num, entries in toc_map.items():
        for level, title in entries:
            classifications.append(
                BlockClassification(
                    bbox=(0, 0, 0, 0),
                    content_type=ContentType.TOC,
                    text=title,
                    confidence=0.8,
                    detector_name="toc",
                    page_num=page_num,
                    metadata={"level": level, "bbox_available": False},
                )
            )
    context["toc_map"] = toc_map
    return DetectionResult(
        detector_name="toc",
        classifications=classifications,
        page_num=0,
        metadata={"toc_map": toc_map},
    )


def _extract_toc_from_pdf(doc: "fitz.Document") -> dict:
    """
    Extract table of contents using hybrid approach: embedded metadata first,
    font-based heuristics as fallback.

    Strategy:
    1. Try embedded ToC from PDF metadata (doc.get_toc())
    2. If empty, analyze font distribution to find body text size
    3. Use font size heuristics to detect headings (15%+ larger than body)
    4. Build heading hierarchy based on relative font sizes

    Font-based detection achieves 70-85% accuracy based on research findings.
    Works best for PDFs with consistent heading formatting (size, boldness).

    Args:
        doc: PyMuPDF document object

    Returns:
        dict: Maps page_number (1-indexed) to list of (level, title) tuples
              Empty dict if no ToC available via either method
    """
    toc_map = {}

    # --- Phase 1: Try Embedded ToC (Primary Method) ---
    try:
        toc = doc.get_toc()  # Returns list of [level, title, page_num]
        if toc:
            for level, title, page_num in toc:
                if page_num not in toc_map:
                    toc_map[page_num] = []
                toc_map[page_num].append((level, title))

            logging.info(
                f"✓ Embedded ToC: {len(toc)} entries covering {len(toc_map)} pages"
            )
            return toc_map
        else:
            logging.info(
                "✗ No embedded ToC metadata found, trying font-based detection"
            )

    except Exception as toc_err:
        logging.warning(
            f"✗ Error reading embedded ToC: {toc_err}, trying font-based detection"
        )

    # --- Phase 2: Font-Based Heuristics (Fallback Method) ---
    try:
        # Step 1: Analyze font distribution to find body text size
        body_size = _analyze_font_distribution(doc, sample_pages=10)

        # Step 2: Detect headings using font size threshold (15% larger than body)
        toc_map = _detect_headings_from_fonts(
            doc,
            body_size=body_size,
            threshold=1.15,  # 15% larger than body text
            min_heading_length=3,
            max_heading_length=150,
        )

        if toc_map:
            total_headings = sum(len(headings) for headings in toc_map.values())
            logging.info(
                f"✓ Font-based ToC: {total_headings} headings across {len(toc_map)} pages "
                f"(body_size={body_size:.1f}pt)"
            )
        else:
            logging.info("✗ Font-based detection found no headings")

        return toc_map

    except Exception as font_err:
        logging.warning(f"✗ Font-based ToC detection failed: {font_err}")
        return {}


def _identify_and_remove_front_matter(
    content_lines: list[str],
) -> tuple[list[str], str]:
    """
    Identifies title (basic heuristic), removes basic front matter lines based on keywords,
    returns cleaned content lines and title. Matches current test expectations.
    """
    logging.debug("Running basic front matter removal and title identification...")
    title = "Unknown Title"  # Default title
    cleaned_lines = []

    # --- Basic Title Identification Heuristic ---
    # Look for the first non-empty line within the first ~5 lines
    # SKIP page markers (they're not titles)
    for line in content_lines[:5]:
        stripped_line = line.strip()
        # Skip page markers like [[PDF_page_1]] or ((p.1))
        if stripped_line and not (
            stripped_line.startswith("[[") or stripped_line.startswith("((")
        ):
            title = stripped_line
            logging.debug(f"Identified potential title: {title}")
            break  # Found the first non-empty line, assume it's the title

    # --- Front Matter Removal Logic ---
    # Define keywords for publisher info, copyright, etc.
    FRONT_MATTER_SKIP_TWO = ["dedication", "copyright notice"]  # Skip line + next
    FRONT_MATTER_SKIP_ONE = [
        "copyright",
        "isbn",
        "published by",
        "acknowledgments",
        "cambridge university press",
        "stanford university press",
        "library of congress",
        "cataloging in publication",
        "all rights reserved",
        "printed in",
        "reprinted",
        "first published",
        "permissions",
        "without permission",
    ]

    i = 0
    while i < len(content_lines):
        line = content_lines[i]
        line_lower = line.strip().lower()
        skipped = False

        # Check skip-two keywords first
        if any(keyword in line_lower for keyword in FRONT_MATTER_SKIP_TWO):
            logging.debug(
                f"Skipping front matter block (2 lines) starting with: {line.strip()}"
            )
            i += 2  # Skip current line and the next line
            skipped = True
        # Check skip-one keywords if not already skipped
        elif any(keyword in line_lower for keyword in FRONT_MATTER_SKIP_ONE):
            logging.debug(f"Skipping single front matter line: {line.strip()}")
            i += 1  # Skip current line only
            skipped = True

        if not skipped:
            # Preserve lines
            cleaned_lines.append(line)
            i += 1

    # Return original lines if filtering removed everything (edge case)
    # Note: This edge case handling might need review if the test changes
    # Ensure a tuple is always returned, even if cleaned_lines is empty
    if not cleaned_lines:
        logging.warning("Front matter removal resulted in empty content.")
        # Return empty list and the identified title
        return [], title

    return cleaned_lines, title


def _format_toc_lines_as_markdown(toc_lines: list[str]) -> str:
    """Formats extracted ToC lines into a Markdown list, handling basic indentation."""
    markdown_list = []
    base_indent = -1  # Track base indentation level

    for line in toc_lines:
        stripped_line = line.strip()
        if not stripped_line:
            continue  # Skip empty lines

        # Basic indentation detection (count leading spaces)
        indent_level = len(line) - len(line.lstrip(" "))
        if base_indent == -1:
            base_indent = indent_level  # Set base indent on first non-empty line

        # Calculate relative indent level (simple approach)
        relative_indent = max(
            0, (indent_level - base_indent) // 2
        )  # Assume 2 spaces per level
        indent_str = "  " * relative_indent
        # Remove page numbers/dots for cleaner Markdown
        text_part = re.sub(r"[\s.]{2,}\d+$", "", stripped_line).strip()
        markdown_list.append(f"{indent_str}* {text_part}")

    return "\n".join(markdown_list)


def _extract_and_format_toc(
    content_lines: list[str], output_format: str
) -> tuple[list[str], str]:
    """
    Extracts Table of Contents (ToC) lines based on heuristics, formats it
    (currently only for Markdown), and returns remaining content lines and formatted ToC.
    """
    logging.debug("Attempting to extract and format Table of Contents...")
    toc_lines = []
    remaining_lines = []
    in_toc = False
    toc_start_index = -1  # Added: Track start of ToC
    toc_end_index = -1
    # main_content_start_index = -1 # Removed: Simplify logic based on toc_end_index

    # Heuristic: Look for common ToC start keywords
    TOC_START_KEYWORDS = ["contents", "table of contents"]
    # Heuristic: Look for lines ending with page numbers (dots or spaces before number)
    # Updated regex to be more specific and avoid matching chapter titles
    TOC_LINE_PATTERN = re.compile(
        r"^(.*?)[\s.]{2,}(\d+)$"
    )  # Non-greedy match for text, require >=2 dots/spaces before number
    # Heuristic: Look for common main content start keywords
    MAIN_CONTENT_START_KEYWORDS = ["introduction", "preface", "chapter 1", "part i"]

    # First pass: Identify potential ToC block
    for i, line in enumerate(content_lines):
        line_lower = line.strip().lower()

        if not in_toc and any(keyword in line_lower for keyword in TOC_START_KEYWORDS):
            in_toc = True
            toc_start_index = i  # Record start index
            logging.debug(f"Potential ToC start found at line {i}: {line.strip()}")
            # Don't add the keyword line itself to toc_lines
            continue  # Skip the "Contents" line itself

        if in_toc:
            # Check if line matches ToC pattern OR is empty (allow empty lines within ToC)
            is_toc_like = bool(TOC_LINE_PATTERN.match(line.strip())) or not line.strip()
            # Check if line signals start of main content AND doesn't look like a ToC line itself
            is_main_content_start = (
                any(
                    line_lower.startswith(keyword)
                    for keyword in MAIN_CONTENT_START_KEYWORDS
                )
                and not is_toc_like
            )

            if is_toc_like and not is_main_content_start:
                # toc_lines.append(line) # Keep original line with indentation - NO, collect indices first
                toc_end_index = i  # Track the last potential ToC line index
            # Simplified end condition: if it's not a ToC line, assume ToC ended on the previous line.
            else:
                logging.debug(
                    f"Potential ToC end detected before line {i} (non-matching line): {line.strip()}"
                )
                break  # Stop processing ToC lines

    # Determine final content lines based on findings
    if (
        toc_start_index != -1
        and toc_end_index != -1
        and toc_end_index >= toc_start_index
    ):  # Ensure end is after start
        # ToC found: combine lines before start and after end
        remaining_lines = (
            content_lines[:toc_start_index] + content_lines[toc_end_index + 1 :]
        )
        # Ensure toc_lines only contains lines within the identified block
        # (Adjust indices relative to the original content_lines)
        actual_toc_start_line_index = toc_start_index + 1  # Line after the keyword
        actual_toc_end_line_index = toc_end_index
        toc_lines = content_lines[
            actual_toc_start_line_index : actual_toc_end_line_index + 1
        ]

    else:
        # No ToC found or block incomplete, keep all original lines
        remaining_lines = content_lines
        toc_lines = []  # Ensure toc_lines is empty

    logging.debug(
        f"Identified {len(toc_lines)} ToC lines. {len(remaining_lines)} remaining content lines."
    )

    # Format ToC only if requested and lines were found
    formatted_toc = ""  # Initialize as empty string instead of None
    if output_format == "markdown" and toc_lines:
        formatted_toc = _format_toc_lines_as_markdown(toc_lines)
        logging.debug("Formatted ToC for Markdown output.")

    return remaining_lines, formatted_toc


# --- PDF Quality Analysis ---
