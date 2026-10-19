"""Offline acquisition invariants; fake only the provider transfer boundary."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import AsyncMock

import pytest
from lib.acquisition import acquire, AcquisitionError
from lib import python_bridge as bridge

BOOK = {
    "id": "42",
    "hash": "abc",
    "title": "Books",
    "author": "Author",
    "extension": "pdf",
}
PAYLOAD = b"%PDF-1.7\noriginal bytes"


async def transfer(book, directory, *, filename, publication_hook):
    from lib.acquisition import destination_name

    stage = Path(directory) / ".test-part"
    stage.write_bytes(PAYLOAD)
    target = Path(directory) / destination_name(book, filename)
    publication_hook(stage, target)
    if target.exists() and target.read_bytes() != PAYLOAD:
        raise FileExistsError("Refusing to overwrite different bytes")
    stage.replace(target)
    return {"file_path": str(target), "publication_reused": False}


@pytest.mark.asyncio
async def test_sha256_reuse_refuses_same_size_altered_file(tmp_path):
    provider = AsyncMock(side_effect=transfer)
    first = await acquire(BOOK, str(tmp_path), transfer=provider)
    assert first["verified"] == "sha256"
    again = await acquire(BOOK, str(tmp_path), transfer=provider)
    assert again["transfer_skipped"] is True
    assert provider.await_count == 1
    Path(first["path"]).write_bytes(b"x" * len(PAYLOAD))
    with pytest.raises(FileExistsError):
        await acquire(BOOK, str(tmp_path), transfer=provider)
    assert provider.await_count == 2  # not a checksum-blind quota-free success


@pytest.mark.asyncio
async def test_intent_written_before_transfer_and_sha_checkpoint_before_publication(
    tmp_path,
):
    async def crash(book, directory, *, filename, publication_hook):
        records = list(Path(directory).glob("*.acq.json"))
        assert json.loads(records[0].read_text())["state"] == "intent"
        stage = Path(directory) / ".stage"
        stage.write_bytes(PAYLOAD)
        from lib.acquisition import destination_name

        publication_hook(stage, Path(directory) / destination_name(book, filename))
        raise RuntimeError("simulated crash before publication")

    with pytest.raises(RuntimeError, match="simulated crash"):
        await acquire(BOOK, str(tmp_path), transfer=crash)
    record = json.loads(next(tmp_path.glob("*.acq.json")).read_text())
    assert record["state"] == "intent"
    assert record["sha256"] == hashlib.sha256(PAYLOAD).hexdigest()
    assert not Path(record["path"]).exists()
    result = await acquire(BOOK, str(tmp_path), transfer=transfer)
    assert result["transfer_skipped"] is False
    assert json.loads(Path(result["record"]).read_text())["state"] == "complete"


WORKER = r"""
import asyncio, json, os, sys
from pathlib import Path
from lib.acquisition import acquire, destination_name
book = json.loads(sys.argv[2])
async def transfer(book, directory, *, filename, publication_hook):
    with open(Path(directory) / 'transfers', 'a') as h: h.write('issued\n')
    await asyncio.sleep(0.25)
    stage = Path(directory) / ('.stage-' + str(os.getpid()))
    stage.write_bytes(b'%PDF-1.7\noriginal bytes')
    target = Path(directory) / destination_name(book, filename)
    publication_hook(stage, target)
    stage.replace(target)
    if sys.argv[3] == 'crash': os._exit(23)
    return {'file_path': str(target)}
print(json.dumps(asyncio.run(acquire(book, sys.argv[1], transfer=transfer))))
"""


def test_cross_process_download_coalescing_two_real_processes(tmp_path):
    args = [sys.executable, "-c", WORKER, str(tmp_path), json.dumps(BOOK), "normal"]
    processes = [
        subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        for _ in range(2)
    ]
    outputs = [p.communicate(timeout=15) for p in processes]
    assert [p.returncode for p in processes] == [0, 0], outputs
    results = [json.loads(out) for out, _ in outputs]
    assert sorted(r["transfer_skipped"] for r in results) == [False, True]
    assert (tmp_path / "transfers").read_text().splitlines() == ["issued"]
    assert not list(tmp_path.glob("*.lock"))


@pytest.mark.asyncio
async def test_intent_receipt_survives_process_crash_after_publication(tmp_path):
    result = subprocess.run(
        [sys.executable, "-c", WORKER, str(tmp_path), json.dumps(BOOK), "crash"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 23, result.stderr
    provider = AsyncMock(side_effect=AssertionError("must not contact upstream"))
    recovered = await acquire(BOOK, str(tmp_path), transfer=provider)
    assert recovered["transfer_skipped"] is True
    provider.assert_not_awaited()
    record = json.loads(Path(recovered["record"]).read_text())
    assert record["state"] == "complete"


@pytest.mark.asyncio
async def test_output_guard_and_filename_admission_precede_provider_contact(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("ZLIBRARY_OUTPUT_ROOT", str(tmp_path / "root"))
    provider = AsyncMock()
    with pytest.raises(AcquisitionError) as e:
        await acquire(BOOK, str(tmp_path / "elsewhere"), transfer=provider)
    assert e.value.reason == "output_refused"
    with pytest.raises(AcquisitionError):
        await acquire(BOOK, filename="../escape.pdf", transfer=provider)
    provider.assert_not_awaited()


@pytest.mark.asyncio
async def test_bridge_search_and_history_forward_page_and_validate_limits_before_auth(
    monkeypatch,
):
    eapi = AsyncMock()
    eapi.search.return_value = {"books": []}
    eapi.get_downloaded.return_value = {"books": []}
    get = AsyncMock(return_value=eapi)
    monkeypatch.setattr(bridge, "get_eapi_client", get)
    await bridge.search("books", count=3, page=4)
    assert eapi.search.call_args.kwargs["page"] == 4
    await bridge.get_download_history(count=3, page=4)
    eapi.get_downloaded.assert_awaited_once_with(limit=3, page=4)
    get.reset_mock()
    for bad in [0, -1, 51, 1.5, True]:
        with pytest.raises(ValueError):
            await bridge.search("books", count=bad)
        with pytest.raises(ValueError):
            await bridge.get_download_history(count=bad)
    get.assert_not_awaited()


@pytest.mark.asyncio
async def test_bridge_download_authentication_occurs_only_after_receipt_check(
    tmp_path, monkeypatch
):
    await acquire(BOOK, str(tmp_path), transfer=transfer)
    initialize = AsyncMock(side_effect=AssertionError("reuse must not authenticate"))
    monkeypatch.setattr(bridge, "initialize_eapi_client", initialize)
    result = await bridge._dispatch_bridge_function(
        "acquire_book", {"book_details": BOOK, "output_dir": str(tmp_path)}
    )
    assert result["transfer_skipped"] is True
    initialize.assert_not_awaited()


@pytest.mark.asyncio
async def test_bridge_new_transfer_initializes_account_after_intent(
    tmp_path, monkeypatch
):
    initialized = False

    async def initialize():
        nonlocal initialized
        assert (
            json.loads(next(tmp_path.glob("*.acq.json")).read_text())["state"]
            == "intent"
        )
        initialized = True

    async def download(book, directory, **kwargs):
        assert initialized, "EAPI client must be initialized before downloading"
        return await transfer(book, directory, **kwargs)

    monkeypatch.setenv("ZLIBRARY_EMAIL", "offline@example.invalid")
    monkeypatch.setenv("ZLIBRARY_PASSWORD", "offline-password")
    monkeypatch.setattr(bridge, "initialize_eapi_client", initialize)
    monkeypatch.setattr(bridge, "download_book", download)
    result = await bridge._dispatch_bridge_function(
        "acquire_book", {"book_details": BOOK, "output_dir": str(tmp_path)}
    )
    assert result["transfer_skipped"] is False


@pytest.mark.asyncio
async def test_cli_limit_admission_precedes_initialization(monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["python_bridge.py", "search", '{"query":"book","count":0}']
    )
    initialize = AsyncMock()
    monkeypatch.setattr(bridge, "initialize_eapi_client", initialize)
    monkeypatch.setattr(bridge, "_eapi_client", None)
    with pytest.raises(SystemExit):
        await bridge.main()
    initialize.assert_not_awaited()


def test_detail_metadata_keeps_upstream_edition_and_translator():
    from lib.enhanced_metadata import extract_metadata_from_eapi

    result = extract_metadata_from_eapi(
        {"book": {"edition": "Revised", "translator": "A Translator"}}
    )
    assert result["edition"] == "Revised"
    assert result["translator"] == "A Translator"


@pytest.mark.asyncio
async def test_history_keeps_only_an_explicit_upstream_timestamp(monkeypatch):
    eapi = AsyncMock()
    eapi.get_downloaded.return_value = {
        "books": [{**BOOK, "downloaded_at": "2026-10-19T12:00:00Z"}]
    }
    monkeypatch.setattr(bridge, "get_eapi_client", AsyncMock(return_value=eapi))
    rows = await bridge.get_download_history()
    assert rows[0]["downloaded_at"] == "2026-10-19T12:00:00Z"


@pytest.mark.asyncio
async def test_publication_checkpoint_failure_removes_owned_source_staging(
    tmp_path, monkeypatch
):
    staged = tmp_path / ".source-attempt.pdf"

    async def fetch(*args):
        staged.write_bytes(PAYLOAD)
        return str(staged)

    def checkpoint(*args):
        raise OSError("receipt disk error")

    monkeypatch.setattr(bridge, "_fetch_from_source", fetch)
    with pytest.raises(OSError):
        await bridge.download_book(
            {"md5": "0" * 32, "source": "libgen", "title": "Book", "extension": "pdf"},
            str(tmp_path),
            publication_hook=checkpoint,
        )
    assert not staged.exists()


@pytest.mark.asyncio
async def test_symlink_destination_cannot_escape_configured_output_root(
    tmp_path, monkeypatch
):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(PAYLOAD)
    from lib.acquisition import destination_name

    (root / destination_name(BOOK)).symlink_to(outside)
    monkeypatch.setenv("ZLIBRARY_OUTPUT_ROOT", str(root))
    provider = AsyncMock(side_effect=transfer)
    with pytest.raises(AcquisitionError) as error:
        await acquire(BOOK, transfer=provider)
    assert error.value.reason == "output_refused"
    provider.assert_not_awaited()
    assert outside.read_bytes() == PAYLOAD


@pytest.mark.asyncio
async def test_source_quota_and_provenance_reach_reply_and_sidecar(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace
    from lib.sources.config import SourceConfig
    from lib.sources.models import SourceType, QuotaInfo
    import hashlib

    md5 = hashlib.md5(PAYLOAD).hexdigest()

    async def candidates(*args, **kwargs):
        yield SimpleNamespace(
            source=SourceType.ANNAS_ARCHIVE,
            url="https://download.example.invalid/book",
            quota_info=QuotaInfo(4, 10, 6),
        )

    router = SimpleNamespace(config=SourceConfig(), iter_download_candidates=candidates)

    async def stream(*args, **kwargs):
        path = tmp_path / ".source-body.pdf"
        path.write_bytes(PAYLOAD)
        return bridge._DownloadedPath(str(path), "signature")

    monkeypatch.setattr(bridge, "get_source_router", AsyncMock(return_value=router))
    monkeypatch.setattr(bridge, "_download_url_to_file", stream)
    monkeypatch.setenv("ANNAS_SECRET_KEY", "offline")
    result = await bridge._dispatch_bridge_function(
        "acquire_book",
        {
            "book_details": {
                "md5": md5,
                "source": "annas",
                "title": "Book",
                "extension": "pdf",
            },
            "output_dir": str(tmp_path),
        },
    )
    assert result["quota_estimate"]["remaining"] == 4
    assert result["quota_estimate"]["basis"] == "observed"
    record = json.loads(Path(result["record"]).read_text())
    assert record["provenance"]["host"] == "download.example.invalid"
    assert record["provenance"]["route"] == "fast_download"
