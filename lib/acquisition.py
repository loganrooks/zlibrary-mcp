"""Durable per-destination acquisition receipts, independent of provider authentication.

The output-root guard is argument admission, not protection against an operator
concurrently swapping directories. Receipts are not authorization tokens.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time

from lib.filename_utils import create_unified_filename, normalize_document_extension

try:
    import fcntl
except ImportError:  # Windows still uses O_EXCL; no advisory lock available.
    fcntl = None


class AcquisitionError(ValueError):
    def __init__(self, reason, message, *, issued=False):
        super().__init__(message)
        self.reason = reason
        self.issued = issued

    def to_dict(self):
        return {"reason": self.reason, "request_issued": self.issued}


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def destination_name(book, filename=None):
    if filename is None:
        return create_unified_filename(
            book, year=book.get("year", ""), language=book.get("language", "")
        )
    if (
        not isinstance(filename, str)
        or filename in {"", ".", ".."}
        or any(c in filename for c in ("/", "\\", "\x00"))
    ):
        raise AcquisitionError("invalid_argument", "filename must be a basename")
    cleaned = re.sub(r"[^\w. -]", "_", filename).strip(" .")
    if not cleaned:
        raise AcquisitionError(
            "invalid_argument", "filename is empty after sanitization"
        )
    extension = normalize_document_extension(book.get("extension")) or "bin"
    return Path(cleaned).stem[:180] + "." + extension


def output_directory(output_dir):
    root_value = os.environ.get("ZLIBRARY_OUTPUT_ROOT")
    root = Path(root_value).expanduser().resolve() if root_value else None
    directory = (
        Path(output_dir).expanduser().resolve()
        if output_dir
        else root or Path("downloads").resolve()
    )
    if root is not None and not directory.is_relative_to(root):
        raise AcquisitionError(
            "output_refused", "output_dir is outside ZLIBRARY_OUTPUT_ROOT"
        )
    return directory


def _identity(book):
    source = str(book.get("source") or "zlibrary").lower()
    if source == "annas_archive":
        source = "annas"
    identifiers = (
        {
            "id": str(book.get("id", "")),
            "hash": book.get("hash") or book.get("book_hash"),
        }
        if source == "zlibrary"
        else {"md5": str(book.get("md5") or "").lower()}
    )
    if not all(identifiers.values()):
        raise AcquisitionError(
            "invalid_argument", "Selection has no usable source identity"
        )
    return source, identifiers


def _hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(path):
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _atomic_json(path, record):
    descriptor, temporary = tempfile.mkstemp(prefix=".receipt-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as stream:
            json.dump(record, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        # Persist the directory entry as well as the receipt bytes on POSIX.
        if os.name == "posix":
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _remove_stale(lock, budget):
    """Never steal an active local holder merely because a call was slow."""
    try:
        with lock.open("r+") as existing:
            if fcntl:
                try:
                    fcntl.flock(existing, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    return
            try:
                record = json.load(existing)
            except ValueError:
                record = {}
            st = os.fstat(existing.fileno())
            stale = (
                not _alive(record.get("pid"))
                if record.get("pid")
                else time.time() - st.st_mtime > budget
            )
            if stale and lock.stat().st_ino == st.st_ino:
                lock.unlink()
    except FileNotFoundError:
        pass


@asynccontextmanager
async def destination_lock(path, budget):
    lock = Path(str(path) + ".lock")
    deadline = time.monotonic() + budget
    descriptor = None
    while descriptor is None:
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        except FileExistsError:
            _remove_stale(lock, budget)
            if time.monotonic() >= deadline:
                raise AcquisitionError(
                    "breaker_open",
                    "Destination is still being acquired; retry after the active call completes",
                )
            await asyncio.sleep(0.05)
        except OSError as error:
            # Fail closed instead of advertising an idempotence promise this filesystem cannot provide.
            raise AcquisitionError(
                "output_refused", "Cannot create the destination acquisition lock"
            ) from error
    try:
        if fcntl:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
        os.write(descriptor, json.dumps({"pid": os.getpid(), "time": _now()}).encode())
        os.fsync(descriptor)
        yield
    finally:
        try:
            if lock.stat().st_ino == os.fstat(descriptor).st_ino:
                lock.unlink()
        except FileNotFoundError:
            pass
        os.close(descriptor)


def _record(book, source, identifiers, destination, request):
    return {
        "record_version": 1,
        "state": "intent",
        "path": str(destination),
        "bytes": None,
        "sha256": None,
        "md5": book.get("md5"),
        "reused": False,
        "transfer_skipped": False,
        "downloaded_at": _now(),
        "source": source,
        "provenance": {"route": source, "mirror": None, "host": None},
        **{
            field: book.get(field) or None
            for field in [
                "title",
                "author",
                "year",
                "language",
                "publisher",
                "pages",
                "isbn",
                "series",
                "edition",
                "translator",
            ]
        },
        "format": book.get("extension") or None,
        "identifiers": identifiers,
        "request": {
            field: request.get(field)
            for field in ["ref", "query", "item_id", "why_chosen"]
        },
    }


def _reply(record, record_path, skipped):
    return {
        "path": record["path"],
        "bytes": record["bytes"],
        "reused": False if skipped else record["reused"],
        "transfer_skipped": skipped,
        "verified": "sha256",
        "record": str(record_path),
    }


async def acquire(
    book_details, output_dir=None, filename=None, request=None, *, transfer
):
    """Check current bytes under a cross-process lock before any provider call."""
    book = dict(book_details)
    directory = output_directory(output_dir)
    name = destination_name(book, filename)
    source, identifiers = _identity(book)
    destination = directory / name
    if destination.is_symlink() or destination.resolve().parent != directory:
        raise AcquisitionError(
            "output_refused", "Destination must remain inside the output directory"
        )
    directory.mkdir(parents=True, exist_ok=True)
    receipt_path = Path(str(destination) + ".acq.json")
    budget = max(
        1.0, float(os.environ.get("PYTHON_BRIDGE_LONG_TIMEOUT", "600000")) / 1000
    )
    async with destination_lock(destination, budget):
        previous = _read(receipt_path)
        path = Path(previous.get("path") or destination)
        if (
            previous.get("record_version") == 1
            and previous.get("state") in {"complete", "intent"}
            and previous.get("source") == source
            and previous.get("identifiers") == identifiers
            and path.resolve().parent == directory
            and not path.is_symlink()
            and previous.get("sha256")
            and path.is_file()
        ):
            actual = _hash(path)
            if actual == previous["sha256"] and path.stat().st_size == previous.get(
                "bytes"
            ):
                # An intent with a checkpointed hash can recover publication before finalization.
                previous.update(state="complete", transfer_skipped=True, reused=False)
                record_path = Path(str(path) + ".acq.json")
                _atomic_json(receipt_path, previous)
                if record_path != receipt_path:
                    _atomic_json(record_path, previous)
                return _reply(previous, record_path, True)
        record = _record(book, source, identifiers, destination, request or {})
        _atomic_json(
            receipt_path, record
        )  # precedes authentication and every upstream request

        def checkpoint(stage, target):
            if target.is_symlink() or target.resolve().parent != directory:
                raise AcquisitionError(
                    "output_refused",
                    "Published destination must remain inside the output directory",
                    issued=True,
                )
            record.update(
                path=str(target), bytes=stage.stat().st_size, sha256=_hash(stage)
            )
            _atomic_json(
                receipt_path, record
            )  # still intent; crash after publication is recoverable

        result = await transfer(
            book, str(directory), filename=filename, publication_hook=checkpoint
        )
        final = Path(result["file_path"]).resolve()
        if final.parent != directory or not final.is_file():
            raise AcquisitionError(
                "internal",
                "Transfer did not publish inside the destination",
                issued=True,
            )
        # The checkpoint is called by the publication code. A fallback hash supports legacy transfers.
        record.update(
            path=str(final),
            bytes=final.stat().st_size,
            sha256=_hash(final),
            state="complete",
            reused=bool(result.get("publication_reused", False)),
            provenance=result.get("provenance") or record["provenance"],
        )
        record_path = Path(str(final) + ".acq.json")
        _atomic_json(record_path, record)
        if record_path != receipt_path:
            _atomic_json(receipt_path, record)
        reply = _reply(record, record_path, False)
        if result.get("quota_estimate"):
            reply["quota_estimate"] = result["quota_estimate"]
        return reply
