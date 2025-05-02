#!/usr/bin/env python3

"""
Script to run the RAG Real-World Testing Framework.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import difflib # Cycle 20 Refactor: Added import (Retry)
import re
from typing import Dict, Any, Callable, Optional, List
import logging # Added logging import

# Ensure lib directory is in path if running script directly
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import processors needed for the main function
from lib.rag_processing import process_pdf, process_epub, process_txt
# Import the download function (assuming location)
from lib.python_bridge import download_book


def load_manifest(manifest_path):
    """Loads the test manifest JSON file."""
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Manifest file not found at {manifest_path}", file=sys.stderr)
        raise # Re-raise the exception to be caught by the test
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in manifest file {manifest_path}: {e}", file=sys.stderr)
        raise # Re-raise the exception to be caught by the test
    except Exception as e:
        print(f"An unexpected error occurred while loading the manifest: {e}", file=sys.stderr)
        raise # Re-raise for unexpected errors

def evaluate_output(
    processed_text: Optional[str],
    format_type: str,
    document_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluates the quality of the processed text or markdown output.

    Args:
        processed_text: The extracted text or generated markdown content.
                        Can be None if processing failed.
        format_type: The type of content ('text' or 'markdown').
        document_metadata: Metadata about the original document.

    Returns:
        A dictionary containing evaluation metrics.
        Returns {"error": "No content to evaluate"} if processed_text is None.
    """
    if processed_text is None:
        return {"error": "No content to evaluate"}

    metrics = {}

    # Cycle 7 Green: Add text length metric
    metrics["text_length"] = len(processed_text)

    # Cycle 8 Green: Add word count metric
    metrics["word_count"] = len(processed_text.split())

    # Cycle 11 Green: Basic noise detection
    noise_patterns = ["Header", "Footer", "Page \\d+"] # Simple patterns
    metrics["noise_detected"] = any(re.search(pattern, processed_text, re.IGNORECASE) for pattern in noise_patterns)

    # TODO: Implement other evaluation metrics based on spec
    #       (e.g., markdown structure checks, AI eval call)

    # Cycle 20 Refactor: Implement Markdown heading accuracy calculation
    if format_type == "markdown":
        ground_truth_headings = document_metadata.get("ground_truth_headings", [])
        extracted_headings = []
        if processed_text:
            # Regex to find markdown headings (# Heading Text)
            heading_pattern = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)
            for match in heading_pattern.finditer(processed_text):
                level = len(match.group(1))
                text = match.group(2).strip()
                extracted_headings.append((level, text))

        if not ground_truth_headings:
            # No ground truth provided, accuracy is undefined/not applicable
            metrics["markdown_heading_accuracy"] = None
        elif not extracted_headings and ground_truth_headings:
             # Ground truth exists, but nothing extracted -> 0% accuracy
             metrics["markdown_heading_accuracy"] = 0.0
        elif not ground_truth_headings and extracted_headings:
             # Headings extracted, but no ground truth -> Undefined/Not applicable
             metrics["markdown_heading_accuracy"] = None
        else:
            # Use difflib SequenceMatcher for robust comparison
            # Convert tuples to simple strings for matching
            gt_str = [f"{lvl}-{txt}" for lvl, txt in ground_truth_headings]
            ext_str = [f"{lvl}-{txt}" for lvl, txt in extracted_headings]

            seq_matcher = difflib.SequenceMatcher(None, gt_str, ext_str)
            accuracy = seq_matcher.ratio() # Similarity ratio (0.0 to 1.0)
            metrics["markdown_heading_accuracy"] = accuracy

    return metrics

def determine_pass_fail(results: Dict[str, Any]) -> str:
    """
    Determines the overall pass/fail status for a document test based on evaluation metrics.
    Checks for errors, detected noise, and minimum text length.
    """
    text_eval = results.get("text_eval", {})
    md_eval = results.get("markdown_eval", {})

    # --- Failure Condition Checks ---

    # 1. Check for processing or evaluation errors
    if "error" in text_eval or "error" in md_eval:
        return "FAIL" # Fail immediately if any error occurred

    # 2. Check for detected noise (e.g., headers, footers)
    if text_eval.get("noise_detected", False) or md_eval.get("noise_detected", False):
        return "FAIL" # Fail if noise was detected in either output

    # 3. Check for minimum text length
    # TODO: Make threshold configurable (FR-CONF-01)
    MIN_TEXT_LENGTH_THRESHOLD = 10
    if (text_eval.get("text_length", MIN_TEXT_LENGTH_THRESHOLD) < MIN_TEXT_LENGTH_THRESHOLD or
        md_eval.get("text_length", MIN_TEXT_LENGTH_THRESHOLD) < MIN_TEXT_LENGTH_THRESHOLD):
        # Using get with default ensures it fails if key missing or value is < threshold
        return "FAIL" # Fail if either output is too short

    # --- Pass Condition ---
    # If none of the failure conditions were met, the test passes.
    # TODO: Add more sophisticated pass criteria based on metrics (FR-TEST-12)
    return "PASS"


async def run_single_test( # Make the function async
    document_metadata: Dict[str, Any],
    output_dir: str, # Directory for results/reports
    download_dir: str, # Directory specifically for downloads
    processor_map: Dict[str, Callable[[Path, str], Optional[str]]], # Injected dependency
    evaluate_func: Callable[[Optional[str], str, Dict[str, Any]], Dict[str, Any]], # Injected dependency
    pass_fail_func: Callable[[Dict[str, Any]], str] # Injected dependency
) -> Dict[str, Any]:
    """Runs the RAG processing and evaluation for a single document."""
    doc_id: str = document_metadata.get("id", "unknown_id")
    doc_format: str = document_metadata.get("format", "unknown")
    # Prioritize local_sample_path for now as per spec
    doc_path_str: Optional[str] = document_metadata.get("local_sample_path")
    downloaded_this_run = False

    if not doc_path_str:
        # Try downloading if ID and format are present
        if doc_id != "unknown_id" and doc_format != "unknown":
            print(f"  No local path for {doc_id}, attempting download...")
            try:
                # Ensure download directory exists
                Path(download_dir).mkdir(parents=True, exist_ok=True)
                # Construct book_details dict for download_book function
                book_details_for_download = {
                    "id": doc_id,
                    "url": document_metadata.get("url") # Pass URL if available
                    # Add other necessary keys if download_book requires them
                }
                download_result = await download_book( # Await the async call
                    book_details=book_details_for_download, # Pass book_details dict
                    output_dir=download_dir,
                )
                doc_path_str = download_result.get("file_path") # Extract file_path
                if doc_path_str:
                    print(f"  Downloaded {doc_id} to {doc_path_str}")
                    downloaded_this_run = True
                else:
                    # download_book might return None on failure before raising error
                    raise RuntimeError("Download function returned None")
            except Exception as download_error:
                print(f"Error: Failed to download {doc_id}: {download_error}", file=sys.stderr)
                return {"id": doc_id, "status": "FAIL", "reason": f"Download failed: {download_error}"}
        else:
            # Still skip if no local path AND no ID/format for download
            print(f"Warning: Skipping doc ID {doc_id} - no local_sample_path and missing id/format for download.", file=sys.stderr)
            return {"id": doc_id, "status": "SKIPPED", "reason": "No local_sample_path or id/format"}

    # Proceed if we have a path (either local or downloaded)
    doc_path: Path = Path(doc_path_str)
    if not doc_path.exists():
         # This check is important even after download, in case download_book returns a non-existent path
         print(f"Error: Skipping doc ID {doc_id} - file path does not exist: {doc_path_str}", file=sys.stderr)
         return {"id": doc_id, "status": "FAIL", "reason": f"File not found after potential download: {doc_path_str}"}

    results: Dict[str, Any] = {"id": doc_id, "format": doc_format}
    if downloaded_this_run:
        results["downloaded_path"] = doc_path_str # Store the downloaded path
    eval_results: Dict[str, Dict[str, Any]] = {}

    # --- Determine which processing function to use ---
    # Use the injected processor_map
    process_func: Optional[Callable[[Path, str], Optional[str]]] = processor_map.get(doc_format)

    if not process_func:
        print(f"Warning: Skipping doc ID {doc_id} - unsupported format: {doc_format}", file=sys.stderr)
        return {"id": doc_id, "status": "SKIPPED", "reason": f"Unsupported format: {doc_format}"}

    # --- Run processing for text and markdown ---
    try:
        print(f"  Processing {doc_id} for text output...")
        text_content: Optional[str] = process_func(doc_path, output_format='text')
        print(f"  Evaluating text output for {doc_id}...")
        eval_results["text"] = evaluate_func(text_content, 'text', document_metadata)
        # Add preview for easier debugging in report
        results["processed_text_preview"] = text_content[:100] if text_content else None
    except Exception as e:
        print(f"  Error processing {doc_id} for text: {e}", file=sys.stderr)
        eval_results["text"] = {"error": str(e)}
        results["processed_text_preview"] = None

    try:
        print(f"  Processing {doc_id} for markdown output...")
        md_content: Optional[str] = process_func(doc_path, output_format='markdown')
        print(f"  Evaluating markdown output for {doc_id}...")
        eval_results["markdown"] = evaluate_func(md_content, 'markdown', document_metadata)
        # Add preview for easier debugging in report
        results["processed_markdown_preview"] = md_content[:100] if md_content else None
    except Exception as e:
        print(f"  Error processing {doc_id} for markdown: {e}", file=sys.stderr)
        eval_results["markdown"] = {"error": str(e)}
        results["processed_markdown_preview"] = None

    # --- Determine overall status ---
    results["text_eval"] = eval_results.get("text", {})
    results["markdown_eval"] = eval_results.get("markdown", {})
    results["status"] = pass_fail_func(results)

    return results


def generate_report(all_results: List[Dict[str, Any]], output_dir: str):
    """Generates the final test report as a JSON file."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True) # Create dir if not exists

    report_file_path = output_path / "rag_test_report.json"

    try:
        with open(report_file_path, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2)
        print(f"Report generated successfully at: {report_file_path}")
    except Exception as e:
        print(f"Error generating report: {e}", file=sys.stderr)


async def main_async(): # Rename main to avoid conflict, make it async
    """Main function to parse arguments and run the test suite."""
    parser = argparse.ArgumentParser(description="Run RAG Real-World Tests.")
    parser.add_argument(
        "--manifest_path",
        required=True,
        help="Path to the JSON manifest file defining test documents."
    )
    parser.add_argument(
        "--output_dir",
        required=True,
        help="Directory to save test results and reports."
    )
    args = parser.parse_args()
    print(f"Manifest path: {args.manifest_path}")
    print(f"Output directory: {args.output_dir}")

    try:
        manifest_data = load_manifest(args.manifest_path)

        # Define the processor map using imported functions
        processor_map = {
            'pdf': process_pdf,
            'epub': process_epub,
            'txt': process_txt,
            # Add other formats here if needed
        }

        all_results = []
        documents_to_test = manifest_data.get("documents", [])

        # Define and create download directory
        output_path = Path(args.output_dir)
        download_dir = output_path / "downloads"
        download_dir.mkdir(parents=True, exist_ok=True)
        print(f"Download directory: {download_dir}")

        if not documents_to_test:
            print("Warning: No documents found in the manifest.", file=sys.stderr)
        else:
            print(f"Found {len(documents_to_test)} documents to test.")

        # Loop through documents and run tests
        for doc_metadata in documents_to_test:
            doc_id = doc_metadata.get("id", "unknown")
            print(f"Running test for document: {doc_id}...")
            # Await the async run_single_test call
            result = await run_single_test(
                doc_metadata,
                args.output_dir, # Main output dir for reports
                str(download_dir), # Specific dir for downloads
                processor_map=processor_map,
                evaluate_func=evaluate_output, # Pass the actual function
                pass_fail_func=determine_pass_fail # Pass the actual function
            )
            all_results.append(result)
            print(f"Result for {doc_id}: {result.get('status', 'UNKNOWN')}")

        # Generate the final report
        print("Generating final report...")
        generate_report(all_results, args.output_dir)

        print("Testing complete.")

    except FileNotFoundError:
        # Error already printed by load_manifest
        sys.exit(1)
    except json.JSONDecodeError:
        # Error already printed by load_manifest
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred in main: {e}", file=sys.stderr) # Generic catch for other errors
        sys.exit(1)


if __name__ == "__main__":
    # Configure logging if needed
    # logging.basicConfig(level=logging.INFO)
    asyncio.run(main_async()) # Run the async main function