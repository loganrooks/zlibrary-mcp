"""Recall regression tests: ensure no body text is lost during Phase 11 refactoring."""

import json
import re
import sys
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.rag.orchestrator_pdf import process_pdf

pytestmark = [pytest.mark.slow, pytest.mark.ground_truth]

BASELINE_PATH = PROJECT_ROOT / "test_files" / "ground_truth" / "body_text_baseline.json"
BASELINE_TEXTS_DIR = PROJECT_ROOT / "test_files" / "ground_truth" / "baseline_texts"
TEST_FILES_DIR = PROJECT_ROOT / "test_files"


def load_baseline():
    """Load baseline JSON and return (pdf_name, info) pairs for parametrize."""
    if not BASELINE_PATH.exists():
        pytest.skip(
            "Baseline JSON not found; run scripts/generate_recall_baseline.py first"
        )
    with open(BASELINE_PATH) as f:
        data = json.load(f)
    return list(data["baselines"].items())


def normalize_line(line: str) -> str:
    """Normalize a line for fuzzy matching: strip, lowercase, collapse whitespace."""
    line = line.strip().lower()
    line = re.sub(r"\s+", " ", line)
    return line


def is_structural_line(line: str) -> bool:
    """Check if a line is generated structural content (TOC links, navigation).

    These lines are non-deterministic between runs due to TOC detection
    variability and should be excluded from recall comparison.
    Body text recall is what matters.
    """
    normalized = line.strip().lower()
    # TOC markdown links: * [Title](#anchor) or ](#anchor-text)
    if re.match(r"^\* \[", normalized):
        return True
    if re.match(r"^]\(#", normalized):
        return True
    # Standalone anchor references
    if re.match(r"^#[a-z0-9-]+\)?", normalized):
        return True
    return False


def get_pdf_ids():
    """Return list of (pdf_name, info) for parametrize, or empty if no baseline."""
    if not BASELINE_PATH.exists():
        return []
    with open(BASELINE_PATH) as f:
        data = json.load(f)
    return list(data["baselines"].items())


PDF_IDS = get_pdf_ids()


@pytest.mark.slow
@pytest.mark.parametrize(
    "pdf_name,baseline_info",
    PDF_IDS,
    ids=[item[0] for item in PDF_IDS] if PDF_IDS else [],
)
def test_no_body_text_recall_loss(pdf_name, baseline_info):
    """Every non-empty line in the baseline must appear in current output."""
    pdf_path = TEST_FILES_DIR / pdf_name
    if not pdf_path.exists():
        pytest.skip(f"PDF {pdf_name} no longer exists in test_files/")

    baseline_text_path = BASELINE_TEXTS_DIR / f"{pdf_name}.txt"
    if not baseline_text_path.exists():
        pytest.skip(f"Baseline text file missing for {pdf_name}")

    # Get current output
    current_text = process_pdf(pdf_path, output_format="markdown")

    # Load baseline text
    baseline_text = baseline_text_path.read_text(encoding="utf-8")

    # Normalize lines for comparison, excluding non-deterministic structural lines
    baseline_lines = {
        normalize_line(l)
        for l in baseline_text.split("\n")
        if l.strip() and not is_structural_line(l)
    }
    current_lines = {
        normalize_line(l)
        for l in current_text.split("\n")
        if l.strip() and not is_structural_line(l)
    }

    # Find lost lines (in baseline but not in current)
    lost_lines = baseline_lines - current_lines
    if lost_lines:
        sample = list(lost_lines)[:10]
        pytest.fail(
            f"RECALL LOSS in {pdf_name}: {len(lost_lines)} lines lost out of "
            f"{len(baseline_lines)} baseline lines.\n"
            f"Sample lost lines:\n" + "\n".join(f"  - {l}" for l in sample)
        )


@pytest.mark.slow
@pytest.mark.parametrize(
    "pdf_name,baseline_info",
    PDF_IDS,
    ids=[item[0] for item in PDF_IDS] if PDF_IDS else [],
)
def test_body_text_not_shorter(pdf_name, baseline_info):
    """Current body text length must be >= 95% of baseline length."""
    pdf_path = TEST_FILES_DIR / pdf_name
    if not pdf_path.exists():
        pytest.skip(f"PDF {pdf_name} no longer exists in test_files/")

    current_text = process_pdf(pdf_path, output_format="markdown")
    baseline_length = baseline_info["body_text_length"]
    current_length = len(current_text)

    threshold = 0.95
    if current_length < baseline_length * threshold:
        pytest.fail(
            f"GROSS RECALL LOSS in {pdf_name}: current={current_length} chars, "
            f"baseline={baseline_length} chars "
            f"({current_length / baseline_length:.1%} of baseline, threshold={threshold:.0%})"
        )
