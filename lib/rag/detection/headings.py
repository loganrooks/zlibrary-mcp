"""
Heading detection from PDF font analysis.

Contains font distribution analysis and font-based heading detection
for building table of contents from PDFs without embedded ToC metadata.
"""
import logging
import re

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

__all__ = [
    '_analyze_font_distribution',
    '_detect_headings_from_fonts',
]

def _analyze_font_distribution(doc: 'fitz.Document', sample_pages: int = 10) -> float:
    """
    Analyze font size distribution across document to identify body text size.

    Uses statistical mode of font sizes from a sample of pages to determine
    the most common text size (body text). This serves as a baseline for
    detecting headings via relative size comparison.

    Args:
        doc: PyMuPDF document object
        sample_pages: Number of pages to sample (default: 10, max: total pages)

    Returns:
        float: Mode (most common) font size in points, or 10.0 if analysis fails
    """
    from collections import Counter

    font_sizes = []
    total_pages = len(doc)
    pages_to_sample = min(sample_pages, total_pages)

    # Sample pages evenly throughout document
    if total_pages <= sample_pages:
        page_indices = range(total_pages)
    else:
        # Spread samples evenly: beginning, middle, end
        step = total_pages // sample_pages
        page_indices = range(0, total_pages, step)[:sample_pages]

    logging.debug(f"Analyzing font distribution across {pages_to_sample} pages")

    try:
        for page_num in page_indices:
            page = doc[page_num]
            blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT).get("blocks", [])

            for block in blocks:
                if block.get("type") == 0:  # Text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            size = span.get("size")
                            text = span.get("text", "").strip()

                            # Only count substantial text (ignore page numbers, isolated chars)
                            if size and text and len(text) >= 3:
                                # Round to nearest 0.5 to group similar sizes
                                font_sizes.append(round(size * 2) / 2)

        if not font_sizes:
            logging.warning("No font sizes extracted, using default body size of 10.0")
            return 10.0

        # Find mode (most common font size)
        size_counts = Counter(font_sizes)
        body_size = size_counts.most_common(1)[0][0]

        logging.info(f"Detected body text size: {body_size}pt "
                    f"(from {len(font_sizes)} text spans, "
                    f"top 3 sizes: {size_counts.most_common(3)})")

        return body_size

    except Exception as e:
        logging.warning(f"Error analyzing font distribution: {e}, using default 10.0")
        return 10.0


def _detect_headings_from_fonts(
    doc: 'fitz.Document',
    body_size: float,
    threshold: float = 1.15,
    min_heading_length: int = 3,
    max_heading_length: int = 150
) -> dict:
    """
    Detect headings across all pages using font-based heuristics.

    Identifies potential headings by comparing font sizes against the body text
    baseline. Larger font sizes indicate higher-level headings. Includes filters
    to reduce false positives (page numbers, short text, overly long text).

    Algorithm:
    1. Scan all text spans in document
    2. Compare each span's font size to body_size
    3. If size >= body_size * threshold, consider as heading
    4. Assign heading level based on relative size (larger = higher level)
    5. Filter false positives based on length, content patterns

    Args:
        doc: PyMuPDF document object
        body_size: Mode font size from _analyze_font_distribution (body text baseline)
        threshold: Multiplier for minimum heading size (default: 1.15 = 15% larger)
        min_heading_length: Minimum characters for valid heading (default: 3)
        max_heading_length: Maximum characters for valid heading (default: 150)

    Returns:
        dict: Maps page_number (1-indexed) to list of (level, title) tuples
              Empty dict if no headings detected
    """
    toc_map = {}
    min_heading_size = body_size * threshold

    logging.info(f"Detecting headings: body_size={body_size}pt, "
                f"min_heading_size={min_heading_size:.1f}pt "
                f"(threshold={threshold})")

    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT).get("blocks", [])
            page_headings = []

            for block in blocks:
                if block.get("type") == 0:  # Text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            size = span.get("size", 0)
                            text = span.get("text", "").strip()
                            flags = span.get("flags", 0)
                            is_bold = bool(flags & 2)  # Font flag for bold

                            # Check if this span qualifies as a heading
                            if size >= min_heading_size and text:
                                # --- False Positive Filters ---

                                # Filter 1: Length constraints
                                if len(text) < min_heading_length or len(text) > max_heading_length:
                                    continue

                                # Filter 2: Pure numbers (likely page numbers)
                                if re.match(r'^\d+$', text):
                                    continue

                                # Filter 3: Roman numerals alone (likely page numbers)
                                if re.match(r'^[ivxlcdm]+$', text, re.IGNORECASE) and len(text) <= 5:
                                    continue

                                # Filter 4: Single letters or punctuation
                                if len(text) == 1:
                                    continue

                                # Filter 5: Mostly numbers/punctuation (e.g., "1.2.3", "---")
                                alpha_ratio = sum(c.isalpha() for c in text) / len(text)
                                if alpha_ratio < 0.5:
                                    continue

                                # --- Determine Heading Level ---
                                # Level based on relative font size (larger = higher level)
                                # Also consider bold formatting for disambiguation

                                size_ratio = size / body_size

                                if size_ratio >= 1.8:
                                    # 80%+ larger than body = H1
                                    level = 1
                                elif size_ratio >= 1.5:
                                    # 50-80% larger = H2
                                    level = 2
                                elif size_ratio >= 1.3:
                                    # 30-50% larger = H3 (or H2 if bold)
                                    level = 2 if is_bold else 3
                                elif size_ratio >= 1.15:
                                    # 15-30% larger = H3 (or H4 if not bold)
                                    level = 3 if is_bold else 4
                                else:
                                    # Below threshold (shouldn't happen due to initial check)
                                    continue

                                page_headings.append((level, text))

            # Add headings to map (use 1-indexed page numbers for consistency)
            if page_headings:
                toc_map[page_num + 1] = page_headings

        total_headings = sum(len(headings) for headings in toc_map.values())
        logging.info(f"Font-based detection found {total_headings} headings "
                    f"across {len(toc_map)} pages")

        # Log sample headings for validation
        if toc_map:
            sample_page = next(iter(toc_map))
            sample_headings = toc_map[sample_page][:3]
            logging.debug(f"Sample headings from page {sample_page}: {sample_headings}")

        return toc_map

    except Exception as e:
        logging.warning(f"Error detecting headings from fonts: {e}")
        return {}


