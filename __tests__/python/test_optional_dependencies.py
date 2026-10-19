"""Regression coverage for the acquisition-only dependency boundary."""

from __future__ import annotations

import asyncio
from pathlib import Path
import subprocess
import sys

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

import pytest


pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER = REPO_ROOT / "scripts" / "check_optional_imports.py"


def _dependency_name(requirement: str) -> str:
    """Return the normalized distribution name from a simple requirement."""
    return (
        requirement.split("[", 1)[0]
        .split("<", 1)[0]
        .split(">", 1)[0]
        .split("=", 1)[0]
        .strip()
        .lower()
        .replace("_", "-")
    )


def test_pyproject_removes_processing_extras():
    """Moving a heavy package back to core must fail the packaging boundary."""
    config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = config["project"]

    core = {_dependency_name(value) for value in project["dependencies"]}
    extras = {
        name: {_dependency_name(value) for value in values}
        for name, values in project["optional-dependencies"].items()
    }

    rag = {"pymupdf", "ebooklib", "nltk"}
    scholar_only = {
        "opencv-python-headless",
        "ocrmypdf",
        "pytesseract",
        "pdf2image",
        "pillow",
    }

    assert not core.intersection(rag | scholar_only)
    assert "rag" not in extras
    assert "scholar" not in extras
    assert "ocr" not in extras
    assert config["tool"]["uv"]["package"] is False


def test_import_checker_reports_module_scope_heavy_imports(tmp_path):
    """An unguarded heavy import must produce a path-and-line diagnostic."""
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    (lib_dir / "guarded.py").write_text(
        "try:\n    import fitz\nexcept ImportError:\n    fitz = None\n",
        encoding="utf-8",
    )
    (lib_dir / "unguarded.py").write_text("from PIL import Image\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(CHECKER), "--root", str(lib_dir)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "unguarded.py:1" in result.stderr
    assert "PIL" in result.stderr
    assert "lib/guarded.py:" not in result.stderr


def test_repository_has_no_unguarded_module_scope_heavy_imports():
    """The repository checker must pass on the complete lib import graph."""
    result = subprocess.run(
        [sys.executable, str(CHECKER)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_checker_core_smoke_completes_offline_acquisition():
    """The CI smoke entry point must exercise startup, search, and install guidance."""
    result = subprocess.run(
        [sys.executable, str(CHECKER), "--core-smoke"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Core-only bridge smoke OK" in result.stdout


@pytest.mark.asyncio
async def test_core_smoke_does_not_create_a_background_executor(monkeypatch):
    """The standalone core check must terminate without executor shutdown work."""
    from scripts.check_optional_imports import _run_core_smoke

    async def unexpected_to_thread(*args, **kwargs):
        raise AssertionError("core smoke started a background executor")

    monkeypatch.setattr(asyncio, "to_thread", unexpected_to_thread)

    await _run_core_smoke(REPO_ROOT)
