"""Offline regressions for the settled #204 output policy."""

import os
from pathlib import Path
import stat
from unittest.mock import AsyncMock

import pytest

from lib import acquisition
from test_interface_acquisition import BOOK, PAYLOAD, transfer


def test_default_root_is_data_directory_independent_of_cwd(tmp_path, monkeypatch):
    monkeypatch.delenv("ZLIBRARY_OUTPUT_ROOT", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    expected = (
        tmp_path
        / ("local" if os.name == "nt" else "data")
        / "zlibrary-mcp"
        / "downloads"
    )
    for name in ("first", "second"):
        cwd = tmp_path / name
        cwd.mkdir()
        monkeypatch.chdir(cwd)
        assert acquisition.output_directory(None) == expected
    if os.name != "nt":
        monkeypatch.delenv("XDG_DATA_HOME")
        assert (
            acquisition.output_directory(None)
            == Path.home() / ".local/share/zlibrary-mcp/downloads"
        )


def test_relative_output_is_root_relative(tmp_path, monkeypatch):
    root = tmp_path / "root"
    monkeypatch.setenv("ZLIBRARY_OUTPUT_ROOT", str(root))
    monkeypatch.chdir(tmp_path)
    assert acquisition.output_directory("nested") == root / "nested"
    assert acquisition.output_directory(str(root / "inside")) == root / "inside"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "unsafe", ["..", "a/../b", "~/books", "~someone/books", "outside", "symlink"]
)
@pytest.mark.parametrize("unrestricted", ["0", "1"])
async def test_refusals_precede_provider_contact(
    tmp_path, monkeypatch, unsafe, unrestricted
):
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setenv("ZLIBRARY_OUTPUT_ROOT", str(root))
    monkeypatch.setenv("ZLIBRARY_UNRESTRICTED_OUTPUT", unrestricted)
    if unsafe in {"outside", "symlink"}:
        if unrestricted == "1":
            pytest.skip("unrestricted mode deliberately permits outside resolved paths")
        outside = tmp_path / "elsewhere"
        if unsafe == "symlink":
            (root / "link").symlink_to(outside, target_is_directory=True)
            unsafe = "link"
        else:
            unsafe = str(outside)
    provider = AsyncMock(side_effect=AssertionError("no provider contact"))
    with pytest.raises(acquisition.AcquisitionError) as caught:
        await acquisition.acquire(BOOK, unsafe, transfer=provider)
    assert caught.value.to_dict()["reason"] == "output_refused"
    assert caught.value.to_dict()["request_issued"] is False
    provider.assert_not_awaited()


def test_unrestricted_lifts_only_containment(tmp_path, monkeypatch):
    root = tmp_path / "root"
    monkeypatch.setenv("ZLIBRARY_OUTPUT_ROOT", str(root))
    monkeypatch.setenv("ZLIBRARY_UNRESTRICTED_OUTPUT", "1")
    assert (
        acquisition.output_directory(str(tmp_path / "outside")) == tmp_path / "outside"
    )
    assert acquisition.output_directory("nested") == root / "nested"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "new_directory", [True, False], ids=["new-levels", "existing-levels"]
)
@pytest.mark.parametrize("staged", [True, False], ids=["staged", "callback-copy"])
@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
async def test_private_new_levels_artifact_and_receipt_preserve_existing_mode(
    tmp_path, monkeypatch, staged, new_directory
):
    monkeypatch.setenv("ZLIBRARY_OUTPUT_ROOT", str(tmp_path))
    tmp_path.chmod(0o755)
    directory = tmp_path / "new" / "nested"
    if not new_directory:
        directory.mkdir(parents=True)
        directory.parent.chmod(0o755)
        directory.chmod(0o755)

    async def copy_callback(book, directory, *, filename, publication_hook):
        stage = Path(directory) / ".stage"
        stage.write_bytes(PAYLOAD)
        target = Path(directory) / acquisition.destination_name(book, filename)
        publication_hook(stage, target)
        target.write_bytes(stage.read_bytes())
        return {"file_path": str(target)}

    previous = os.umask(0o022)
    try:
        result = await acquisition.acquire(
            BOOK, str(directory), transfer=transfer if staged else copy_callback
        )
    finally:
        os.umask(previous)
    assert stat.S_IMODE(tmp_path.stat().st_mode) == 0o755
    for path in (directory.parent, directory):
        assert stat.S_IMODE(path.stat().st_mode) == (0o700 if new_directory else 0o755)
    for path in (Path(result["path"]), Path(result["record"])):
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_relative_environment_root_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("ZLIBRARY_OUTPUT_ROOT", "relative")
    with pytest.raises(acquisition.AcquisitionError, match="ZLIBRARY_OUTPUT_ROOT"):
        acquisition.output_directory(None)
