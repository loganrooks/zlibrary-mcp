"""Validate receipts actually persisted by offline acquisition against v1."""

import hashlib
import json
from pathlib import Path
from unittest.mock import AsyncMock

from jsonschema import Draft202012Validator, FormatChecker
import pytest

from lib.acquisition import acquire

SCHEMA = Path(__file__).resolve().parents[2] / "docs/schemas/acq-record-v1.schema.json"
PAYLOAD = b"%PDF-1.7\noffline receipt contract"
REQUEST = {
    "ref": "r-offline",
    "query": "edition",
    "item_id": "item-1",
    "why_chosen": "translator",
}


@pytest.fixture
def validator():
    schema = json.loads(SCHEMA.read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


@pytest.mark.parametrize("source", ["zlibrary", "libgen", "annas_archive"])
@pytest.mark.asyncio
async def test_real_intent_checkpoint_complete_and_reuse_validate(
    tmp_path, monkeypatch, validator, source
):
    monkeypatch.setenv("ZLIBRARY_OUTPUT_ROOT", str(tmp_path))
    book = {
        "source": source,
        "id": "42",
        "hash": "catalog-hash",
        "md5": "A" * 32,
        "title": "Edition",
        "extension": "epub",
        "year": 2026,
        "pages": 123,
        "isbn": ["9780000000000"],
        "author": "Author",
        "translator": "Translator",
    }
    initial_path = tmp_path / "chosen.epub.acq.json"
    canonical_path = tmp_path / "chosen.pdf.acq.json"
    observed = []

    def read_valid(path):
        record = json.loads(path.read_text())
        validator.validate(record)
        # Keep the contract's field inventory synchronized with the real writer.
        assert set(record) <= set(validator.schema["properties"])
        observed.append(record)
        return record

    async def transfer(book, directory, *, filename, publication_hook):
        initial = read_valid(initial_path)
        assert initial["state"] == "intent"
        assert initial["bytes"] is None and initial["sha256"] is None
        assert initial["request"] == REQUEST
        stage = Path(directory) / ".offline-stage"
        stage.write_bytes(PAYLOAD)
        target = Path(directory) / "chosen.pdf"
        publication_hook(stage, target)
        assert not target.exists()
        alias, canonical = read_valid(initial_path), read_valid(canonical_path)
        assert alias == canonical
        assert canonical["state"] == "intent"
        assert canonical["sha256"] == hashlib.sha256(PAYLOAD).hexdigest()
        assert canonical["bytes"] == len(PAYLOAD)
        assert canonical["format"] == "pdf"
        stage.replace(target)
        return {
            "file_path": str(target),
            "provenance": {
                "route": "offline",
                "mirror": None,
                "host": "fixture.invalid",
            },
        }

    result = await acquire(
        book, str(tmp_path), filename="chosen.epub", request=REQUEST, transfer=transfer
    )
    complete = read_valid(Path(result["record"]))
    assert read_valid(initial_path) == complete
    assert complete["state"] == "complete"
    assert complete["year"] == 2026 and complete["isbn"] == ["9780000000000"]
    assert complete["publisher"] is None
    assert complete["source"] == ("annas" if source == "annas_archive" else source)
    assert complete["identifiers"] == (
        {"id": "42", "hash": "catalog-hash"}
        if source == "zlibrary"
        else {"md5": "a" * 32}
    )
    raw = Path(result["record"]).read_bytes()
    forbidden = AsyncMock(
        side_effect=AssertionError("receipt reuse must remain offline")
    )
    reused = await acquire(
        book, str(tmp_path), filename="chosen.epub", transfer=forbidden
    )
    forbidden.assert_not_awaited()
    assert reused["transfer_skipped"] is True
    assert complete["transfer_skipped"] is False
    assert Path(reused["record"]).read_bytes() == raw
    assert [r["state"] for r in observed] == [
        "intent",
        "intent",
        "intent",
        "complete",
        "complete",
    ]
    validator.validate({**complete, "future_additive_key": {"ignored": True}})
    assert not validator.is_valid({**complete, "record_version": 2})
    assert not validator.is_valid({**complete, "sha256": None, "bytes": None})


@pytest.mark.asyncio
async def test_published_hashed_intent_recovers_to_valid_complete(
    tmp_path, monkeypatch, validator
):
    monkeypatch.setenv("ZLIBRARY_OUTPUT_ROOT", str(tmp_path))
    book = {
        "source": "zlibrary",
        "id": "42",
        "hash": "catalog-hash",
        "title": "Recovery",
        "extension": "pdf",
    }

    async def interrupted(book, directory, *, filename, publication_hook):
        stage = Path(directory) / ".offline-stage"
        target = Path(directory) / "recovery.pdf"
        stage.write_bytes(PAYLOAD)
        publication_hook(stage, target)
        stage.replace(target)
        raise RuntimeError("interrupted after publication")

    with pytest.raises(RuntimeError, match="interrupted after publication"):
        await acquire(
            book, str(tmp_path), filename="recovery.pdf", transfer=interrupted
        )
    sidecar = tmp_path / "recovery.pdf.acq.json"
    intent = json.loads(sidecar.read_text())
    validator.validate(intent)
    assert intent["state"] == "intent" and intent["sha256"] is not None
    forbidden = AsyncMock(side_effect=AssertionError("recovery must remain offline"))
    recovered = await acquire(
        book, str(tmp_path), filename="recovery.pdf", transfer=forbidden
    )
    forbidden.assert_not_awaited()
    complete = json.loads(sidecar.read_text())
    validator.validate(complete)
    assert complete["state"] == "complete"
    assert complete["transfer_skipped"] is True and complete["reused"] is False
    assert recovered["transfer_skipped"] is True
    assert complete["downloaded_at"] == intent["downloaded_at"]
