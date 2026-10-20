"""A successful final link commits even when removing its staging name fails."""

import json
from pathlib import Path

import pytest

from lib import acquisition as acq
from lib import python_bridge as bridge
from lib.sources.net import WalkDeadline


@pytest.mark.asyncio
@pytest.mark.parametrize("persistent", [False, True])
async def test_final_link_commits_before_best_effort_stage_cleanup(
    tmp_path, monkeypatch, persistent
):
    """Catch unlink-before-commit and a later cleanup retry replacing success."""
    now = [0.0]
    monkeypatch.setattr(
        acq, "WalkDeadline", lambda budget: WalkDeadline(budget, clock=lambda: now[0])
    )
    stage, target = tmp_path / ".source-fixture.pdf", tmp_path / "chosen.pdf"
    payload = b"%PDF-1.7\npublished despite stage unlink failure"
    unlink, link = Path.unlink, bridge.os.link
    commits = []

    def fail_stage_unlink(path, *args, **kwargs):
        if path == stage and target.exists():
            commits.append(acq._acquisition_scope.get()["published"])
            if persistent or len(commits) == 1:
                raise PermissionError("synthetic stage unlink refusal")
        return unlink(path, *args, **kwargs)

    def final_link(source, destination):
        link(source, destination)
        now[0] += 10000.0  # Any late cooperative refusal would strand the receipt.

    async def fetch(*args):
        stage.write_bytes(payload)
        return bridge._DownloadedPath(str(stage), "signature")

    monkeypatch.setattr(Path, "unlink", fail_stage_unlink)
    monkeypatch.setattr(bridge.os, "link", final_link)
    monkeypatch.setattr(bridge, "_fetch_from_source", fetch)
    book = {"source": "libgen", "md5": "a" * 32, "extension": "pdf"}
    result = await acq.acquire(
        book, str(tmp_path), filename="chosen.pdf", transfer=bridge.download_book
    )
    assert commits and all(commits)
    assert target.read_bytes() == payload
    assert json.loads(Path(result["record"]).read_text())["state"] == "complete"
    assert stage.exists() is persistent

    async def forbidden(*args, **kwargs):
        pytest.fail("committed receipt replayed its provider transfer")

    hit = await acq.acquire(
        book, str(tmp_path), filename="chosen.pdf", transfer=forbidden
    )
    assert hit["transfer_skipped"] is True
    assert hit["path"] == str(target)


@pytest.mark.asyncio
async def test_eapi_cleanup_cannot_replace_a_committed_receipt(tmp_path, monkeypatch):
    """The EAPI-owned directory is another retry of cleanup after final link."""
    from types import SimpleNamespace

    target = tmp_path / "chosen.pdf"
    cleanup, commits = [], []
    temporary_directory, unlink = bridge.tempfile.TemporaryDirectory, Path.unlink

    def staging_directory(**kwargs):
        directory = temporary_directory(**kwargs)
        cleanup.append(directory.cleanup)

        def refuse_cleanup():
            assert target.exists()
            raise PermissionError("synthetic persistent directory cleanup refusal")

        directory.cleanup = refuse_cleanup
        return directory

    async def download_file(*, output_dir, **kwargs):
        stage = Path(output_dir) / "provider.pdf"
        stage.write_bytes(b"%PDF-1.7\nsynthetic EAPI artifact")
        return str(stage)

    async def get_client():
        return SimpleNamespace(download_file=download_file)

    def fail_stage_unlink(path, *args, **kwargs):
        if path.name == "provider.pdf" and target.exists():
            commits.append(acq._acquisition_scope.get()["published"])
            raise PermissionError("synthetic persistent stage unlink refusal")
        return unlink(path, *args, **kwargs)

    monkeypatch.setattr(bridge, "get_eapi_client", get_client)
    monkeypatch.setattr(bridge.tempfile, "TemporaryDirectory", staging_directory)
    monkeypatch.setattr(Path, "unlink", fail_stage_unlink)
    try:
        result = await acq.acquire(
            {"source": "zlibrary", "id": "17", "hash": "fixture", "extension": "pdf"},
            str(tmp_path),
            filename="chosen.pdf",
            transfer=bridge.download_book,
        )
        assert commits == [True]
        assert json.loads(Path(result["record"]).read_text())["state"] == "complete"
        assert target.read_bytes().startswith(b"%PDF-")
    finally:
        for release in cleanup:
            release()
