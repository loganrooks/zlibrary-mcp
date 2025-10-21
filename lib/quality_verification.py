#!/usr/bin/env python3
"""
Quality Verification Module for RAG Processing

Compares processed markdown output against original PDF to verify:
- Page marker accuracy and placement
- Citation preservation (A/B citations, footnotes)
- Header extraction and hierarchy
- Text completeness and fidelity

Usage:
    from lib.quality_verification import verify_processing_quality

    report = verify_processing_quality(
        pdf_path="downloads/book.pdf",
        markdown_path="processed_rag_output/book.md",
        sample_every=50
    )

    print(f"Quality Score: {report['overall_score']}/100")
    print(f"Critical Issues: {len(report['issues']['critical'])}")
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from collections import Counter

try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError(
        "PyMuPDF (fitz) is required for quality verification. "
        "Install with: pip install PyMuPDF"
    )

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class QualityIssue:
    """Represents a single quality issue found during verification."""

    severity: str  # 'critical', 'high', 'medium', 'low'
    category: str  # 'page_markers', 'citations', 'headers', 'footnotes', 'content'
    description: str
    page_num: Optional[int] = None
    context: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'severity': self.severity,
            'category': self.category,
            'description': self.description,
            'page_num': self.page_num,
            'context': self.context
        }


@dataclass
class QualityReport:
    """Complete quality verification report."""

    overall_score: float  # 0-100
    content_similarity: float  # 0-1 average similarity
    pages_checked: int
    total_pages: int
    issues: Dict[str, List[QualityIssue]] = field(default_factory=lambda: {
        'critical': [],
        'high': [],
        'medium': [],
        'low': []
    })

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'overall_score': round(self.overall_score, 2),
            'content_similarity': round(self.content_similarity, 4),
            'pages_checked': self.pages_checked,
            'total_pages': self.total_pages,
            'issues': {
                severity: [issue.to_dict() for issue in issues]
                for severity, issues in self.issues.items()
            },
            'summary': {
                'critical_count': len(self.issues['critical']),
                'high_count': len(self.issues['high']),
                'medium_count': len(self.issues['medium']),
                'low_count': len(self.issues['low']),
                'total_issues': sum(len(issues) for issues in self.issues.values())
            }
        }


def generate_sample_pages(total_pages: int, sample_every: int = 50) -> List[int]:
    """
    Generate stratified sample of page numbers to verify.

    Includes:
    - First page (1)
    - Last page (total_pages)
    - Middle page (total_pages // 2)
    - Every Nth page based on sample_every

    Args:
        total_pages: Total number of pages in document
        sample_every: Sample every Nth page (default: 50)

    Returns:
        Sorted list of unique page numbers to sample
    """
    if total_pages <= 0:
        return []

    sample_pages = set()

    # Always include first, last, and middle
    sample_pages.add(1)
    sample_pages.add(total_pages)
    if total_pages > 2:
        sample_pages.add(total_pages // 2)

    # Add every Nth page
    if sample_every > 0:
        sample_pages.update(range(1, total_pages + 1, sample_every))

    # Ensure we don't exceed total pages
    sample_pages = {p for p in sample_pages if 1 <= p <= total_pages}

    logger.info(f"Sampling {len(sample_pages)} pages from {total_pages} total pages")

    return sorted(sample_pages)


def extract_pdf_page_for_comparison(pdf_path: str, page_num: int) -> Dict[str, Any]:
    """
    Extract PDF page content with metadata for comparison.

    Args:
        pdf_path: Path to PDF file
        page_num: Page number (1-indexed)

    Returns:
        Dict containing:
        - text: Extracted text content
        - blocks: Text blocks with position info
        - fonts: Font information
        - has_citations: Whether page contains citation markers
        - has_footnotes: Whether page contains footnote markers
    """
    try:
        doc = fitz.open(pdf_path)

        # Convert to 0-indexed
        page_idx = page_num - 1

        if page_idx < 0 or page_idx >= len(doc):
            logger.error(f"Page {page_num} out of range (1-{len(doc)})")
            return {
                'text': '',
                'blocks': [],
                'fonts': [],
                'has_citations': False,
                'has_footnotes': False
            }

        page = doc[page_idx]

        # Extract text
        text = page.get_text("text")

        # Extract blocks with position info
        blocks = page.get_text("dict")["blocks"]

        # Extract font information
        fonts = set()
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line.get("spans", []):
                        fonts.add(span.get("font", ""))

        # Detect citations (A/B pattern like "23A", "45B")
        has_citations = bool(re.search(r'\b\d+[A-Z]\b', text))

        # Detect footnote markers (letters in parentheses or superscript)
        has_footnotes = bool(re.search(r'\([a-z]\)|[a-z]\.(?=\s)', text, re.IGNORECASE))

        doc.close()

        return {
            'text': text,
            'blocks': blocks,
            'fonts': list(fonts),
            'has_citations': has_citations,
            'has_footnotes': has_footnotes
        }

    except Exception as e:
        logger.error(f"Error extracting PDF page {page_num}: {e}")
        return {
            'text': '',
            'blocks': [],
            'fonts': [],
            'has_citations': False,
            'has_footnotes': False
        }


def extract_markdown_section(markdown_path: str, page_num: int) -> str:
    """
    Extract markdown content between page markers.

    Looks for content between:
    [[PDF_page_N]] and [[PDF_page_N+1]]

    Args:
        markdown_path: Path to markdown file
        page_num: Page number to extract (1-indexed)

    Returns:
        Extracted markdown text for the page
    """
    try:
        with open(markdown_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find start marker
        start_pattern = rf'\[\[PDF_page_{page_num}\]\]'
        end_pattern = rf'\[\[PDF_page_{page_num + 1}\]\]'

        start_match = re.search(start_pattern, content)
        if not start_match:
            logger.warning(f"Start marker for page {page_num} not found")
            return ""

        start_pos = start_match.end()

        # Find end marker (next page)
        end_match = re.search(end_pattern, content[start_pos:])
        if end_match:
            end_pos = start_pos + end_match.start()
            section = content[start_pos:end_pos]
        else:
            # Last page - take everything to end
            section = content[start_pos:]

        return section.strip()

    except Exception as e:
        logger.error(f"Error extracting markdown section for page {page_num}: {e}")
        return ""


def compare_page_content(pdf_content: Dict[str, Any], md_content: str) -> Tuple[float, List[QualityIssue]]:
    """
    Compare PDF page content with markdown section.

    Uses difflib.SequenceMatcher to calculate similarity.

    Args:
        pdf_content: Dict from extract_pdf_page_for_comparison
        md_content: Markdown text from extract_markdown_section

    Returns:
        Tuple of (similarity_score, list_of_issues)
        - similarity_score: 0-1 float
        - issues: List of QualityIssue objects
    """
    issues = []

    pdf_text = pdf_content.get('text', '')

    if not pdf_text:
        issues.append(QualityIssue(
            severity='critical',
            category='content',
            description='PDF page has no extractable text'
        ))
        return 0.0, issues

    if not md_content:
        issues.append(QualityIssue(
            severity='critical',
            category='content',
            description='Markdown section is empty'
        ))
        return 0.0, issues

    # Clean texts for comparison (normalize whitespace)
    pdf_clean = re.sub(r'\s+', ' ', pdf_text).strip()
    md_clean = re.sub(r'\s+', ' ', md_content).strip()

    # Calculate similarity
    matcher = SequenceMatcher(None, pdf_clean, md_clean)
    similarity = matcher.ratio()

    # Flag low similarity
    if similarity < 0.7:
        issues.append(QualityIssue(
            severity='high',
            category='content',
            description=f'Low content similarity: {similarity:.2%}',
            context=f'PDF length: {len(pdf_clean)}, MD length: {len(md_clean)}'
        ))
    elif similarity < 0.85:
        issues.append(QualityIssue(
            severity='medium',
            category='content',
            description=f'Moderate content similarity: {similarity:.2%}'
        ))

    # Check length ratio
    length_ratio = len(md_clean) / len(pdf_clean) if pdf_clean else 0
    if length_ratio < 0.5:
        issues.append(QualityIssue(
            severity='high',
            category='content',
            description=f'Markdown significantly shorter than PDF ({length_ratio:.1%})'
        ))
    elif length_ratio > 2.0:
        issues.append(QualityIssue(
            severity='medium',
            category='content',
            description=f'Markdown significantly longer than PDF ({length_ratio:.1%})'
        ))

    return similarity, issues


def detect_page_number_duplication(md_text: str, page_num: int) -> List[QualityIssue]:
    """
    Detect if page numbers appear duplicated in markdown body.

    Checks for patterns like:
    - "Page 23" in body text
    - Page numbers at start/end of lines
    - Repeated page number patterns

    Args:
        md_text: Markdown section text
        page_num: Expected page number

    Returns:
        List of QualityIssue objects
    """
    issues = []

    # Pattern: "Page N" or just "N" at line boundaries
    page_patterns = [
        rf'\bPage\s+{page_num}\b',
        rf'^{page_num}\s*$',
        rf'\s{page_num}\s*$'
    ]

    for pattern in page_patterns:
        matches = re.finditer(pattern, md_text, re.MULTILINE | re.IGNORECASE)
        for match in matches:
            context_start = max(0, match.start() - 30)
            context_end = min(len(md_text), match.end() + 30)
            context = md_text[context_start:context_end]

            issues.append(QualityIssue(
                severity='medium',
                category='page_markers',
                description=f'Page number {page_num} appears in body text',
                page_num=page_num,
                context=context.strip()
            ))

    return issues


def detect_missing_citations(pdf_text: str, md_text: str, page_num: int) -> List[QualityIssue]:
    """
    Detect missing citation markers (A/B citations, footnote markers).

    Args:
        pdf_text: Original PDF text
        md_text: Markdown text
        page_num: Page number for context

    Returns:
        List of QualityIssue objects
    """
    issues = []

    # Find A/B citations in PDF (pattern: number followed by letter like "23A")
    pdf_citations = set(re.findall(r'\b(\d+[A-Z])\b', pdf_text))
    md_citations = set(re.findall(r'\b(\d+[A-Z])\b', md_text))

    missing_citations = pdf_citations - md_citations
    if missing_citations:
        issues.append(QualityIssue(
            severity='high',
            category='citations',
            description=f'Missing A/B citations: {", ".join(sorted(missing_citations))}',
            page_num=page_num
        ))

    # Find footnote markers in PDF (pattern: letter in parens or letter with period)
    pdf_footnotes = set(re.findall(r'\(([a-z])\)|([a-z])\.(?=\s)', pdf_text, re.IGNORECASE))
    # Flatten tuples from alternation
    pdf_footnotes = {item for tup in pdf_footnotes for item in tup if item}

    md_footnotes = set(re.findall(r'\(([a-z])\)|([a-z])\.(?=\s)', md_text, re.IGNORECASE))
    md_footnotes = {item for tup in md_footnotes for item in tup if item}

    missing_footnotes = pdf_footnotes - md_footnotes
    if missing_footnotes:
        issues.append(QualityIssue(
            severity='high',
            category='footnotes',
            description=f'Missing footnote markers: {", ".join(sorted(missing_footnotes))}',
            page_num=page_num
        ))

    return issues


def detect_header_issues(md_text: str, page_num: int) -> List[QualityIssue]:
    """
    Detect header hierarchy and formatting issues.

    Checks for:
    - Split headers (header text broken across lines)
    - Wrong header levels (e.g., ### when ## expected)
    - Headers that look like body text

    Args:
        md_text: Markdown section text
        page_num: Page number for context

    Returns:
        List of QualityIssue objects
    """
    issues = []

    # Find all headers
    headers = re.findall(r'^(#{1,6})\s+(.+)$', md_text, re.MULTILINE)

    if not headers:
        return issues  # No headers on this page is fine

    # Check for headers followed immediately by another header (possible split)
    lines = md_text.split('\n')
    for i, line in enumerate(lines):
        if re.match(r'^#{1,6}\s+', line):
            # Check if next line is also a header
            if i + 1 < len(lines) and re.match(r'^#{1,6}\s+', lines[i + 1]):
                issues.append(QualityIssue(
                    severity='medium',
                    category='headers',
                    description='Consecutive headers detected (possible split header)',
                    page_num=page_num,
                    context=f"{line}\n{lines[i + 1]}"
                ))

    # Check for suspicious header hierarchy (skip from ### to #)
    header_levels = [len(level) for level, _ in headers]
    for i in range(len(header_levels) - 1):
        level_jump = header_levels[i + 1] - header_levels[i]
        if level_jump < -2:  # e.g., ### to #
            issues.append(QualityIssue(
                severity='low',
                category='headers',
                description=f'Large header level jump: {"#" * header_levels[i]} to {"#" * header_levels[i + 1]}',
                page_num=page_num
            ))

    # Check for very short headers (< 3 chars) which might be extraction errors
    for level, text in headers:
        if len(text.strip()) < 3:
            issues.append(QualityIssue(
                severity='low',
                category='headers',
                description=f'Suspiciously short header: "{text.strip()}"',
                page_num=page_num
            ))

    return issues


def detect_footnote_issues(pdf_text: str, md_text: str, page_num: int) -> List[QualityIssue]:
    """
    Detect footnote handling issues.

    Checks for:
    - Letter footnotes merged into body text
    - Missing footnote content
    - Footnotes in wrong location

    Args:
        pdf_text: Original PDF text
        md_text: Markdown text
        page_num: Page number for context

    Returns:
        List of QualityIssue objects
    """
    issues = []

    # Count footnote markers in each
    pdf_markers = len(re.findall(r'\([a-z]\)', pdf_text, re.IGNORECASE))
    md_markers = len(re.findall(r'\([a-z]\)', md_text, re.IGNORECASE))

    if pdf_markers > md_markers:
        issues.append(QualityIssue(
            severity='high',
            category='footnotes',
            description=f'Missing footnote markers: PDF has {pdf_markers}, MD has {md_markers}',
            page_num=page_num
        ))

    # Check for footnote content patterns (usually at bottom of page)
    # Pattern: letter followed by period and text
    pdf_footnote_content = re.findall(r'^([a-z])\.\s+(.{10,})', pdf_text, re.MULTILINE | re.IGNORECASE)
    md_footnote_content = re.findall(r'^([a-z])\.\s+(.{10,})', md_text, re.MULTILINE | re.IGNORECASE)

    if len(pdf_footnote_content) > len(md_footnote_content):
        issues.append(QualityIssue(
            severity='medium',
            category='footnotes',
            description=f'Possible missing footnote content (PDF: {len(pdf_footnote_content)}, MD: {len(md_footnote_content)})',
            page_num=page_num
        ))

    return issues


def calculate_quality_score(
    issues: Dict[str, List[QualityIssue]],
    avg_similarity: float,
    total_pages: int
) -> float:
    """
    Calculate overall quality score (0-100).

    Scoring:
    - Start with 100
    - Subtract weighted penalties for issues
    - Adjust based on content similarity

    Weights:
    - critical: 10 points each
    - high: 5 points each
    - medium: 2 points each
    - low: 1 point each

    Args:
        issues: Dict of issues by severity
        avg_similarity: Average content similarity (0-1)
        total_pages: Total pages in document

    Returns:
        Quality score from 0-100
    """
    score = 100.0

    # Severity weights (points to deduct)
    weights = {
        'critical': 10.0,
        'high': 5.0,
        'medium': 2.0,
        'low': 1.0
    }

    # Deduct points for issues
    for severity, issue_list in issues.items():
        penalty = len(issue_list) * weights.get(severity, 1.0)
        score -= penalty

    # Adjust based on average similarity
    # If similarity < 0.85, deduct up to 20 points
    if avg_similarity < 0.85:
        similarity_penalty = (0.85 - avg_similarity) * 100  # Scale to 0-85
        score -= min(similarity_penalty, 20)

    # Ensure score doesn't go below 0
    score = max(0, score)

    return score


def verify_processing_quality(
    pdf_path: str,
    markdown_path: str,
    sample_every: int = 50
) -> Dict[str, Any]:
    """
    Main entry point for quality verification.

    Orchestrates the entire verification process:
    1. Generate sample pages
    2. Extract and compare each page
    3. Run all issue detection checks
    4. Calculate quality score
    5. Return comprehensive report

    Args:
        pdf_path: Path to original PDF file
        markdown_path: Path to processed markdown file
        sample_every: Sample every Nth page (default: 50)

    Returns:
        Dict representation of QualityReport
    """
    logger.info(f"Starting quality verification: {pdf_path} -> {markdown_path}")

    # Validate paths
    if not Path(pdf_path).exists():
        logger.error(f"PDF file not found: {pdf_path}")
        return {
            'error': 'PDF file not found',
            'overall_score': 0,
            'issues': {'critical': [{'description': 'PDF file not found'}]}
        }

    if not Path(markdown_path).exists():
        logger.error(f"Markdown file not found: {markdown_path}")
        return {
            'error': 'Markdown file not found',
            'overall_score': 0,
            'issues': {'critical': [{'description': 'Markdown file not found'}]}
        }

    # Get total pages
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()
    except Exception as e:
        logger.error(f"Error opening PDF: {e}")
        return {
            'error': f'Error opening PDF: {e}',
            'overall_score': 0,
            'issues': {'critical': [{'description': f'Error opening PDF: {e}'}]}
        }

    # Generate sample pages
    sample_pages = generate_sample_pages(total_pages, sample_every)

    # Initialize report
    report = QualityReport(
        overall_score=0.0,
        content_similarity=0.0,
        pages_checked=len(sample_pages),
        total_pages=total_pages
    )

    similarities = []

    # Process each sample page
    for page_num in sample_pages:
        logger.debug(f"Verifying page {page_num}/{total_pages}")

        # Extract content
        pdf_content = extract_pdf_page_for_comparison(pdf_path, page_num)
        md_content = extract_markdown_section(markdown_path, page_num)

        # Compare content
        similarity, content_issues = compare_page_content(pdf_content, md_content)
        similarities.append(similarity)

        for issue in content_issues:
            issue.page_num = page_num
            report.issues[issue.severity].append(issue)

        # Run all detection checks
        detection_checks = [
            detect_page_number_duplication(md_content, page_num),
            detect_missing_citations(pdf_content['text'], md_content, page_num),
            detect_header_issues(md_content, page_num),
            detect_footnote_issues(pdf_content['text'], md_content, page_num)
        ]

        for issues in detection_checks:
            for issue in issues:
                report.issues[issue.severity].append(issue)

    # Calculate metrics
    report.content_similarity = sum(similarities) / len(similarities) if similarities else 0.0
    report.overall_score = calculate_quality_score(
        report.issues,
        report.content_similarity,
        total_pages
    )

    logger.info(
        f"Verification complete. Score: {report.overall_score}/100, "
        f"Similarity: {report.content_similarity:.2%}, "
        f"Issues: {sum(len(issues) for issues in report.issues.values())}"
    )

    return report.to_dict()


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 3:
        print("Usage: python quality_verification.py <pdf_path> <markdown_path> [sample_every]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    markdown_path = sys.argv[2]
    sample_every = int(sys.argv[3]) if len(sys.argv) > 3 else 50

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run verification
    report = verify_processing_quality(pdf_path, markdown_path, sample_every)

    # Print summary
    print("\n" + "=" * 60)
    print("QUALITY VERIFICATION REPORT")
    print("=" * 60)
    print(f"Overall Score: {report['overall_score']}/100")
    print(f"Content Similarity: {report['content_similarity']:.2%}")
    print(f"Pages Checked: {report['pages_checked']}/{report['total_pages']}")
    print("\nIssue Summary:")
    for severity in ['critical', 'high', 'medium', 'low']:
        count = len(report['issues'][severity])
        if count > 0:
            print(f"  {severity.upper()}: {count}")

    # Print details if there are issues
    if report.get('summary', {}).get('total_issues', 0) > 0:
        print("\nDetailed Issues:")
        for severity in ['critical', 'high', 'medium', 'low']:
            issues = report['issues'][severity]
            if issues:
                print(f"\n{severity.upper()}:")
                for issue in issues[:5]:  # Show first 5 of each severity
                    page_info = f" (page {issue['page_num']})" if issue['page_num'] else ""
                    print(f"  - {issue['description']}{page_info}")
                if len(issues) > 5:
                    print(f"  ... and {len(issues) - 5} more")
