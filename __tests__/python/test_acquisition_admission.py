"""Occupied-destination admission must precede intent, auth and transfer."""

import hashlib
import json
from pathlib import Path

import pytest
from lib import acquisition as acq
from lib import python_bridge as bridge

PAYLOAD = b"%PDF-1.7\nsynthetic admission artifact"


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["libgen", "zlibrary"])
@pytest.mark.parametrize("corrected", [False, True])
@pytest.mark.parametrize("state", ["modified", "foreign", "intact"])
async def test_occupied_destination_admission(
    tmp_path, monkeypatch, source, corrected, state
):
    book = {
        "source": source,
        "id": "1",
        "hash": "hash1",
        "md5": hashlib.md5(PAYLOAD).hexdigest(),
        "title": "Chosen",
        "extension": "epub" if corrected else "pdf",
    }
    filename = "chosen.epub" if corrected else "chosen.pdf"
    predicted, target = tmp_path / filename, tmp_path / "chosen.pdf"
    transfers, demands, writes = [], [], []

    async def transfer(book, directory, *, filename, publication_hook):
        transfers.append(True)
        if source == "zlibrary":
            demands.append(True)
        stage = tmp_path / ".stage"
        stage.write_bytes(PAYLOAD)
        try:
            publication_hook(stage, target)
            reused = bridge._publish_or_reuse(stage, target)
            return {"file_path": str(target), "publication_reused": reused}
        finally:
            stage.unlink(missing_ok=True)

    if state == "foreign":
        predicted.write_bytes(b"unrelated existing bytes")
    else:
        await acq.acquire(book, str(tmp_path), filename=filename, transfer=transfer)
        if state == "modified":
            target.write_bytes(b"modified existing bytes")
    receipts = {p: p.read_bytes() for p in tmp_path.glob("*.acq.json")}
    files = {p: p.read_bytes() for p in {predicted, target} if p.exists()}
    original_atomic = acq._atomic_json

    def watch_write(*args):
        writes.append(True)
        return original_atomic(*args)

    monkeypatch.setattr(acq, "_atomic_json", watch_write)
    transfers.clear()
    demands.clear()
    if state == "intact":
        reply = await acq.acquire(
            book, str(tmp_path), filename=filename, transfer=transfer
        )
        assert reply["transfer_skipped"] is True
        assert json.loads(Path(reply["record"]).read_text())["state"] == "complete"
    else:
        with pytest.raises(acq.AcquisitionError) as error:
            await acq.acquire(book, str(tmp_path), filename=filename, transfer=transfer)
        assert error.value.reason == "output_refused"
        assert error.value.issued is False
        assert len(str(error.value)) <= 199
        assert "different bytes" in str(error.value)
    assert transfers == demands == writes == []
    assert {p: p.read_bytes() for p in tmp_path.glob("*.acq.json")} == receipts
    assert all(p.read_bytes() == contents for p, contents in files.items())
