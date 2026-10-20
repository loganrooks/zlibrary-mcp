"""Receipt-only acquisition (#267): serve a verified receipt, never write intent or transfer."""

import hashlib
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from lib.acquisition import AcquisitionError, acquire, destination_name
from lib import python_bridge as bridge

BOOK = {
    "id": "42",
    "hash": "abc",
    "title": "Books",
    "author": "Author",
    "extension": "pdf",
}
PAYLOAD = b"%PDF-1.7\nreceipt-only bytes"


async def transfer(book, directory, *, filename, publication_hook):
    stage = Path(directory) / ".test-part"
    stage.write_bytes(PAYLOAD)
    target = Path(directory) / destination_name(book, filename)
    publication_hook(stage, target)
    stage.replace(target)
    return {"file_path": str(target), "publication_reused": False}


def snapshot(directory):
    return {p.name: p.read_bytes() for p in Path(directory).iterdir()}


@pytest.mark.asyncio
async def test_receipt_only_serves_a_verified_receipt_without_transfer(tmp_path):
    provider = AsyncMock(side_effect=transfer)
    first = await acquire(BOOK, str(tmp_path), transfer=provider)
    before = snapshot(tmp_path)
    hit = await acquire(BOOK, str(tmp_path), receipt_only=True, transfer=provider)
    assert hit["transfer_skipped"] is True
    assert hit["path"] == first["path"]
    assert provider.await_count == 1
    assert snapshot(tmp_path) == before


@pytest.mark.asyncio
async def test_receipt_only_miss_writes_no_intent_and_never_transfers(tmp_path):
    provider = AsyncMock(side_effect=transfer)
    miss = await acquire(BOOK, str(tmp_path), receipt_only=True, transfer=provider)
    assert miss == {"receipt_hit": False}
    provider.assert_not_awaited()
    assert list(tmp_path.glob("*.acq.json")) == []


@pytest.mark.asyncio
async def test_receipt_only_modified_artifact_is_a_miss_and_changes_nothing(tmp_path):
    provider = AsyncMock(side_effect=transfer)
    first = await acquire(BOOK, str(tmp_path), transfer=provider)
    Path(first["path"]).write_bytes(b"x" * len(PAYLOAD))
    before = snapshot(tmp_path)
    miss = await acquire(BOOK, str(tmp_path), receipt_only=True, transfer=provider)
    assert miss == {"receipt_hit": False}
    assert provider.await_count == 1
    assert snapshot(tmp_path) == before


@pytest.mark.asyncio
async def test_bridge_receipt_only_never_authenticates_or_downloads(
    tmp_path, monkeypatch
):
    monkeypatch.delenv("ZLIBRARY_EMAIL", raising=False)
    monkeypatch.delenv("ZLIBRARY_PASSWORD", raising=False)
    download = AsyncMock(side_effect=AssertionError("receipt-only must not download"))
    login = AsyncMock(side_effect=AssertionError("receipt-only must not log in"))
    monkeypatch.setattr(bridge, "download_book", download)
    monkeypatch.setattr(bridge, "initialize_eapi_client", login)
    miss = await bridge._dispatch_bridge_function(
        "acquire_book",
        {
            "book_details": {**BOOK, "source": "zlibrary"},
            "output_dir": str(tmp_path),
            "receipt_only": True,
        },
    )
    assert miss == {"receipt_hit": False}
    download.assert_not_awaited()
    login.assert_not_awaited()
    assert list(tmp_path.glob("*.acq.json")) == []


@pytest.mark.asyncio
async def test_receipt_only_foreign_destination_refuses_before_intent(tmp_path):
    # Pinned as accepted (round 2): Node answers this refusal with breaker_open.
    provider = AsyncMock(side_effect=transfer)
    await acquire(BOOK, str(tmp_path), filename="same.pdf", transfer=provider)
    before = snapshot(tmp_path)
    other = {**BOOK, "id": "43", "hash": "def"}
    with pytest.raises(AcquisitionError) as error:
        await acquire(
            other,
            str(tmp_path),
            filename="same.pdf",
            receipt_only=True,
            transfer=provider,
        )
    assert error.value.reason == "output_refused"
    assert error.value.issued is False
    assert provider.await_count == 1
    assert snapshot(tmp_path) == before


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["hashed-intent", "missing-canonical", "stale-alias"])
async def test_receipt_only_serves_recovery_states_without_writing(tmp_path, case):
    # Breaker gate round 1: these recovery states used to repair receipts in place.
    target = tmp_path / ("selected.pdf" if case == "hashed-intent" else "actual.epub")
    target.write_bytes(PAYLOAD)
    record = {
        "record_version": 1,
        "state": "complete",
        "path": str(target),
        "sha256": hashlib.sha256(PAYLOAD).hexdigest(),
        "bytes": len(PAYLOAD),
        "source": "zlibrary",
        "identifiers": {"id": "42", "hash": "abc"},
        "reused": False,
        "transfer_skipped": False,
    }
    alias = tmp_path / "selected.pdf.acq.json"
    if case == "hashed-intent":
        alias.write_text(json.dumps({**record, "state": "intent"}))
    elif case == "missing-canonical":
        alias.write_text(json.dumps(record))
    else:
        Path(str(target) + ".acq.json").write_text(json.dumps(record))
        alias.write_text(json.dumps({**record, "downloaded_at": "old-alias"}))
    before = snapshot(tmp_path)
    provider = AsyncMock(side_effect=AssertionError("receipt-only must not transfer"))
    hit = await acquire(
        {**BOOK, "source": "zlibrary"},
        str(tmp_path),
        filename="selected.pdf",
        receipt_only=True,
        transfer=provider,
    )
    provider.assert_not_awaited()
    assert hit["transfer_skipped"] is True
    assert hit["path"] == str(target)
    assert Path(hit["record"]).exists()
    assert snapshot(tmp_path) == before
