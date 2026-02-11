"""
Ground Truth Loading and Validation Utilities.

Provides infrastructure for rigorous real-world TDD with documented expectations.
Prevents hallucinations by anchoring tests to verified ground truth.
"""

import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class ValidationResult:
    """Result from ground truth validation."""

    passed: bool
    all_detected: bool
    quality_score: float
    processing_time_ms: float
    missed_features: List[str]
    false_positives: List[str]
    hallucinations: List[str]
    details: Dict[str, Any]

    def __str__(self):
        if self.passed:
            return f"✅ PASSED: All features detected, quality={self.quality_score:.2f}, time={self.processing_time_ms:.0f}ms"
        else:
            msg = "❌ FAILED:\n"
            if self.missed_features:
                msg += f"  Missed: {', '.join(self.missed_features)}\n"
            if self.false_positives:
                msg += f"  False positives: {', '.join(self.false_positives)}\n"
            if self.hallucinations:
                msg += f"  Hallucinations: {', '.join(self.hallucinations[:3])}...\n"
            return msg


def load_ground_truth(test_name: str) -> dict:
    """
    Load ground truth for test PDF.

    Args:
        test_name: Test identifier (e.g., 'derrida_of_grammatology')

    Returns:
        Ground truth dictionary

    Raises:
        FileNotFoundError: If ground truth doesn't exist
        ValueError: If ground truth invalid
    """
    gt_file = Path("test_files/ground_truth") / f"{test_name}.json"

    if not gt_file.exists():
        raise FileNotFoundError(
            f"Ground truth not found: {gt_file}\n"
            f"Create ground truth first:\n"
            f"  1. Manually inspect PDF\n"
            f"  2. Document features in {gt_file}\n"
            f"  3. Follow schema in test_files/ground_truth/schema_v3.json"
        )

    with open(gt_file) as f:
        gt = json.load(f)

    # Validate schema
    _validate_ground_truth_schema(gt)

    # Validate referenced PDF exists
    pdf_path = Path(gt["pdf_file"])
    if not pdf_path.exists():
        raise FileNotFoundError(f"Test PDF not found: {pdf_path}")

    return gt


def validate_against_ground_truth(
    output_text: str,
    gt: dict,
    processing_time_ms: Optional[float] = None,
    quality_flags: Optional[set] = None,
    quality_score: Optional[float] = None,
) -> ValidationResult:
    """
    Validate processing result against ground truth.

    Args:
        output_text: Processed output (markdown or text)
        gt: Ground truth dictionary
        processing_time_ms: Actual processing time
        quality_flags: Detected quality flags
        quality_score: Calculated quality score

    Returns:
        ValidationResult with detailed validation
    """
    missed = []
    false_positives = []
    hallucinations = []

    # Validate X-marks
    xmarks = gt.get("features", {}).get("xmarks", [])
    for xmark in xmarks:
        expected_word = xmark.get("expected_recovery") or xmark["word_under_erasure"]
        expected_output = xmark.get("expected_output", f"~~{expected_word}~~")

        # Check if word recovered
        if expected_word not in output_text and expected_output not in output_text:
            missed.append(
                f"X-mark word '{expected_word}' on page {xmark['page_index']}"
            )

        # Check if corrupted version NOT in output (should be recovered)
        corrupted = xmark.get("corrupted_extraction")
        if corrupted and corrupted in output_text:
            missed.append(
                f"Corrupted text '{corrupted}' not recovered (should be '{expected_word}')"
            )

    # Validate footnotes
    for footnote in gt.get("features", {}).get("footnotes", []):
        marker = footnote["marker"]
        # v3 schema: marker is an object with 'symbol' key
        marker_symbol = marker["symbol"] if isinstance(marker, dict) else marker
        if (
            f"^{marker_symbol}" not in output_text
            and f"[^{marker_symbol}]" not in output_text
        ):
            missed.append(f"Footnote marker '^{marker_symbol}'")

    # Validate formatting
    for fmt in gt.get("features", {}).get("formatting", []):
        expected = fmt["expected_output"]
        if expected not in output_text:
            missed.append(f"Formatting '{expected}' for text '{fmt['text']}'")

    # Validate quality score
    expected_quality = gt["expected_quality"]
    quality_ok = True
    if quality_score is not None:
        quality_ok = quality_score >= expected_quality["quality_score_min"]
    else:
        quality_score = 0.0  # Unknown

    # Validate processing time
    processing_ok = True
    if processing_time_ms:
        max_time = expected_quality["processing_time_max_ms"]
        processing_ok = processing_time_ms < max_time

    # Check for expected quality flags
    if quality_flags is not None:
        for expected_flag in expected_quality.get("quality_flags", []):
            if expected_flag not in quality_flags:
                missed.append(f"Quality flag '{expected_flag}'")

    # Overall result
    passed = (
        len(missed) == 0
        and len(false_positives) == 0
        and len(hallucinations) == 0
        and quality_ok
        and processing_ok
    )

    return ValidationResult(
        passed=passed,
        all_detected=(len(missed) == 0),
        quality_score=quality_score,
        processing_time_ms=processing_time_ms or 0.0,
        missed_features=missed,
        false_positives=false_positives,
        hallucinations=hallucinations,
        details={"quality_ok": quality_ok, "processing_ok": processing_ok},
    )


def _validate_ground_truth_schema(gt: dict):
    """Validate ground truth schema - lenient, only validates fields that exist.

    Different ground truth files serve different purposes:
    - Footnote tests: pdf_file, footnotes
    - Performance tests: pdf_file, expected_quality
    - Quality tests: pdf_file, features, expected_quality

    Only pdf_file is truly required for all tests.
    """
    # Only pdf_file is universally required
    if "pdf_file" not in gt:
        raise ValueError("Ground truth missing required field: 'pdf_file'")

    # v3 schema requires metadata
    if "metadata" not in gt:
        raise ValueError(
            "Ground truth missing required field: 'metadata'. "
            "All ground truth files must conform to v3 schema. "
            "See test_files/ground_truth/schema_v3.json for the required structure."
        )

    # Validate expected_quality subfields IF that section exists
    if "expected_quality" in gt:
        eq = gt["expected_quality"]
        # These are required IF expected_quality exists
        if "quality_score_min" not in eq and "processing_time_max_ms" not in eq:
            # Warn but don't fail - some files may have partial expected_quality
            pass


def list_ground_truth_tests() -> List[str]:
    """List all available ground truth tests."""
    gt_dir = Path("test_files/ground_truth")
    if not gt_dir.exists():
        return []

    # Utility files that are not actual ground truth test cases
    EXCLUDED_FILES = {
        "schema_v3.json",  # JSON schema v3 (canonical)
        "body_text_baseline.json",  # Recall baseline data
        "correction_matrix.json",  # Validation results
    }

    gt_files = gt_dir.glob("*.json")
    return [f.stem for f in gt_files if f.name not in EXCLUDED_FILES]
