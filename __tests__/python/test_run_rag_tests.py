import pytest
import sys
import json # Added import
from pathlib import Path
from unittest.mock import patch # Re-add patch for other tests
# Remove unittest.mock import, use mocker fixture instead
from unittest.mock import MagicMock # Keep MagicMock for direct instantiation

# Test if the script can be imported and has a main function
def test_main_function_exists():
    """
    Tests if the run_rag_tests script can be imported and has a main function.
    """
    try:
        from scripts import run_rag_tests
        assert callable(run_rag_tests.main)
    except ImportError:
        pytest.fail("Could not import 'scripts.run_rag_tests'. Does the file exist and is it importable?")
    except AttributeError:
        pytest.fail("The 'main' function is missing from 'scripts.run_rag_tests'.")
# Add more tests here as we proceed with TDD

# Remove decorators, we will use 'with patch' inside
def test_main_parses_arguments():
    """
    Tests if the main function sets up argument parsing for manifest_path and output_dir.
    """
    mock_parser = MagicMock()
    mock_argument_parser = MagicMock(return_value=mock_parser)
    mock_load_manifest_func = MagicMock(return_value={"documents": []}) # Mock for load_manifest

    # Patch sys.argv, ArgumentParser, load_manifest, and sys.exit using 'with'
    with patch.object(sys, 'argv', ['run_rag_tests.py', '--manifest_path', 'dummy.json', '--output_dir', 'dummy_out']), \
         patch('argparse.ArgumentParser', mock_argument_parser), \
         patch('scripts.run_rag_tests.load_manifest', mock_load_manifest_func), \
         patch('sys.exit') as mock_exit: # Patch sys.exit
        try:
            from scripts import run_rag_tests
            # # importlib.reload(run_rag_tests) # Removed reload # Removed reload
            run_rag_tests.main() # Call main *within* the patch context
        except ImportError:
             pytest.fail("Could not import 'scripts.run_rag_tests'.")
        # No longer need to catch SystemExit here as it's patched
        except Exception as e:
             pytest.fail(f"run_rag_tests.main() raised an unexpected exception: {e}")

    # Check if add_argument was called for manifest_path and output_dir
    # Assertions remain the same
    calls = mock_parser.add_argument.call_args_list
    arg_names = [call[0][0] for call in calls] # Gets the first positional argument ('--manifest_path', etc.)

    assert '--manifest_path' in arg_names, "Argument --manifest_path was not added."
    assert '--output_dir' in arg_names, "Argument --output_dir was not added."
    # Check if parse_args was called
    mock_parser.parse_args.assert_called_once()


# Test manifest loading
def test_load_manifest_success():
    """
    Tests if load_manifest correctly loads a valid JSON manifest file.
    """
    # Use the sample manifest created for testing
    sample_manifest_path = "scripts/sample_manifest.json"
    try:
        from scripts import run_rag_tests
        # We need to reload the module if it was already imported in another test
        import importlib
        # importlib.reload(run_rag_tests) # Removed reload
        manifest_data = run_rag_tests.load_manifest(sample_manifest_path)

        assert isinstance(manifest_data, dict), "Manifest data should be a dictionary."
        assert "description" in manifest_data, "Manifest should have a 'description' key."
        assert "documents" in manifest_data, "Manifest should have a 'documents' key."
        assert isinstance(manifest_data["documents"], list), "'documents' should be a list."
        assert len(manifest_data["documents"]) > 0, "Manifest 'documents' list should not be empty."
        # Check structure of the first document
        doc = manifest_data["documents"][0]
        assert "id" in doc
        assert "format" in doc
        assert "local_sample_path" in doc

    except ImportError:
        pytest.fail("Could not import 'scripts.run_rag_tests'.")
    except FileNotFoundError:
        pytest.fail(f"Sample manifest file not found at {sample_manifest_path}")
    except Exception as e:
        pytest.fail(f"load_manifest raised an unexpected exception: {e}")

def test_load_manifest_file_not_found():
    """
    Tests if load_manifest raises FileNotFoundError for a non-existent file.
    """
    non_existent_path = "non_existent_manifest.json"
    with pytest.raises(FileNotFoundError):
        from scripts import run_rag_tests
        import importlib
        # importlib.reload(run_rag_tests) # Removed reload
        run_rag_tests.load_manifest(non_existent_path)

def test_load_manifest_invalid_json():
    """
    Tests if load_manifest raises an appropriate error for invalid JSON.
    """
    # Create a temporary invalid JSON file
    invalid_json_path = "scripts/invalid_manifest.json"
    with open(invalid_json_path, "w") as f:
        f.write("{invalid json content")

    with pytest.raises(json.JSONDecodeError):
         from scripts import run_rag_tests
         import importlib
         # importlib.reload(run_rag_tests) # Removed reload
         run_rag_tests.load_manifest(invalid_json_path)

    # Clean up the temporary file
    import os
    # Check if the file exists before trying to remove it
    if os.path.exists(invalid_json_path):
        os.remove(invalid_json_path)

# Test main execution loop
# Test main execution loop - Using mocker.patch
def test_main_loads_manifest_and_runs_tests_revised(mocker): # Add mocker fixture
    """
    Tests if main loads the manifest, calls run_single_test for each doc,
    and calls generate_report, using mocker.patch for better isolation.
    """
    # Setup mock argparse
    mock_args = MagicMock()
    mock_args.manifest_path = 'dummy_manifest.json'
    mock_args.output_dir = 'dummy_output'
    mock_parser = MagicMock()
    mock_parser.parse_args.return_value = mock_args
    mocker.patch('argparse.ArgumentParser', return_value=mock_parser)
    mocker.patch('sys.exit') # Patch sys.exit

    # Setup mock manifest data
    mock_manifest_data = {
        "documents": [
            {"id": "doc1", "local_sample_path": "path1"},
            {"id": "doc2", "local_sample_path": "path2"},
        ]
    }
    # Patch load_manifest using mocker
    mock_load_manifest = mocker.patch('scripts.run_rag_tests.load_manifest', return_value=mock_manifest_data)

    # Setup mock results for run_single_test using mocker
    mock_run_single_test_results = [
        {"id": "doc1", "status": "PASS"},
        {"id": "doc2", "status": "FAIL"},
    ]
    mock_run_single_test = mocker.patch('scripts.run_rag_tests.run_single_test', side_effect=mock_run_single_test_results)

    # Patch generate_report using mocker
    mock_generate_report = mocker.patch('scripts.run_rag_tests.generate_report')

    try:
        # Import the module first
        from scripts import run_rag_tests
        # Call main - mocks are applied by mocker.patch
        run_rag_tests.main()
    except Exception as e:
        pytest.fail(f"run_rag_tests.main() raised an unexpected exception: {e}")

    # Assertions on the mocks patched by mocker
    mock_load_manifest.assert_called_once_with('dummy_manifest.json')
    assert mock_run_single_test.call_count == 2

    # Need to adjust assertion for run_single_test calls as mocker.patch doesn't
    # directly capture calls in the same way when patching module-level functions.
    # We check the call count and can infer the arguments based on the loop.
    # A more robust check might involve inspecting the arguments passed to the
    # *actual* run_single_test if it weren't fully mocked, but here it's fully replaced.

    # Check that generate_report was called with the collected results
    expected_report_arg = [
        {"id": "doc1", "status": "PASS"},
        {"id": "doc2", "status": "FAIL"},
    ]
    mock_generate_report.assert_called_once_with(expected_report_arg, 'dummy_output')


# Test run_single_test function - Using Dependency Injection and mocker
def test_run_single_test_calls_processing_and_eval(mocker): # Add mocker fixture
    """
    Tests if run_single_test calls injected processing, evaluation,
    and pass/fail functions correctly, using pytest-mock (mocker).
    """
    mocker.resetall() # Reset mocks to prevent leakage from previous tests
    mock_doc_metadata = {
        "id": "test_doc_001",
        "format": "pdf", # Format determines which processor is looked up initially
        "local_sample_path": "__tests__/python/fixtures/rag_robustness/sample.pdf"
    }
    output_dir = "temp_test_output"

    # Use mocker to create mocks if needed, or MagicMock directly
    # Using MagicMock directly is fine here as we pass them explicitly
    # Use side_effect with lambda to explicitly define behavior for each call
    mock_process_pdf = MagicMock(side_effect=lambda *args, **kwargs: "Mocked Processed Content")
    mock_evaluate_output = MagicMock(side_effect=lambda *args, **kwargs: {"metric": 1.0})
    mock_determine_pass_fail = MagicMock(side_effect=lambda *args, **kwargs: "PASS")

    # Define the processor map containing the mock
    mock_processor_map = {
        'pdf': mock_process_pdf
    }

    # Call the function under test, passing mocks as arguments
    from scripts import run_rag_tests
    results = run_rag_tests.run_single_test(
        mock_doc_metadata,
        output_dir,
        processor_map=mock_processor_map, # Pass the map containing the mock
        evaluate_func=mock_evaluate_output,
        pass_fail_func=mock_determine_pass_fail
    )

    # Assertions on the mocks
    assert mock_process_pdf.call_count == 2
    expected_doc_path = Path(mock_doc_metadata["local_sample_path"])
    mock_process_pdf.assert_any_call(expected_doc_path, output_format='text')
    mock_process_pdf.assert_any_call(expected_doc_path, output_format='markdown')

    assert mock_evaluate_output.call_count == 2
    mock_determine_pass_fail.assert_called_once()

    # Assertions on the results dictionary
    assert isinstance(results, dict), "run_single_test should return a dictionary."
    assert results["id"] == "test_doc_001"
    assert results["status"] == "PASS"
    assert "text_eval" in results
    assert "markdown_eval" in results
# Test placeholder functions
def test_evaluate_output_placeholder_returns_dict():
    """Tests if the placeholder evaluate_output returns a dictionary."""
    from scripts import run_rag_tests
    # Dummy inputs, content doesn't matter for placeholder
    result = run_rag_tests.evaluate_output("dummy text", "text", {})
    assert isinstance(result, dict)
def test_determine_pass_fail_placeholder_returns_string():
    """Tests if the placeholder determine_pass_fail returns a string."""
    from scripts import run_rag_tests
    # Dummy input, content doesn't matter for placeholder
    result = run_rag_tests.determine_pass_fail({})
    assert isinstance(result, str)