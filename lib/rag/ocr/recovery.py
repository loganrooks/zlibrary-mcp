"""
OCR quality assessment and remediation.

Contains functions for assessing PDF OCR quality, re-OCRing with Tesseract,
and running OCR on PDF files.
"""
import io
import logging
import subprocess
import tempfile
from pathlib import Path

from lib.rag.utils.exceptions import TesseractNotFoundError, OCRDependencyError
from lib.rag.ocr.spacing import detect_letter_spacing_issue

logger = logging.getLogger(__name__)

# OCR Dependencies (Optional)
try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    pytesseract = None
    convert_from_path = None
    Image = None

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None


def _get_facade():
    """Get facade module for test mockability of optional dependencies."""
    import lib.rag_processing as _rp
    return _rp

__all__ = [
    'run_ocr_on_pdf',
    'assess_pdf_ocr_quality',
    'redo_ocr_with_tesseract',
]


def assess_pdf_ocr_quality(pdf_path: Path, sample_pages: int = 10) -> dict:
    """
    Assess OCR quality of a PDF by sampling pages and detecting common issues.

    Samples pages strategically (beginning, middle, end) and checks for:
    - Letter spacing issues (e.g., "T H E")
    - Low text extraction rate
    - High image-to-text ratio

    Args:
        pdf_path: Path to PDF file
        sample_pages: Number of pages to sample (default 10)

    Returns:
        dict with:
            - score: Quality score 0-1 (1 = perfect, 0 = terrible)
            - has_text_layer: Whether PDF has embedded text
            - issues: List of detected issues
            - recommendation: "use_existing" | "redo_ocr" | "force_ocr"
    """
    _fitz = getattr(_get_facade(), 'fitz', fitz)
    try:
        doc = _fitz.open(pdf_path)
        total_pages = doc.page_count

        if total_pages == 0:
            return {
                "score": 0.0,
                "has_text_layer": False,
                "issues": ["no_pages"],
                "recommendation": "error"
            }

        # Sample strategy: first 3 + middle 4 + last 3
        # For small PDFs, sample all pages
        if total_pages <= sample_pages:
            sample_indices = list(range(total_pages))
        else:
            first = list(range(min(3, total_pages)))
            last = list(range(max(total_pages - 3, 3), total_pages))
            middle_start = total_pages // 2 - 2
            middle = list(range(middle_start, min(middle_start + 4, total_pages)))
            sample_indices = sorted(set(first + middle + last))[:sample_pages]

        # Quality metrics
        pages_with_issues = 0
        pages_with_text = 0
        total_chars = 0
        issue_types = set()

        for page_num in sample_indices:
            page = doc[page_num]
            text = page.get_text()

            # Check if page has text
            if len(text.strip()) > 50:  # Minimum threshold for "has text"
                pages_with_text += 1
                total_chars += len(text)

                # Check for letter spacing issues
                if detect_letter_spacing_issue(text):
                    pages_with_issues += 1
                    issue_types.add("letter_spacing")
            else:
                issue_types.add("missing_text")

        doc.close()

        # Calculate quality score
        has_text_layer = pages_with_text > 0

        if not has_text_layer:
            return {
                "score": 0.0,
                "has_text_layer": False,
                "issues": list(issue_types),
                "recommendation": "force_ocr"
            }

        # Score based on percentage of clean pages
        clean_pages_ratio = 1.0 - (pages_with_issues / len(sample_indices))

        # Penalize if very few pages have text
        text_coverage_ratio = pages_with_text / len(sample_indices)

        # Average characters per sampled page
        avg_chars = total_chars / max(pages_with_text, 1)

        # Combined score (weighted)
        score = (
            clean_pages_ratio * 0.6 +  # Primary: how many pages are clean
            text_coverage_ratio * 0.3 +  # Secondary: text coverage
            min(avg_chars / 1000, 1.0) * 0.1  # Tertiary: text density
        )

        # Determine recommendation
        if score >= 0.75:
            recommendation = "use_existing"
        elif score >= 0.3:
            recommendation = "redo_ocr"
        else:
            recommendation = "force_ocr"

        logging.info(
            f"OCR quality assessment: score={score:.2f}, "
            f"pages_sampled={len(sample_indices)}, "
            f"pages_with_issues={pages_with_issues}, "
            f"recommendation={recommendation}"
        )

        return {
            "score": round(score, 2),
            "has_text_layer": has_text_layer,
            "issues": list(issue_types),
            "recommendation": recommendation
        }

    except Exception as e:
        logging.error(f"Error assessing PDF quality: {e}")
        return {
            "score": 0.5,  # Neutral score on error
            "has_text_layer": True,  # Assume it exists
            "issues": ["assessment_error"],
            "recommendation": "use_existing"  # Safe fallback
        }


def redo_ocr_with_tesseract(input_pdf: Path, output_dir: Path = None) -> Path:
    """
    Re-OCR a PDF using Tesseract via ocrmypdf.

    Strips existing (poor quality) text layer and performs fresh OCR.

    Args:
        input_pdf: Path to input PDF with poor OCR quality
        output_dir: Directory for output PDF (default: temp directory)

    Returns:
        Path to OCR'd PDF file

    Raises:
        subprocess.CalledProcessError: If ocrmypdf fails
        FileNotFoundError: If tesseract is not installed
    """
    if output_dir is None:
        output_dir = Path(tempfile.gettempdir())

    output_dir.mkdir(parents=True, exist_ok=True)

    # Output filename: original_name.ocr.pdf
    output_pdf = output_dir / f"{input_pdf.stem}.ocr.pdf"

    logging.info(f"Re-OCRing PDF with Tesseract: {input_pdf.name}")

    try:
        # ocrmypdf command: strip bad OCR, re-OCR with Tesseract
        result = subprocess.run(
            [
                'ocrmypdf',
                '--redo-ocr',  # Strip existing text layer, re-OCR
                '--optimize', '1',  # Light optimization
                '--output-type', 'pdf',  # Output as PDF
                '--jobs', '4',  # Parallel processing (4 threads)
                '--skip-big', '50',  # Skip pages > 50MB (likely images)
                str(input_pdf),
                str(output_pdf)
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        logging.info(f"OCR complete: {output_pdf}")
        return output_pdf

    except subprocess.TimeoutExpired:
        logging.error(f"OCR timeout after 10 minutes: {input_pdf.name}")
        raise
    except subprocess.CalledProcessError as e:
        logging.error(f"OCR failed: {e.stderr}")
        raise
    except FileNotFoundError:
        logging.error("Tesseract not found. Install with: apt-get install tesseract-ocr")
        raise


def run_ocr_on_pdf(pdf_path: str, lang: str = 'eng') -> str: # Cycle 21 Refactor: Add lang parameter
    """
    Performs OCR on a PDF file using Tesseract via PyMuPDF rendering.

    Args:
        pdf_path: Path to the PDF file.
        lang: Language code for Tesseract (e.g., 'eng').

    Returns:
        Extracted text content as a single string.

    Raises:
        OCRDependencyError: If required OCR dependencies are not installed.
        TesseractNotFoundError: If Tesseract executable is not found.
        RuntimeError: For other processing errors.
    """
    # Get optional deps from facade for test mockability
    _rp = _get_facade()
    _OCR_AVAILABLE = getattr(_rp, 'OCR_AVAILABLE', OCR_AVAILABLE)
    _PYMUPDF_AVAILABLE = getattr(_rp, 'PYMUPDF_AVAILABLE', PYMUPDF_AVAILABLE)
    _fitz = getattr(_rp, 'fitz', fitz)
    _pytesseract = getattr(_rp, 'pytesseract', pytesseract)
    _Image = getattr(_rp, 'Image', Image)

    if not _OCR_AVAILABLE:
        raise OCRDependencyError("OCR dependencies (pytesseract, pdf2image, Pillow) not installed.")
    if not _PYMUPDF_AVAILABLE:
        raise OCRDependencyError("PyMuPDF (fitz) is required for OCR rendering but not installed.")

    logging.info(f"Running OCR on {pdf_path} with language '{lang}'...")
    extracted_text = ""
    doc = None
    try:
        doc = _fitz.open(pdf_path)
        page_count = len(doc)
        logging.debug(f"PDF has {page_count} pages.")

        for i, page in enumerate(doc):
            page_num = i + 1
            logging.debug(f"Processing page {page_num}/{page_count} for OCR...")
            try:
                # Render page to pixmap, then to PNG bytes
                pix = page.get_pixmap(dpi=300) # Higher DPI for better OCR
                img_bytes = pix.tobytes("png")
                img = _Image.open(io.BytesIO(img_bytes))

                # Perform OCR on the image
                page_text = _pytesseract.image_to_string(img, lang=lang)
                extracted_text += page_text + "\n\n" # Add page separator
                logging.debug(f"OCR successful for page {page_num}.")
            # Specific exception must come BEFORE generic Exception
            except TesseractNotFoundError as tess_err:
                 logging.error(f"Tesseract not found during OCR on page {page_num}: {tess_err}")
                 raise # Re-raise to be caught by outer handler
            except Exception as page_err:
                 logging.error(f"Error during OCR on page {page_num}: {page_err}", exc_info=True)
                 # Continue to next page if one fails? Or raise? Let's continue for now.
                 extracted_text += f"[OCR Error on Page {page_num}]\n\n"

        logging.info(f"OCR completed for {pdf_path}. Total extracted length: {len(extracted_text)}")
        return extracted_text.strip()

    # Removed redundant outer TesseractNotFoundError catch, inner loop handler re-raises.
    # Catch specific PyMuPDF file opening errors or other RuntimeErrors
    except RuntimeError as fitz_err:
         logging.error(f"PyMuPDF/Runtime error during OCR preparation for {pdf_path}: {fitz_err}", exc_info=True)
         raise RuntimeError(f"PyMuPDF/Runtime error during OCR: {fitz_err}") from fitz_err
    except Exception as e: # General catch for other unexpected errors
        logging.error(f"Unexpected error during OCR for {pdf_path}: {e}", exc_info=True)
        raise RuntimeError(f"Unexpected OCR error: {e}") from e
    finally:
        # Close document if it exists and is not already closed
        if doc is not None and not doc.is_closed:
            doc.close()
