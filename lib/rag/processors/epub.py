"""
EPUB document processing and HTML-to-Markdown conversion.

Contains the EPUB node-to-markdown converter and the process_epub entry point.
"""
import logging
import re
from pathlib import Path

from lib.rag.utils.text import _html_to_text
from lib.rag.detection.toc import _identify_and_remove_front_matter, _extract_and_format_toc

logger = logging.getLogger(__name__)

try:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup, NavigableString
    EBOOKLIB_AVAILABLE = True
except ImportError:
    EBOOKLIB_AVAILABLE = False
    BeautifulSoup = None
    NavigableString = None


def _get_facade():
    """Get facade module for test mockability of optional dependencies."""
    import lib.rag_processing as _rp
    return _rp

__all__ = [
    '_epub_node_to_markdown',
    'process_epub',
]


def _epub_node_to_markdown(node: 'BeautifulSoup', footnote_defs: dict, list_level: int = 0) -> str:
    """
    Recursively converts a BeautifulSoup node (from EPUB HTML) to Markdown.
    Handles common HTML tags (headings, p, lists, blockquote, pre) and
    EPUB-specific footnote references/definitions (epub:type="noteref/footnote").
    """
    # Handle plain text nodes directly
    if isinstance(node, NavigableString):
        return str(node) # Return the string content
    markdown_parts = []
    node_name = getattr(node, 'name', None)
    indent = "  " * list_level # Indentation for nested lists
    prefix = '' # Default prefix

    if node_name == 'h1': prefix = '# '
    elif node_name == 'h2': prefix = '## '
    elif node_name == 'h3': prefix = '### '
    elif node_name == 'h4': prefix = '#### '
    elif node_name == 'h5': prefix = '##### '
    elif node_name == 'h6': prefix = '###### '
    elif node_name == 'p': prefix = ''
    elif node_name == 'ul':
        # Handle UL items recursively
        for child in node.find_all('li', recursive=False):
            item_text = _epub_node_to_markdown(child, footnote_defs, list_level + 1).strip()
            if item_text: markdown_parts.append(f"{indent}* {item_text}")
        return "\n".join(markdown_parts) # Return joined list items
    elif node_name == 'nav' and node.get('epub:type') == 'toc':
        # Handle Table of Contents (often uses nested <p><a>...</a></p> or similar)
        for child in node.descendants:
            if getattr(child, 'name', None) == 'a' and child.get_text(strip=True):
                 link_text = child.get_text(strip=True)
                 markdown_parts.append(f"* {link_text}")
        return "\n".join(markdown_parts)
    elif node_name == 'ol':
        # Handle OL items recursively
        for i, child in enumerate(node.find_all('li', recursive=False)):
            item_text = _epub_node_to_markdown(child, footnote_defs, list_level + 1).strip()
            if item_text: markdown_parts.append(f"{indent}{i+1}. {item_text}")
        return "\n".join(markdown_parts)
    elif node_name == 'li':
        # Process content within LI, prefix handled by parent ul/ol
        prefix = ''
    elif node_name == 'blockquote':
        prefix = '> '
    elif node_name == 'pre':
        # Handle code blocks
        code_content = node.get_text()
        return f"```\n{code_content}\n```"
    elif node_name == 'img':
        # Handle images - create placeholder
        src = node.get('src', '')
        alt = node.get('alt', '')
        return f"[Image: {src}/{alt}]" # Placeholder format as per spec/test
    elif node_name == 'table':
        # Basic table handling - extract text content
        # FUTURE: Implement proper Markdown table conversion if needed (edge case)
        return node.get_text(separator=' ', strip=True)
    elif node_name == 'a' and node.get('epub:type') == 'noteref':
        # Footnote reference
        href = node.get('href', '')
        fn_id_match = re.search(r'#ft(\d+)', href) # Example pattern, adjust if needed
        if fn_id_match:
            fn_id = fn_id_match.group(1)
            # Return the reference marker, process siblings/children if any (unlikely for simple ref)
            child_content = "".join(_epub_node_to_markdown(child, footnote_defs, list_level) for child in node.children).strip()
            return f"{child_content}[^{fn_id}]" # Append ref marker
        else:
             # Fallback if pattern doesn't match, process children
             pass # Continue to process children below
    elif node.get('epub:type') == 'footnote':
        # Footnote definition
        fn_id = node.get('id', '')
        fn_id_match = re.search(r'ft(\d+)', fn_id) # Example pattern
        if fn_id_match:
            num_id = fn_id_match.group(1)
            # Extract definition text, excluding the backlink if present
            content_node = node.find('p') or node # Assume content is in <p> or directly in the element
            if content_node:
                # Remove backlink if it exists (common pattern)
                backlink = content_node.find('a', {'epub:type': 'backlink'})
                if backlink: backlink.decompose()
                # Get cleaned text content
                fn_text = content_node.get_text(strip=True)
                footnote_defs[num_id] = fn_text
            return "" # Don't include definition inline
        else:
            # Fallback if ID pattern doesn't match
            pass # Continue to process children below

    # Process children recursively if not handled by specific tag logic above
    child_content = "".join(_epub_node_to_markdown(child, footnote_defs, list_level) for child in node.children).strip()

    # Apply prefix and return, handle block vs inline elements appropriately
    if node_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'blockquote']:
        # Block elements get prefix and potential double newline separation handled by caller
        return f"{prefix}{child_content}"
    else:
        # Inline elements just return their content
        return child_content


def process_epub(file_path: Path, output_format: str = "txt") -> str:
    """Processes an EPUB file, extracts text, applies preprocessing, and returns content."""
    # Get optional deps from facade for test mockability
    _rp = _get_facade()
    _epub = getattr(_rp, 'epub', epub)
    _ebooklib = getattr(_rp, 'ebooklib', ebooklib)
    _BeautifulSoup = getattr(_rp, 'BeautifulSoup', BeautifulSoup)
    _EBOOKLIB_AVAILABLE = getattr(_rp, 'EBOOKLIB_AVAILABLE', EBOOKLIB_AVAILABLE)

    if not _EBOOKLIB_AVAILABLE: raise ImportError("Required library 'ebooklib' is not installed.")
    logging.info(f"Processing EPUB: {file_path} for format: {output_format}")

    logging.debug(f"Attempting to read EPUB: {file_path}")
    try:
        logging.debug("Successfully opened EPUB file.")
        book = _epub.read_epub(str(file_path))
        all_lines = []
        footnote_defs = {} # Collect footnote definitions across items

        # --- Extract Content (HTML) ---
        items = list(book.get_items_of_type(_ebooklib.ITEM_DOCUMENT))
        logging.debug(f"Found {len(items)} items of type ITEM_DOCUMENT.")

        section_counter = 0
        for item in items:
            section_counter += 1
            logging.debug(f"Processing item: {item.get_name()}")
            try:
                content = item.get_content()
                if isinstance(content, bytes):
                    # Attempt decoding with common encodings
                    try:
                        html_content = content.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            html_content = content.decode('latin-1')
                        except UnicodeDecodeError:
                            logging.warning(f"Could not decode content from item {item.get_name()} in {file_path}. Skipping.")
                            continue
                # If not skipped, proceed with processing
                else: # Assume it's already a string
                    html_content = content

                if not html_content: continue

                # Add section marker for academic citations
                item_name = item.get_name()
                if output_format == "markdown":
                    section_marker = f"`[section.{section_counter}: {item_name}]`\n"
                    all_lines.append(section_marker)
                else:
                    section_marker = f"[Section {section_counter}: {item_name}]\n"
                    all_lines.append(section_marker)

                logging.debug(f"Converting item {item.get_name()} content to {output_format}...")
                # --- Convert HTML to Text or Markdown ---
                try: # Add try block around conversion
                    if output_format == "markdown":
                        logging.debug(f"Item {item.get_name()}: Converting HTML to Markdown...")
                        soup = _BeautifulSoup(html_content, 'lxml')
                        body = soup.find('body')
                        if body:
                            # Process body content, collecting footnote definitions
                            _rp_epub_to_md = getattr(_rp, '_epub_node_to_markdown', _epub_node_to_markdown)
                            item_markdown = _rp_epub_to_md(body, footnote_defs)
                            # Append footnote definitions collected from this item
                            # (Footnote formatting happens at the end)
                            all_lines.extend(item_markdown.splitlines())
                        else:
                             logging.warning(f"No <body> tag found in item {item.get_name()}. Skipping.")
                    else: # Default to text
                        logging.debug(f"Item {item.get_name()}: Extracting plain text from HTML...")
                        _rp_html_to_text = getattr(_rp, '_html_to_text', _html_to_text)
                        item_text = _rp_html_to_text(html_content)
                        if item_text:
                            all_lines.extend(item_text.splitlines())
                except Exception as conversion_err:
                     logging.error(f"Error converting content from item {item.get_name()} in {file_path}: {conversion_err}", exc_info=True)
                     # Optionally add a placeholder or skip the item
                     all_lines.append(f"[Error processing item {item.get_name()}]")

            except Exception as item_err:
                logging.error(f"Error reading content from item {item.get_name()} in {file_path}: {item_err}", exc_info=True)
                all_lines.append(f"[Error reading item {item.get_name()}]")

        # --- Preprocessing ---
        # Use facade references for test mockability
        logging.debug("Starting EPUB preprocessing (front matter, ToC)...")
        _rp_identify = getattr(_rp, '_identify_and_remove_front_matter', _identify_and_remove_front_matter)
        _rp_extract_toc = getattr(_rp, '_extract_and_format_toc', _extract_and_format_toc)
        (lines_after_fm, title) = _rp_identify(all_lines)
        (final_content_lines, formatted_toc) = _rp_extract_toc(lines_after_fm, output_format)

        # --- Final Output Construction ---
        final_output_parts = []
        if title != "Unknown Title":
            final_output_parts.append(f"# {title}" if output_format == "markdown" else title)
        if formatted_toc:
            final_output_parts.append(formatted_toc)

        main_content = "\n".join(final_content_lines) # Join preprocessed lines
        final_output_parts.append(main_content.strip())

        # Append formatted footnote definitions if output is markdown
        if output_format == "markdown" and footnote_defs:
            footnote_block_lines = ["---"]
            for fn_id, fn_text in sorted(footnote_defs.items()):
                footnote_block_lines.append(f"[^{fn_id}]: {fn_text}")
            final_output_parts.append("\n".join(footnote_block_lines))

        return "\n\n".join(part for part in final_output_parts if part).strip()

    except Exception as e:
        logging.error(f"Error processing EPUB {file_path}: {e}", exc_info=True)
        raise RuntimeError(f"Error processing EPUB {file_path}: {e}") from e
