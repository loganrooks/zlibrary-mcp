#!/usr/bin/env python3
"""Generate recall baseline snapshot of process_pdf() output for all test PDFs."""

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from lib.rag.orchestrator_pdf import process_pdf


def main():
    test_files_dir = project_root / "test_files"
    ground_truth_dir = test_files_dir / "ground_truth"
    baseline_texts_dir = ground_truth_dir / "baseline_texts"
    baseline_texts_dir.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(test_files_dir.glob("*.pdf"))
    print(f"Found {len(pdfs)} PDFs")

    baselines = {}
    for pdf_path in pdfs:
        print(f"Processing {pdf_path.name}...", end=" ", flush=True)
        try:
            text = process_pdf(pdf_path, output_format="markdown")
            if not text or not text.strip():
                print("EMPTY OUTPUT, skipping")
                continue

            lines = text.split("\n")
            non_empty_lines = [l for l in lines if l.strip()]
            text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

            baselines[pdf_path.name] = {
                "body_text_length": len(text),
                "body_text_hash": f"sha256:{text_hash}",
                "line_count": len(lines),
                "non_empty_line_count": len(non_empty_lines),
                "sample_lines": [l for l in non_empty_lines[:3]],
            }

            # Save full text
            (baseline_texts_dir / f"{pdf_path.name}.txt").write_text(
                text, encoding="utf-8"
            )
            print(f"OK ({len(text)} chars, {len(lines)} lines)")

        except Exception as e:
            print(f"FAILED: {e}")
            continue

    result = {
        "generated": str(date.today()),
        "description": "Recall baseline: process_pdf() body text output before Phase 11 refactoring",
        "baselines": baselines,
    }

    output_path = ground_truth_dir / "body_text_baseline.json"
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nBaseline saved: {output_path}")
    print(f"Covers {len(baselines)} PDFs")


if __name__ == "__main__":
    main()
