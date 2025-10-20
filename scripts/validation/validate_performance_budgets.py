#!/usr/bin/env python3
"""
Validate Performance Budgets - Quality Gate.

Ensures all operations meet performance budgets defined in:
test_files/performance_budgets.json

Used by:
- Pre-commit hooks (local validation)
- CI/CD pipeline (automated gates)
- Manual verification (development)

Exit codes:
  0: All budgets met ✅
  1: Budget violations detected ❌
"""

import json
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.rag_processing import process_pdf
from lib.garbled_text_detection import detect_garbled_text_enhanced, GarbledDetectionConfig


def load_budgets():
    """Load performance budgets."""
    budget_file = Path('test_files/performance_budgets.json')

    if not budget_file.exists():
        print(f"⚠️  Performance budgets not found: {budget_file}")
        return None

    with open(budget_file) as f:
        return json.load(f)


def validate_operation_budgets(budgets):
    """Validate individual operation performance."""
    violations = []

    ops = budgets.get('operations', {})

    # Test garbled detection
    if 'garbled_detection_per_region' in ops:
        budget = ops['garbled_detection_per_region']
        text = "Sample philosophical text for testing" * 100

        start = time.perf_counter()
        for _ in range(100):
            detect_garbled_text_enhanced(text, GarbledDetectionConfig())
        elapsed_ms = (time.perf_counter() - start) / 100 * 1000

        if elapsed_ms > budget['max_ms']:
            violations.append(
                f"Garbled detection: {elapsed_ms:.2f}ms > {budget['max_ms']}ms budget"
            )
        else:
            print(f"✅ Garbled detection: {elapsed_ms:.2f}ms (budget: {budget['max_ms']}ms)")

    # TODO: Add more operation-level benchmarks

    return violations


def validate_end_to_end_budgets(budgets):
    """Validate end-to-end processing performance."""
    violations = []

    e2e = budgets.get('end_to_end', {})

    # Test small PDF
    if 'small_pdf_26_pages' in e2e:
        budget = e2e['small_pdf_26_pages']
        pdf_path = Path('test_files/derrida_pages_110_135.pdf')

        if pdf_path.exists():
            start = time.time()
            try:
                result = process_pdf(pdf_path, output_format='markdown')
                elapsed_ms = (time.time() - start) * 1000

                if elapsed_ms > budget['max_ms']:
                    violations.append(
                        f"Small PDF processing: {elapsed_ms:.0f}ms > {budget['max_ms']}ms budget"
                    )
                else:
                    print(f"✅ Small PDF: {elapsed_ms:.0f}ms (budget: {budget['max_ms']}ms)")

            except Exception as e:
                violations.append(f"Small PDF processing failed: {e}")
        else:
            print(f"⚠️  Test PDF not found: {pdf_path}")

    return violations


def main():
    """Run all performance budget validations."""
    print("="*80)
    print(" Performance Budget Validation")
    print("="*80)
    print()

    budgets = load_budgets()
    if not budgets:
        print("❌ Cannot load budgets")
        sys.exit(1)

    all_violations = []

    # Validate operations
    print("Validating operation-level budgets...")
    op_violations = validate_operation_budgets(budgets)
    all_violations.extend(op_violations)

    print()

    # Validate end-to-end
    print("Validating end-to-end budgets...")
    e2e_violations = validate_end_to_end_budgets(budgets)
    all_violations.extend(e2e_violations)

    print()
    print("="*80)

    if all_violations:
        print("❌ BUDGET VIOLATIONS DETECTED:")
        print()
        for violation in all_violations:
            print(f"  {violation}")
        print()
        print("Performance regression detected - fix before merging!")
        print("="*80)
        sys.exit(1)
    else:
        print("✅ ALL PERFORMANCE BUDGETS MET")
        print("="*80)
        sys.exit(0)


if __name__ == '__main__':
    main()
