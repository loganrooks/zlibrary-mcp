"""
TXT document processing.

Contains the process_txt entry point for plain text file processing.
"""
import logging
from pathlib import Path

import aiofiles

from lib.rag.detection.toc import _identify_and_remove_front_matter, _extract_and_format_toc

logger = logging.getLogger(__name__)

__all__ = [
    'process_txt',
]


async def process_txt(file_path: Path, output_format: str = "txt") -> str:
    """Processes a TXT file, applies preprocessing, and returns content."""
    logging.info(f"Processing TXT: {file_path}")
    try:
        try:
            # Try reading as UTF-8 first
            async def read_utf8():
                 async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
                     return await f.readlines()
            content_lines = await read_utf8() # Await async read
        except UnicodeDecodeError:
            logging.warning(f"UTF-8 decoding failed for {file_path}. Trying latin-1.")
            try:
                async def read_latin1():
                     async with aiofiles.open(file_path, mode='r', encoding='latin-1') as f:
                         return await f.readlines()
                content_lines = await read_latin1() # Await async read
            except Exception as read_err:
                 logging.error(f"Failed to read {file_path} with fallback encoding: {read_err}")
                 raise IOError(f"Could not read file {file_path}") from read_err
        except Exception as read_err:
             logging.error(f"Failed to read {file_path}: {read_err}")
             raise IOError(f"Could not read file {file_path}") from read_err

        # --- Preprocessing ---
        logging.debug("Starting TXT preprocessing (front matter, ToC)...")
        (lines_after_fm, title) = _identify_and_remove_front_matter(content_lines)
        (final_content_lines, formatted_toc) = _extract_and_format_toc(lines_after_fm, output_format)

        # --- Final Output Construction ---
        final_output_parts = []
        if title != "Unknown Title":
            final_output_parts.append(f"# {title}" if output_format == "markdown" else title)
        if formatted_toc:
            final_output_parts.append(formatted_toc)

        main_content = "\n".join(final_content_lines)
        final_output_parts.append(main_content.strip())

        return "\n\n".join(part for part in final_output_parts if part).strip()

    except Exception as e:
        logging.error(f"Error processing TXT {file_path}: {e}", exc_info=True)
        raise RuntimeError(f"Error processing TXT {file_path}: {e}") from e
