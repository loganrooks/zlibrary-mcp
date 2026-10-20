"""Severe canonical receipt/process controls, independent of live acquisition."""

import asyncio
import errno
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import AsyncMock

import pytest
from lib import acquisition as acq
from lib import python_bridge as bridge

WORKER = Path(__file__).with_name("acquisition_process_worker.py")
PAYLOAD = b"%PDF-1.7\nidentical synthetic bytes"
BOOK = {
    "id": "1",
    "hash": "hash1",
    "title": "Chosen",
    "author": "Fixture",
    "extension": "epub",
}


def processes(directory, specs):
    children = [
        subprocess.Popen(
            [sys.executable, "-B", str(WORKER), str(directory), json.dumps(spec)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for spec in specs
    ]
    try:
        if all(s.get("barrier") for s in specs):
            deadline = time.monotonic() + 7
            while not all((directory / f"ready-{s['id']}").exists() for s in specs):
                assert time.monotonic() < deadline, (
                    "transfers did not overlap before checkpoint"
                )
                assert all(c.poll() is None for c in children), (
                    "worker exited before checkpoint"
                )
                time.sleep(0.01)
            (directory / "go").touch()
        outputs = [c.communicate(timeout=12) for c in children]
        assert [c.returncode for c in children] == [0] * len(children), [
            (c.returncode, err[-600:]) for c, (_, err) in zip(children, outputs)
        ]
        return [json.loads(out) for out, _ in outputs]
    finally:
        for c in children:
            if c.poll() is None:
                c.kill()
            c.communicate(timeout=5)


def assert_consistent(directory, results):
    for result in results:
        if result["status"] == "ok":
            record = json.loads(Path(result["reply"]["record"]).read_text())
            assert record["identifiers"]["id"] == result["id"]
    for path in directory.glob("*.acq.json"):
        record = json.loads(path.read_text())
        if record.get("sha256") and Path(record["path"]).exists():
            canonical = json.loads(Path(record["path"] + ".acq.json").read_text())
            assert canonical["identifiers"] == record["identifiers"]
            assert canonical["sha256"] == record["sha256"]


def test_two_process_corrected_target_identical_bytes_cannot_replace_identity(tmp_path):
    results = processes(
        tmp_path,
        [
            {
                "id": "1",
                "initial": "chosen.epub",
                "target": "chosen.pdf",
                "barrier": True,
                "after_checkpoint_delay": 0.2,
            },
            {
                "id": "2",
                "initial": "chosen.pdf",
                "target": "chosen.pdf",
                "barrier": True,
                "after_checkpoint_delay": 0.2,
            },
        ],
    )
    assert sum(r["status"] == "ok" for r in results) == 1
    refusal = next(r for r in results if r["status"] == "refused")
    assert refusal["reason"] in {"breaker_open", "output_refused"}
    assert refusal["request_issued"] is True
    assert_consistent(tmp_path, results)


def test_opposing_format_swaps_finish_without_nested_wait(tmp_path):
    results = processes(
        tmp_path,
        [
            {
                "id": "1",
                "initial": "chosen.epub",
                "target": "chosen.pdf",
                "barrier": True,
                "after_checkpoint_delay": 0.2,
            },
            {
                "id": "2",
                "initial": "chosen.pdf",
                "target": "chosen.epub",
                "barrier": True,
            },
        ],
    )
    assert all(
        r["status"] == "ok" or (r["reason"] == "breaker_open" and r["request_issued"])
        for r in results
    )
    assert_consistent(tmp_path, results)


def test_unrelated_transfers_overlap_before_checkpoint(tmp_path):
    results = processes(
        tmp_path,
        [
            {"id": "1", "initial": "one.epub", "target": "one.pdf", "barrier": True},
            {"id": "2", "initial": "two.epub", "target": "two.pdf", "barrier": True},
        ],
    )
    assert all(r["status"] == "ok" for r in results)
    assert_consistent(tmp_path, results)


def test_same_initial_two_processes_issue_only_one_transfer(tmp_path):
    spec = {"id": "1", "initial": "chosen.epub", "target": "chosen.pdf"}
    results = processes(tmp_path, [spec, spec])
    assert all(r["status"] == "ok" for r in results)
    assert sorted(r["reply"]["transfer_skipped"] for r in results) == [False, True]
    assert (tmp_path / "transfers").read_text().splitlines() == ["1"]
    assert_consistent(tmp_path, results)


@pytest.mark.parametrize(
    "phase", ["canonical_intent", "alias_intent", "published", "canonical_complete"]
)
@pytest.mark.asyncio
async def test_crash_phases_preserve_canonical_reservation_and_same_identity_recovery(
    tmp_path, phase
):
    spec = {"id": "1", "initial": "chosen.epub", "target": "chosen.pdf", "phase": phase}
    child = subprocess.run(
        [sys.executable, "-B", str(WORKER), str(tmp_path), json.dumps(spec)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert child.returncode == 23, child.stderr[-600:]
    canonical = tmp_path / "chosen.pdf.acq.json"
    reserved = json.loads(canonical.read_text())
    assert reserved["identifiers"] == {"id": "1", "hash": "hash1"}
    assert reserved["sha256"] == hashlib.sha256(PAYLOAD).hexdigest()
    foreign = AsyncMock(
        side_effect=AssertionError("foreign takeover contacted provider")
    )
    with pytest.raises(acq.AcquisitionError) as error:
        await acq.acquire(
            {**BOOK, "id": "2", "hash": "hash2", "extension": "pdf"},
            str(tmp_path),
            filename="chosen.pdf",
            transfer=foreign,
        )
    assert error.value.reason == "output_refused"
    foreign.assert_not_awaited()
    assert_consistent(tmp_path, [])
    recovered = processes(
        tmp_path, [{"id": "1", "initial": "chosen.epub", "target": "chosen.pdf"}]
    )[0]
    assert recovered["status"] == "ok"
    assert recovered["reply"]["transfer_skipped"] is (
        phase in {"published", "canonical_complete"}
    )
    assert_consistent(tmp_path, [recovered])


@pytest.mark.asyncio
async def test_same_identity_canonical_complete_preserves_bytes_and_provenance(
    tmp_path,
):
    first = processes(
        tmp_path, [{"id": "1", "initial": "chosen.pdf", "target": "chosen.pdf"}]
    )[0]
    canonical = Path(first["reply"]["record"])
    original = canonical.read_bytes()
    second = processes(
        tmp_path, [{"id": "1", "initial": "chosen.epub", "target": "chosen.pdf"}]
    )[0]
    assert second["status"] == "ok"
    assert second["reply"]["reused"] is True
    assert second["reply"]["transfer_skipped"] is False
    assert canonical.read_bytes() == original
    assert_consistent(tmp_path, [first, second])


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", ["missing", "repeat", "mismatch"])
async def test_acquire_requires_exactly_one_checkpoint_and_bound_return_target(
    tmp_path, fault
):
    async def transfer(book, directory, *, filename, publication_hook):
        stage, target = tmp_path / ".stage-contract", tmp_path / "chosen.pdf"
        stage.write_bytes(PAYLOAD)
        try:
            if fault != "missing":
                publication_hook(stage, target)
                if fault == "repeat":
                    publication_hook(stage, target)
            bridge._publish_or_reuse(stage, target)
            other = tmp_path / "other.pdf"
            if fault == "mismatch":
                other.write_bytes(PAYLOAD)
            return {"file_path": str(other if fault == "mismatch" else target)}
        finally:
            stage.unlink(missing_ok=True)

    with pytest.raises(acq.AcquisitionError) as error:
        await acq.acquire(
            BOOK, str(tmp_path), filename="chosen.epub", transfer=transfer
        )
    assert error.value.reason == "internal"
    assert error.value.issued is True
    # Every lease released, even when the transfer violated its contract.
    async with acq.destination_lock(tmp_path / "chosen.epub", 0):
        async with acq.destination_lock(tmp_path / "chosen.pdf", 0):
            pass


@pytest.mark.asyncio
async def test_alias_recovery_leases_canonical_before_hashing_it(tmp_path, monkeypatch):
    processes(tmp_path, [{"id": "1", "initial": "chosen.epub", "target": "chosen.pdf"}])
    original_hash = acq._hash

    def guarded_hash(path):
        if path == tmp_path / "chosen.pdf":
            with pytest.raises(acq.AcquisitionError) as error:
                with acq.DestinationLease(path, 0):
                    pytest.fail("alias artifact inspected without canonical lease")
            assert error.value.reason == "breaker_open"
        return original_hash(path)

    monkeypatch.setattr(acq, "_hash", guarded_hash)
    provider = AsyncMock(side_effect=AssertionError("recovery must not transfer"))
    result = await acq.acquire(
        BOOK, str(tmp_path), filename="chosen.epub", transfer=provider
    )
    assert result["transfer_skipped"] is True
    provider.assert_not_awaited()


@pytest.mark.asyncio
async def test_alias_recovery_busy_canonical_is_pretransfer_and_nonwaiting(tmp_path):
    processes(tmp_path, [{"id": "1", "initial": "chosen.epub", "target": "chosen.pdf"}])
    original = (tmp_path / "chosen.epub.acq.json").read_bytes()
    provider = AsyncMock()
    with acq.DestinationLease(tmp_path / "chosen.pdf", 0):
        with pytest.raises(acq.AcquisitionError) as error:
            await asyncio.wait_for(
                acq.acquire(
                    BOOK, str(tmp_path), filename="chosen.epub", transfer=provider
                ),
                timeout=0.5,
            )
    assert error.value.to_dict() == {"reason": "breaker_open", "request_issued": False}
    provider.assert_not_awaited()
    assert (tmp_path / "chosen.epub.acq.json").read_bytes() == original


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fault",
    [
        "hash",
        "canonical_intent",
        "alias_intent",
        "publication",
        "canonical_complete",
        "alias_complete",
        "cancel",
        "transfer",
    ],
)
async def test_bridge_failure_cleanup_releases_every_lease_and_owned_stage(
    tmp_path, monkeypatch, fault
):
    stage = tmp_path / ".source-failure.pdf"
    book = {
        "source": "libgen",
        "md5": hashlib.md5(PAYLOAD).hexdigest(),
        "extension": "epub",
        "title": "Book",
    }

    async def fetch(*args):
        if fault == "transfer":
            raise RuntimeError("synthetic transfer failure")
        stage.write_bytes(PAYLOAD)
        return bridge._DownloadedPath(str(stage), "signature")

    monkeypatch.setattr(bridge, "_fetch_from_source", fetch)
    atomic, hash_file, publish = acq._atomic_json, acq._hash, bridge._publish_or_reuse

    def write(path, record):
        if record.get("sha256"):
            canonical = path.name == "chosen.pdf.acq.json"
            point = ("canonical_" if canonical else "alias_") + record["state"]
            if fault == point:
                raise OSError("synthetic receipt failure")
            if fault == "cancel" and point == "canonical_intent":
                raise asyncio.CancelledError()
        atomic(path, record)

    def digest(path):
        if fault == "hash" and path == stage:
            raise OSError("synthetic hash failure")
        return hash_file(path)

    def publication(*args):
        if fault == "publication":
            raise RuntimeError("synthetic publication failure")
        return publish(*args)

    monkeypatch.setattr(acq, "_atomic_json", write)
    monkeypatch.setattr(acq, "_hash", digest)
    monkeypatch.setattr(bridge, "_publish_or_reuse", publication)
    with pytest.raises((OSError, RuntimeError, asyncio.CancelledError)):
        await acq.acquire(
            book, str(tmp_path), filename="chosen.epub", transfer=bridge.download_book
        )
    assert not stage.exists()
    async with acq.destination_lock(tmp_path / "chosen.epub", 0):
        async with acq.destination_lock(tmp_path / "chosen.pdf", 0):
            pass
    if (tmp_path / "chosen.pdf").exists():
        assert (tmp_path / "chosen.pdf").read_bytes() == PAYLOAD


@pytest.mark.asyncio
async def test_direct_unhooked_bridge_still_publishes_original_file(
    tmp_path, monkeypatch
):
    async def fetch(*args):
        stage = tmp_path / ".source-direct.pdf"
        stage.write_bytes(PAYLOAD)
        return bridge._DownloadedPath(str(stage), "signature")

    monkeypatch.setattr(bridge, "_fetch_from_source", fetch)
    reply = await bridge.download_book(
        {
            "source": "libgen",
            "md5": hashlib.md5(PAYLOAD).hexdigest(),
            "title": "Book",
            "extension": "pdf",
        },
        str(tmp_path),
    )
    assert Path(reply["file_path"]).read_bytes() == PAYLOAD
    assert not list(tmp_path.glob(".source-*"))


def seed_read_receipt(directory, *, alias=False):
    book = {
        "source": "libgen",
        "md5": hashlib.md5(PAYLOAD).hexdigest(),
        "title": "Chosen",
        "author": "Fixture",
        "extension": "epub",
    }
    target = directory / "chosen.pdf"
    target.write_bytes(PAYLOAD)
    canonical = Path(str(target) + ".acq.json")
    record = {
        "record_version": 1,
        "state": "complete",
        "path": str(target),
        "bytes": len(PAYLOAD),
        "sha256": hashlib.sha256(PAYLOAD).hexdigest(),
        "source": "libgen",
        "identifiers": {"md5": book["md5"]},
        "provenance": {"route": "original", "mirror": "held", "host": None},
        "reused": False,
        "transfer_skipped": False,
    }
    canonical.write_text(json.dumps(record))
    if alias:
        (directory / "chosen.epub.acq.json").write_bytes(canonical.read_bytes())
    return book, target, canonical


@pytest.mark.asyncio
@pytest.mark.parametrize("code", [errno.EACCES, errno.EIO])
@pytest.mark.parametrize(
    "phase,issued",
    [
        ("initial", False),
        ("canonical_recovery", False),
        ("checkpoint", True),
        ("post_publication", True),
    ],
)
async def test_receipt_io_failure_refuses_without_erasing_provenance_or_false_boundary(
    tmp_path, monkeypatch, code, phase, issued
):
    book, target, canonical = seed_read_receipt(
        tmp_path, alias=phase == "canonical_recovery"
    )
    alias = tmp_path / "chosen.epub.acq.json"
    originals = {p: p.read_bytes() for p in tmp_path.glob("*.acq.json")}
    filename = "chosen.pdf" if phase == "initial" else "chosen.epub"
    if phase == "initial":
        book["extension"] = "pdf"
    faulty = alias if phase == "post_publication" else canonical
    stage = tmp_path / ".source-read-failure.pdf"
    fetches, observed = [], []
    published = False
    read, publish = Path.read_text, bridge._publish_or_reuse

    async def fetch(*args):
        fetches.append(True)
        stage.write_bytes(PAYLOAD)
        return bridge._DownloadedPath(str(stage), "signature")

    def publication(*args):
        nonlocal published
        result = publish(*args)
        published = True
        return result

    def failure(path, *args, **kwargs):
        if path == faulty and (phase != "post_publication" or published):
            observed.append(path.read_bytes())
            raise OSError(code, "synthetic receipt read failure")
        return read(path, *args, **kwargs)

    monkeypatch.setattr(bridge, "_fetch_from_source", fetch)
    monkeypatch.setattr(bridge, "_publish_or_reuse", publication)
    monkeypatch.setattr(Path, "read_text", failure)
    with pytest.raises(acq.AcquisitionError) as error:
        await acq.acquire(
            book, str(tmp_path), filename=filename, transfer=bridge.download_book
        )
    assert error.value.to_dict() == {
        "reason": "output_refused",
        "request_issued": issued,
    }
    assert len(fetches) == (1 if issued else 0)
    assert observed and faulty.read_bytes() == observed[0]
    for path, contents in originals.items():
        assert path.read_bytes() == contents
    assert target.read_bytes() == PAYLOAD
    assert not stage.exists()
    for name in {filename, "chosen.pdf"}:
        with acq.DestinationLease(tmp_path / name, 0):
            pass


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["initial", "canonical_recovery"])
@pytest.mark.parametrize("kind", ["external_symlink", "dangling_symlink", "directory"])
async def test_receipt_nonregular_path_refuses_without_reading_or_following_it(
    tmp_path, monkeypatch, phase, kind
):
    directory = tmp_path / "output"
    directory.mkdir()
    monkeypatch.setenv("ZLIBRARY_OUTPUT_ROOT", str(directory))
    book, target, canonical = seed_read_receipt(
        directory, alias=phase == "canonical_recovery"
    )
    original_record = canonical.read_bytes()
    canonical.unlink()
    external = tmp_path / "outside-root.json"
    if kind == "directory":
        canonical.mkdir()
    else:
        if kind == "external_symlink":
            external.write_bytes(original_record)
        canonical.symlink_to(external)
    before = canonical.lstat()
    reads = []
    read = Path.read_text

    def watch(path, *args, **kwargs):
        if path in {canonical, external}:
            reads.append(path)
        return read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", watch)
    provider = AsyncMock(
        side_effect=AssertionError("nonregular receipt reached provider")
    )
    if phase == "initial":
        book["extension"] = "pdf"
    with pytest.raises(acq.AcquisitionError) as error:
        await acq.acquire(
            book,
            str(directory),
            filename="chosen.pdf" if phase == "initial" else "chosen.epub",
            transfer=provider,
        )
    assert error.value.to_dict() == {
        "reason": "output_refused",
        "request_issued": False,
    }
    provider.assert_not_awaited()
    assert reads == []
    assert (canonical.lstat().st_dev, canonical.lstat().st_ino) == (
        before.st_dev,
        before.st_ino,
    )
    assert target.read_bytes() == PAYLOAD
    if kind == "external_symlink":
        assert external.read_bytes() == original_record
    elif kind == "dangling_symlink":
        assert canonical.is_symlink() and not external.exists()
    else:
        assert canonical.is_dir()


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", [None, "{bad", "[]", "null", '"scalar"'])
async def test_missing_or_deliberately_malformed_receipt_still_allows_fresh_acquisition(
    tmp_path, raw
):
    receipt = tmp_path / "chosen.pdf.acq.json"
    if raw is not None:
        receipt.write_text(raw)
    calls = []

    async def transfer(book, directory, *, filename, publication_hook):
        calls.append(True)
        stage, target = tmp_path / ".stage-missing", tmp_path / "chosen.pdf"
        stage.write_bytes(PAYLOAD)
        try:
            publication_hook(stage, target)
            reused = bridge._publish_or_reuse(stage, target)
            return {"file_path": str(target), "publication_reused": reused}
        finally:
            stage.unlink(missing_ok=True)

    reply = await acq.acquire(
        {**BOOK, "extension": "pdf"},
        str(tmp_path),
        filename="chosen.pdf",
        transfer=transfer,
    )
    assert reply["transfer_skipped"] is False and len(calls) == 1
    assert json.loads(receipt.read_text())["state"] == "complete"
