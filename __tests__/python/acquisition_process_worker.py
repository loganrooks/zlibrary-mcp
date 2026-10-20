"""Offline process oracle for acquisition leases and crash phases; never a provider."""

import asyncio
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))
from lib import acquisition as acq
from lib.python_bridge import _publish_or_reuse

PAYLOAD = b"%PDF-1.7\nidentical synthetic bytes"


def run(directory, options):
    root = Path(directory)
    if options.get("paused_creator"):
        original = acq.fcntl.flock
        creator = []

        def pause_before_flock(fd, mode):
            if not creator:
                creator.append(fd)
                (root / "created").touch()
                deadline = time.monotonic() + 7
                while not (root / "resume").exists():
                    if time.monotonic() > deadline:
                        raise RuntimeError("created-inode process barrier timeout")
                    time.sleep(0.01)
            return original(fd, mode)

        acq.fcntl.flock = pause_before_flock
        try:
            with acq.DestinationLease(root / "book.pdf", 600, issued=True):
                (root / "admitted").touch()
                outcome = {"status": "admitted"}
        except acq.AcquisitionError as error:
            outcome = {"status": "refused", **error.to_dict()}
        finally:
            acq.fcntl.flock = original
        try:
            os.fstat(creator[0])
            outcome["old_fd_closed"] = False
        except OSError:
            outcome["old_fd_closed"] = True
        return outcome
    if options.get("lease_only"):

        async def hold():
            async with acq.destination_lock(root / "held.pdf", 0):
                (root / "held").touch()
                await asyncio.sleep(30)

        asyncio.run(hold())
        return {"status": "released"}
    identity = options.get("id", "1")
    initial = options.get("initial", "chosen.epub")
    target = root / options.get("target", "chosen.pdf")
    phase = options.get("phase")
    atomic = acq._atomic_json

    def write(path, record):
        atomic(path, record)
        canonical = path == Path(str(target) + ".acq.json")
        if record.get("sha256"):
            point = (
                ("canonical_intent" if canonical else "alias_intent")
                if record["state"] == "intent"
                else ("canonical_complete" if canonical else "alias_complete")
            )
            if phase == point:
                os._exit(23)

    acq._atomic_json = write

    async def transfer(book, directory, *, filename, publication_hook):
        with (root / "transfers").open("a") as log:
            log.write(identity + "\n")
        stage = root / f".stage-{os.getpid()}"
        stage.write_bytes(PAYLOAD)
        try:
            if options.get("barrier"):
                (root / f"ready-{identity}").touch()
                deadline = time.monotonic() + 5
                while not (root / "go").exists():
                    if time.monotonic() > deadline:
                        raise RuntimeError("pre-checkpoint barrier timeout")
                    await asyncio.sleep(0.01)
            else:
                await asyncio.sleep(0.15)
            publication_hook(stage, target)
            await asyncio.sleep(options.get("after_checkpoint_delay", 0))
            reused = _publish_or_reuse(stage, target)
            if phase == "published":
                os._exit(23)
            return {
                "file_path": str(target),
                "publication_reused": reused,
                "provenance": {
                    "route": "synthetic",
                    "mirror": "original",
                    "host": None,
                },
            }
        finally:
            stage.unlink(missing_ok=True)

    book = {
        "id": identity,
        "hash": "hash" + identity,
        "title": "Chosen",
        "author": "Fixture",
        "extension": Path(initial).suffix.lstrip("."),
    }
    try:
        reply = asyncio.run(
            acq.acquire(book, str(root), filename=initial, transfer=transfer)
        )
        return {"status": "ok", "id": identity, "reply": reply}
    except acq.AcquisitionError as error:
        return {"status": "refused", "id": identity, **error.to_dict()}


if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1], json.loads(sys.argv[2]))))
