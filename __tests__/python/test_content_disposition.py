"""Tests for download filename derivation.

Two concerns meet here:

* **Correctness** — RFC 6266 permits three spellings of the filename parameter and
  Z-Library uses all of them. The previous `split("filename=")` implementation
  mis-parsed the extended form, producing percent-encoded names.
* **Safety** — the value arrives in a server-controlled header and is joined onto
  the output directory. `Path("/downloads") / "../../x"` escapes the directory, so
  it must be reduced to a basename first.

Based on the parsing work in PR #13 by @ltspace, extended to cover the traversal
case and the cross-platform separator gap.
"""

import ntpath
import posixpath
from pathlib import Path

import pytest

from zlibrary.eapi import (
    filename_from_content_disposition,
    sanitize_download_filename,
)


class TestFilenameFromContentDisposition:
    @pytest.mark.parametrize(
        "header,expected",
        [
            # Bare value — the common case.
            ("attachment; filename=book.epub", "book.epub"),
            # Quoted value, including a title with spaces.
            (
                'attachment; filename="The Burnout Society.pdf"',
                "The Burnout Society.pdf",
            ),
            # Extended form with percent-encoded UTF-8 (a German title).
            (
                "attachment; filename*=UTF-8''M%C3%BCdigkeitsgesellschaft.epub",
                "Müdigkeitsgesellschaft.epub",
            ),
            # Extended form takes priority: the ASCII `filename` is a lossy fallback
            # that the server supplies for legacy clients.
            (
                'attachment; filename="Mudigkeitsgesellschaft.epub"; '
                "filename*=UTF-8''M%C3%BCdigkeitsgesellschaft.epub",
                "Müdigkeitsgesellschaft.epub",
            ),
            # Case-insensitive parameter name.
            ("attachment; FileName=book.pdf", "book.pdf"),
            # Whitespace around the separator.
            ("attachment; filename = book.pdf", "book.pdf"),
            # Percent-encoded spaces in the extended form.
            (
                "attachment; filename*=UTF-8''Of%20Grammatology.pdf",
                "Of Grammatology.pdf",
            ),
            # Single-quoted value from a lenient server.
            ("attachment; filename='book.mobi'", "book.mobi"),
        ],
    )
    def test_extracts_expected_filename(self, header, expected):
        assert filename_from_content_disposition(header) == expected

    @pytest.mark.parametrize(
        "header",
        [
            "",
            "attachment",
            "inline",
            # Present but empty — must fall through to the URL-derived name rather
            # than yielding an empty filename.
            'attachment; filename=""',
        ],
    )
    def test_returns_none_when_no_usable_filename(self, header):
        assert filename_from_content_disposition(header) is None

    def test_extended_form_is_not_returned_percent_encoded(self):
        """Regression: the old split-based parser returned the raw encoded bytes."""
        result = filename_from_content_disposition(
            "attachment; filename*=UTF-8''M%C3%BCdigkeit.epub"
        )
        assert "%C3%BC" not in result
        assert result == "Müdigkeit.epub"


class TestSanitizeDownloadFilename:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("book.epub", "book.epub"),
            ("The Burnout Society.pdf", "The Burnout Society.pdf"),
            # POSIX traversal.
            ("../../etc/passwd", "passwd"),
            ("/etc/passwd", "passwd"),
            ("./book.epub", "book.epub"),
            # Windows-style traversal. os.path.basename on POSIX does NOT split on
            # backslashes, so a Linux server would pass this through unchanged.
            (r"..\..\Windows\System32\evil.dll", "evil.dll"),
            (r"C:\Windows\evil.dll", "evil.dll"),
            # Mixed separators.
            (r"../..\etc/passwd", "passwd"),
            # Nested directory component.
            ("subdir/book.epub", "book.epub"),
        ],
    )
    def test_reduces_to_basename(self, raw, expected):
        assert sanitize_download_filename(raw) == expected

    @pytest.mark.parametrize("raw", ["", ".", "..", "../", "/", "   "])
    def test_returns_empty_for_unusable_names(self, raw):
        """Caller substitutes a book-id-based default when this returns empty."""
        assert sanitize_download_filename(raw) == ""

    @pytest.mark.parametrize(
        "raw",
        ["../../etc/passwd", r"..\..\evil.dll", "/etc/passwd", r"C:\evil.dll"],
    )
    def test_sanitized_name_cannot_escape_output_dir(self, raw, tmp_path):
        """The property that actually matters, asserted on a real path join."""
        sanitized = sanitize_download_filename(raw)
        joined = Path(tmp_path) / sanitized
        assert joined.resolve().parent == Path(tmp_path).resolve()

    def test_raw_name_would_have_escaped(self, tmp_path):
        """Confirms the vulnerability the sanitizer closes is real, not theoretical."""
        escaped = (Path(tmp_path) / "../../etc/passwd").resolve()
        assert escaped.parent != Path(tmp_path).resolve()

    def test_basename_helpers_disagree_on_backslashes(self):
        """Documents why both posixpath and ntpath are applied, not just os.path."""
        payload = r"..\..\evil.dll"
        # On POSIX, the platform basename leaves the payload intact.
        assert posixpath.basename(payload) == payload
        # ntpath is what actually strips it.
        assert ntpath.basename(payload) == "evil.dll"
