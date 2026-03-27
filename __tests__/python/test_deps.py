"""
Tests for lib/rag/utils/deps.py — dependency checking utilities.

The module uses try/except blocks to detect optional dependencies at import time.
We test that the availability flags and fallback sentinels are set correctly
by mocking the import machinery.
"""

import sys
import pytest

pytestmark = pytest.mark.unit


class TestOCRDependencies:
    """Tests for OCR-related dependency detection (pytesseract, pdf2image, PIL)."""

    def test_ocr_available_when_deps_present(self):
        """When all OCR deps import successfully, OCR_AVAILABLE is True."""
        from lib.rag.utils import deps

        # In this environment, OCR deps may or may not be installed.
        # The key invariant: if OCR_AVAILABLE is True, the references are not None.
        if deps.OCR_AVAILABLE:
            assert deps.pytesseract is not None
            assert deps.convert_from_path is not None
            assert deps.Image is not None
        else:
            assert deps.pytesseract is None
            assert deps.convert_from_path is None
            assert deps.Image is None

    def test_ocr_unavailable_fallback(self, monkeypatch):
        """When OCR deps are missing, OCR_AVAILABLE is False and sentinels are None."""
        # Temporarily remove OCR-related modules from sys.modules so reimport triggers ImportError
        saved = {}
        for mod_name in [
            "pytesseract",
            "pdf2image",
            "pdf2image.convert_from_path",
            "PIL",
            "PIL.Image",
        ]:
            if mod_name in sys.modules:
                saved[mod_name] = sys.modules.pop(mod_name)

        # Block import of pytesseract to trigger the ImportError path
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name in ("pytesseract", "pdf2image", "PIL"):
                raise ImportError(f"Mocked: no module {name}")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        try:
            # Force reimport
            if "lib.rag.utils.deps" in sys.modules:
                del sys.modules["lib.rag.utils.deps"]
            import lib.rag.utils.deps as deps_reloaded

            assert deps_reloaded.OCR_AVAILABLE is False
            assert deps_reloaded.pytesseract is None
            assert deps_reloaded.convert_from_path is None
            assert deps_reloaded.Image is None
        finally:
            # Restore original modules
            sys.modules.update(saved)
            # Re-import original to restore state for other tests
            if "lib.rag.utils.deps" in sys.modules:
                del sys.modules["lib.rag.utils.deps"]
            import lib.rag.utils.deps  # noqa: F401


class TestEbooklibDependencies:
    """Tests for ebooklib/BeautifulSoup dependency detection."""

    def test_ebooklib_available_when_deps_present(self):
        """When ebooklib and bs4 import successfully, EBOOKLIB_AVAILABLE is True."""
        from lib.rag.utils import deps

        if deps.EBOOKLIB_AVAILABLE:
            assert deps.ebooklib is not None
            assert deps.epub is not None
            assert deps.BeautifulSoup is not None
            assert deps.NavigableString is not None
        else:
            assert deps.ebooklib is None
            assert deps.epub is None
            assert deps.BeautifulSoup is None
            assert deps.NavigableString is None

    def test_ebooklib_unavailable_fallback(self, monkeypatch):
        """When ebooklib is missing, EBOOKLIB_AVAILABLE is False."""
        saved = {}
        for mod_name in ["ebooklib", "ebooklib.epub", "bs4"]:
            if mod_name in sys.modules:
                saved[mod_name] = sys.modules.pop(mod_name)

        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name in ("ebooklib", "bs4"):
                raise ImportError(f"Mocked: no module {name}")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        try:
            if "lib.rag.utils.deps" in sys.modules:
                del sys.modules["lib.rag.utils.deps"]
            import lib.rag.utils.deps as deps_reloaded

            assert deps_reloaded.EBOOKLIB_AVAILABLE is False
            assert deps_reloaded.ebooklib is None
            assert deps_reloaded.epub is None
            assert deps_reloaded.BeautifulSoup is None
            assert deps_reloaded.NavigableString is None
        finally:
            sys.modules.update(saved)
            if "lib.rag.utils.deps" in sys.modules:
                del sys.modules["lib.rag.utils.deps"]
            import lib.rag.utils.deps  # noqa: F401


class TestPyMuPDFDependencies:
    """Tests for PyMuPDF (fitz) dependency detection."""

    def test_pymupdf_consistency(self):
        """PYMUPDF_AVAILABLE and fitz should be consistent."""
        from lib.rag.utils import deps

        if deps.PYMUPDF_AVAILABLE:
            assert deps.fitz is not None
        else:
            assert deps.fitz is None

    def test_pymupdf_unavailable_fallback(self, monkeypatch):
        """When fitz is missing, PYMUPDF_AVAILABLE is False."""
        saved = {}
        if "fitz" in sys.modules:
            saved["fitz"] = sys.modules.pop("fitz")

        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "fitz":
                raise ImportError("Mocked: no module fitz")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        try:
            if "lib.rag.utils.deps" in sys.modules:
                del sys.modules["lib.rag.utils.deps"]
            import lib.rag.utils.deps as deps_reloaded

            assert deps_reloaded.PYMUPDF_AVAILABLE is False
            assert deps_reloaded.fitz is None
        finally:
            sys.modules.update(saved)
            if "lib.rag.utils.deps" in sys.modules:
                del sys.modules["lib.rag.utils.deps"]
            import lib.rag.utils.deps  # noqa: F401


class TestXmarkDependencies:
    """Tests for OpenCV/numpy (x-mark detection) dependency detection."""

    def test_xmark_consistency(self):
        """XMARK_AVAILABLE and cv2/np should be consistent."""
        from lib.rag.utils import deps

        if deps.XMARK_AVAILABLE:
            assert deps.cv2 is not None
            assert deps.np is not None
        else:
            assert deps.cv2 is None
            assert deps.np is None

    def test_xmark_unavailable_fallback(self, monkeypatch):
        """When cv2 is missing, XMARK_AVAILABLE is False."""
        saved = {}
        for mod_name in ["cv2", "numpy", "numpy.core", "numpy.core.multiarray"]:
            if mod_name in sys.modules:
                saved[mod_name] = sys.modules.pop(mod_name)

        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name in ("cv2",):
                raise ImportError("Mocked: no module cv2")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        try:
            if "lib.rag.utils.deps" in sys.modules:
                del sys.modules["lib.rag.utils.deps"]
            import lib.rag.utils.deps as deps_reloaded

            assert deps_reloaded.XMARK_AVAILABLE is False
            assert deps_reloaded.cv2 is None
            assert deps_reloaded.np is None
        finally:
            sys.modules.update(saved)
            if "lib.rag.utils.deps" in sys.modules:
                del sys.modules["lib.rag.utils.deps"]
            import lib.rag.utils.deps  # noqa: F401
