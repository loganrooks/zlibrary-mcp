"""Tests for the upstream reachability probe.

The network calls themselves are not exercised here — they are the point of the
scheduled job. What is tested is the reporting contract the CI workflow depends
on: which failures are actionable, and the exact `$GITHUB_OUTPUT` encoding.
"""

import importlib.util
import os
import sys
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parent.parent.parent / "scripts" / "check_upstream.py"


@pytest.fixture(scope="module")
def check_upstream():
    spec = importlib.util.spec_from_file_location("check_upstream", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    # The module uses `from __future__ import annotations` with @dataclass, and
    # dataclasses resolves those string annotations via sys.modules — so the module
    # must be registered before exec_module, not after.
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        del sys.modules[spec.name]
        raise
    yield module
    del sys.modules[spec.name]


def test_required_failure_is_actionable(check_upstream):
    """Z-Library failures must be reported as FAIL, not warnings."""
    result = check_upstream.ProbeResult(
        name="zlibrary:eapi/book/search", ok=False, detail="boom", required=True
    )
    assert result.symbol == "FAIL"


def test_optional_failure_is_a_warning(check_upstream):
    """LibGen/Anna's are fallbacks; their absence must not read as a hard failure."""
    result = check_upstream.ProbeResult(
        name="libgen:search", ok=False, detail="boom", required=False
    )
    assert result.symbol == "WARN"


def test_passing_probe_reports_ok(check_upstream):
    result = check_upstream.ProbeResult(name="x", ok=True, detail="fine")
    assert result.symbol == "OK"


def test_render_summarises_required_and_optional_failures(check_upstream):
    results = [
        check_upstream.ProbeResult("a", True, "fine"),
        check_upstream.ProbeResult("b", False, "broken", required=True),
        check_upstream.ProbeResult("c", False, "broken", required=False),
    ]
    report = check_upstream.render(results)
    assert "1 passing, 1 required failing, 1 optional failing" in report
    assert "FAIL" in report and "WARN" in report and "OK" in report


def test_github_output_uses_heredoc_for_multiline_report(
    check_upstream, tmp_path, monkeypatch
):
    """A bare `report=<multi-line>` assignment breaks the workflow parser."""
    out = tmp_path / "gh_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))

    check_upstream.emit_github_output("line one\nline two", failed=True)

    written = out.read_text(encoding="utf-8")
    assert "failed=true\n" in written
    assert "report<<PROBE_EOF\n" in written
    assert "line one\nline two\n" in written
    assert written.rstrip().endswith("PROBE_EOF")


def test_github_output_is_a_noop_outside_ci(check_upstream, monkeypatch):
    """Running `npm run doctor` locally must not fail for lack of GITHUB_OUTPUT."""
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    check_upstream.emit_github_output("anything", failed=False)  # must not raise


def test_probe_targets_match_runtime_defaults(check_upstream):
    """The probe is only useful if it checks what the server actually contacts."""
    assert check_upstream.ZLIB_DOMAIN == os.environ.get(
        "ZLIBRARY_EAPI_DOMAIN", "z-library.sk"
    )
    assert check_upstream.ANNAS_BASE_URL == os.environ.get(
        "ANNAS_BASE_URL", "https://annas-archive.li"
    )
