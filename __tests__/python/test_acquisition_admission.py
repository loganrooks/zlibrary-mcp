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
        assert "no matching receipt" in str(error.value)
        assert "different bytes" not in str(error.value)
    assert transfers == demands == writes == []
    assert {p: p.read_bytes() for p in tmp_path.glob("*.acq.json")} == receipts
    assert all(p.read_bytes() == contents for p, contents in files.items())


def publication_transfer(directory, calls):
    async def transfer(book, output_dir, *, filename, publication_hook):
        calls.append(True)
        stage, target = directory / ".stage-receipt", directory / "chosen.pdf"
        stage.write_bytes(PAYLOAD)
        try:
            publication_hook(stage, target)
            reused = bridge._publish_or_reuse(stage, target)
            return {"file_path": str(target), "publication_reused": reused}
        finally:
            stage.unlink(missing_ok=True)

    return transfer


def admission_book(source, corrected):
    return {
        "source": source,
        "id": "1",
        "hash": "hash1",
        "md5": hashlib.md5(PAYLOAD).hexdigest(),
        "title": "Chosen",
        "extension": "epub" if corrected else "pdf",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["libgen", "zlibrary"])
async def test_format_corrected_receipt_hit_ignores_occupied_predicted_name(
    tmp_path, source
):
    calls = []
    transfer = publication_transfer(tmp_path, calls)
    book = admission_book(source, corrected=True)
    first = await acq.acquire(
        book, str(tmp_path), filename="chosen.epub", transfer=transfer
    )
    assert Path(first["path"]) == tmp_path / "chosen.pdf"
    predicted = tmp_path / "chosen.epub"
    predicted.write_bytes(b"unrelated file at predicted name")
    receipts = {p: p.read_bytes() for p in tmp_path.glob("*.acq.json")}
    calls.clear()

    repeated = await acq.acquire(
        book, str(tmp_path), filename="chosen.epub", transfer=transfer
    )

    assert repeated["transfer_skipped"] is True
    assert repeated["path"] == first["path"]
    assert calls == []
    assert predicted.read_bytes() == b"unrelated file at predicted name"
    assert Path(repeated["path"]).read_bytes() == PAYLOAD
    assert {p: p.read_bytes() for p in tmp_path.glob("*.acq.json")} == receipts


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["libgen", "zlibrary"])
@pytest.mark.parametrize("corrected", [False, True])
async def test_deleted_receipt_artifact_redownloads_once(tmp_path, source, corrected):
    calls = []
    transfer = publication_transfer(tmp_path, calls)
    book = admission_book(source, corrected)
    filename = "chosen.epub" if corrected else "chosen.pdf"
    first = await acq.acquire(book, str(tmp_path), filename=filename, transfer=transfer)
    assert len(calls) == 1
    Path(first["path"]).unlink()
    calls.clear()

    repeated = await acq.acquire(
        book, str(tmp_path), filename=filename, transfer=transfer
    )

    assert repeated["transfer_skipped"] is False
    assert calls == [True]
    assert Path(repeated["path"]).read_bytes() == PAYLOAD
    assert repeated["bytes"] == len(PAYLOAD)
    receipts = list(tmp_path.glob("*.acq.json"))
    assert Path(repeated["record"]) in receipts
    for path in receipts:
        record = json.loads(path.read_text())
        assert record["state"] == "complete"
        assert record["path"] == repeated["path"]
        assert record["bytes"] == len(PAYLOAD)
        assert record["sha256"] == hashlib.sha256(PAYLOAD).hexdigest()
