import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock, call # Import call

# Import functions to test from the rag_processing module
# Assuming the test file is run from the project root
from lib.rag_processing import _slugify, save_processed_text, FileSaveError, PROCESSED_OUTPUT_DIR

# --- Tests for _slugify ---

@pytest.mark.parametrize("input_value, expected_slug", [
    ("Simple Title", "simple-title"),
    ("Author Name", "author-name"),
    ("Title with !@#$%^&*()_+", "title-with"),
    ("  Leading/Trailing Spaces  ", "leading-trailing-spaces"),
    ("Multiple   Spaces", "multiple-spaces"),
    ("Repeated--Dashes", "repeated-dashes"),
    ("Underscores_and_spaces", "underscores-and-spaces"), # Expect underscore to become hyphen
    ("Unicode Ćafe", "unicode-cafe"), # Default ASCII conversion
    ("", "file"), # Empty string
    ("!@#$", "file"), # Only special chars
    ("---", "file"), # Only dashes
    ("A Very Long Title That Exceeds Potential Limits Just In Case We Need To Test Truncation Later On Maybe", "a-very-long-title-that-exceeds-potential-limits-just-in-case-we-need-to-test-truncation-later-on-maybe"),
])
def test_slugify_ascii(input_value, expected_slug):
    assert _slugify(input_value) == expected_slug

def test_slugify_unicode():
    assert _slugify("你好 世界", allow_unicode=True) == "你好-世界"

# --- Tests for save_processed_text ---

@pytest.fixture
def mock_aiofiles(mocker):
    """Fixture to mock aiofiles.open correctly."""
    # Mock the async context manager returned by aiofiles.open
    mock_async_context_manager = AsyncMock()
    mock_file_handle = AsyncMock() # This represents the file handle 'f'
    mock_file_handle.write = AsyncMock() # Mock the write method

    # Configure __aenter__ to return the mock file handle
    mock_async_context_manager.__aenter__.return_value = mock_file_handle
    # __aexit__ should return None or handle exceptions
    mock_async_context_manager.__aexit__.return_value = None

    # Patch aiofiles.open to return the mock context manager
    mock_open_func = mocker.patch('aiofiles.open', return_value=mock_async_context_manager)

    # Return the mock open function and the mock file handle for assertions
    return mock_open_func, mock_file_handle

@pytest.fixture
def mock_path(mocker):
    """Fixture to mock Path methods, avoiding patching read-only attributes."""
    # Mock the Path class itself
    mock_path_class = mocker.patch('pathlib.Path')

    # Create specific mock instances
    mock_output_dir_instance = MagicMock(spec=Path)
    mock_final_path_instance = MagicMock(spec=Path)
    mock_original_file_path = MagicMock(spec=Path)

    # Configure the Path class mock's side effect
    def path_side_effect(*args, **kwargs):
        # When Path() is called with the output directory string
        if args and args[0] == str(rag_processing.PROCESSED_OUTPUT_DIR):
             # Return the mock for the output directory
            return mock_output_dir_instance
        # When Path() is called with the original file path string
        elif args and isinstance(args[0], str) and 'original' in args[0]: # Heuristic for original path
            return mock_original_file_path
        # Default return (e.g., if Path is called with no args)
        return MagicMock(spec=Path)

    mock_path_class.side_effect = path_side_effect

    # Mock methods on the specific instances
    mock_output_dir_instance.mkdir = MagicMock()
    # Mocking division on the *class variable* PROCESSED_OUTPUT_DIR
    # We need to patch the actual Path object used in the module
    mocker.patch('lib.rag_processing.PROCESSED_OUTPUT_DIR', mock_output_dir_instance)
    mock_output_dir_instance.__truediv__.return_value = mock_final_path_instance

    # Configure the original file path mock
    mock_original_file_path.name = "original.epub"
    mock_original_file_path.stem = "original"
    # Make the original file path mock behave like a Path object for os.path.splitext
    mock_original_file_path.__fspath__ = lambda: "/fake/original.epub" # Needed for os.path functions

    # Return mocks needed by tests
    return mock_path_class, mock_output_dir_instance, mock_final_path_instance, mock_original_file_path


@pytest.mark.asyncio
async def test_save_processed_text_with_metadata_slug(mock_aiofiles, mock_path, mocker): # Added mocker
    """Test saving with metadata generates correct slug filename."""
    mock_open, mock_file = mock_aiofiles
    # Unpack new mock_path fixture results
    mock_path_class, mock_output_dir_instance, mock_final_path_instance, mock_original_file_path = mock_path

    original_file = mock_original_file_path # Use the dedicated mock for original path
    content = "Processed text content."
    output_format = "md"
    book_id = "12345"
    author = "Test Author"
    title = "A Sample Book Title!"

    expected_slug = "test-author-a-sample-book-title"
    expected_filename = f"{expected_slug}-{book_id}.{output_format}"
    # Configure the final path mock for this test's expectation
    mock_final_path_instance.__str__.return_value = str(PROCESSED_OUTPUT_DIR / expected_filename) # Set string representation

    # Mock os.path.splitext used within the function
    mocker.patch('os.path.splitext', return_value=(original_file.stem, '.epub'))

    result_path = await save_processed_text(
        original_file_path=original_file,
        text_content=content,
            output_format=output_format,
            book_id=book_id,
            author=author,
            title=title
        )

    # Assertions using the new fixture structure
    mock_output_dir_instance.mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mock_output_dir_instance.__truediv__.assert_called_once_with(expected_filename)
    mock_open.assert_called_once_with(mock_final_path_instance, mode='w', encoding='utf-8') # Check open uses the final path mock
    mock_file.write.assert_awaited_once_with(content)
    assert result_path == mock_final_path_instance # Result should be the final path mock

@pytest.mark.asyncio
async def test_save_processed_text_long_slug_truncation(mock_aiofiles, mock_path, mocker): # Added mocker
    """Test saving with metadata that generates a long slug truncates correctly."""
    mock_open, mock_file = mock_aiofiles
    # Unpack new mock_path fixture results
    mock_path_class, mock_output_dir_instance, mock_final_path_instance, mock_original_file_path = mock_path

    original_file = mock_original_file_path
    content = "Content"
    output_format = "txt"
    book_id = "987"
    author = "An Author With A Very Long Name Indeed"
    title = "This Title is Extremely Long and Contains Many Words to Exceed the One Hundred Character Limit Set for Slugs"

    # Expected slug generation:
    # author: an-author-with-a-very-long-name-indeed
    # title: this-title-is-extremely-long-and-contains-many-words-to-exceed-the-one-hundred-character-limit-set-for-slugs
    # combined: an-author-with-a-very-long-name-indeed-this-title-is-extremely-long-and-contains-many-words-to-exceed-the-one-hundred-character-limit-set-for-slugs
    # truncated (100 chars): an-author-with-a-very-long-name-indeed-this-title-is-extremely-long-and-contains-many-words-to-ex
    # final (split at last '-'): an-author-with-a-very-long-name-indeed-this-title-is-extremely-long-and-contains-many-words-to
    expected_slug = "an-author-with-a-very-long-name-indeed-this-title-is-extremely-long-and-contains-many-words-to"
    expected_filename = f"{expected_slug}-{book_id}.{output_format}"
    # Configure the final path mock for this test's expectation
    mock_final_path_instance.__str__.return_value = str(PROCESSED_OUTPUT_DIR / expected_filename)

    # Mock os.path.splitext used within the function
    mocker.patch('os.path.splitext', return_value=(original_file.stem, '.epub'))

    result_path = await save_processed_text(
        original_file_path=original_file,
        text_content=content,
            output_format=output_format,
            book_id=book_id,
            author=author,
            title=title
        )
    # Assertions using the new fixture structure
    mock_output_dir_instance.__truediv__.assert_called_once_with(expected_filename)
    mock_open.assert_called_once_with(mock_final_path_instance, mode='w', encoding='utf-8')
    assert result_path == mock_final_path_instance


@pytest.mark.asyncio
async def test_save_processed_text_without_metadata_fallback(mock_aiofiles, mock_path, mocker): # Added mocker
    """Test saving without metadata uses the fallback filename."""
    mock_open, mock_file = mock_aiofiles
    # Unpack new mock_path fixture results
    mock_path_class, mock_output_dir_instance, mock_final_path_instance, mock_original_file_path = mock_path

    original_file = mock_original_file_path
    original_file.stem = "fallback_test" # Set stem for this test
    content = "Fallback content."
    output_format = "txt"

    expected_filename = f"{original_file.stem}.processed.{output_format}"
    # Configure the final path mock for this test's expectation
    mock_final_path_instance.__str__.return_value = str(PROCESSED_OUTPUT_DIR / expected_filename)

    # Mock os.path.splitext used within the function
    mocker.patch('os.path.splitext', return_value=(original_file.stem, '.epub'))

    result_path = await save_processed_text(
        original_file_path=original_file,
        text_content=content,
            output_format=output_format,
            # No metadata provided
            book_id=None,
            author=None,
            title=None
        )

    # Assertions using the new fixture structure
    mock_output_dir_instance.mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mock_output_dir_instance.__truediv__.assert_called_once_with(expected_filename)
    mock_open.assert_called_once_with(mock_final_path_instance, mode='w', encoding='utf-8')
    mock_file.write.assert_awaited_once_with(content)
    assert result_path == mock_final_path_instance

@pytest.mark.asyncio
async def test_save_processed_text_empty_content(mock_aiofiles, mock_path, mocker): # Added mocker
    """Test saving empty string content works."""
    mock_open, mock_file = mock_aiofiles
    # Unpack new mock_path fixture results
    mock_path_class, mock_output_dir_instance, mock_final_path_instance, mock_original_file_path = mock_path

    original_file = mock_original_file_path
    content = "" # Empty string
    output_format = "txt"
    book_id = "empty"
    author = "Author"
    title = "Title"

    expected_slug = "author-title"
    expected_filename = f"{expected_slug}-{book_id}.{output_format}"
    # Configure the final path mock for this test's expectation
    mock_final_path_instance.__str__.return_value = str(PROCESSED_OUTPUT_DIR / expected_filename)

    # Mock os.path.splitext used within the function
    mocker.patch('os.path.splitext', return_value=(original_file.stem, '.epub'))

    result_path = await save_processed_text(
        original_file_path=original_file,
        text_content=content,
            output_format=output_format,
            book_id=book_id,
            author=author,
            title=title
        )
    # Assertions using the new fixture structure
    mock_output_dir_instance.__truediv__.assert_called_once_with(expected_filename)
    mock_open.assert_called_once_with(mock_final_path_instance, mode='w', encoding='utf-8')
    mock_file.write.assert_awaited_once_with("") # Expect empty string write
    assert result_path == mock_final_path_instance

@pytest.mark.asyncio
async def test_save_processed_text_none_content_raises_error(mock_path, mocker): # Added mocker
    """Test saving None content raises ValueError."""
    # Unpack new mock_path fixture results
    mock_path_class, mock_output_dir_instance, mock_final_path_instance, mock_original_file_path = mock_path

    # Mock os.path.splitext used within the function (needed even for error case)
    mocker.patch('os.path.splitext', return_value=(mock_original_file_path.stem, '.epub'))

    # Expect FileSaveError which wraps the original ValueError
    with pytest.raises(FileSaveError, match="Failed to save processed text to unknown_processed_file: Cannot save None content."):
        await save_processed_text(
            original_file_path=mock_original_file_path,
            text_content=None, # None content
            output_format="txt",
            book_id="none_test",
            author="Author",
            title="Title"
        )

@pytest.mark.asyncio
async def test_save_processed_text_os_error_raises_filesaveerror(mock_aiofiles, mock_path, mocker): # Added mocker
    """Test that an OSError during file write raises FileSaveError."""
    mock_open, mock_file = mock_aiofiles
    # Unpack new mock_path fixture results
    mock_path_class, mock_output_dir_instance, mock_final_path_instance, mock_original_file_path = mock_path

    # Configure the mock file write to raise an OSError
    mock_file.write.side_effect = OSError("Disk full")

    original_file = mock_original_file_path
    content = "Some content"
    output_format = "txt"
    book_id = "os_error"
    author = "Author"
    title = "Title"

    expected_slug = "author-title"
    expected_filename = f"{expected_slug}-{book_id}.{output_format}"
    # Configure the final path mock for this test's expectation
    mock_final_path_instance.__str__.return_value = str(PROCESSED_OUTPUT_DIR / expected_filename)

    # Mock os.path.splitext used within the function
    mocker.patch('os.path.splitext', return_value=(original_file.stem, '.epub'))

    # Adjust the expected error message to match the actual raised error
    expected_error_msg = f"Failed to save processed file due to OS error: Disk full"
    try:
        await save_processed_text( # Call awaitable directly
            original_file_path=original_file,
            text_content=content,
                    output_format=output_format,
                    book_id=book_id,
                    author=author,
                    title=title
                )
        pytest.fail("Expected FileSaveError was not raised.") # Fail if no exception
    except FileSaveError as e:
        # Assert the correct exception type and message
        assert str(e) == expected_error_msg
    except Exception as e:
        pytest.fail(f"Raised unexpected exception type {type(e).__name__}: {e}")