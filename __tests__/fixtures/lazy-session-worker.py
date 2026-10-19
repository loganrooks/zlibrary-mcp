"""Offline real-pipe/lease child; never contacts a provider."""

import asyncio
import json
import os
from pathlib import Path
import signal
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from acquisition import AcquisitionError, DestinationLease, acquire
from eapi_session_protocol import SessionProtocolError, request_session

mode, directory = sys.argv[1:3]
for descriptor in (3,) if mode == "control" else (3, 4):
    os.set_inheritable(descriptor, False)
root = Path(directory)
root.mkdir(parents=True, exist_ok=True)
(root / "pid").write_text(str(os.getpid()))


async def main():
    if mode == "control":
        json.loads(sys.stdin.readline(8193))
        (root / "control-ready").write_text("yes")
        try:
            await asyncio.sleep(30)
        finally:
            (root / "control-cleaned").write_text("yes")
        return
    if mode == "early-update":
        os.write(3, b'{"remix_userkey":"early-private-canary"}\n')
        os.close(4)
        await asyncio.sleep(30)
        return
    if mode.startswith("request-"):
        payload = {
            "fragmented": b'{"v":1,"type":"session_needed"}\n',
            "duplicate": b'{"v":1,"type":"session_needed"}\n' * 2,
            "oversize": b"x" * 129,
            "malformed": b'{"private":"canary-not-public"}\n',
            "version": b'{"v":2,"type":"session_needed"}\n',
            "partial": b'{"v":1,"type":"session_needed"}',
        }[mode.removeprefix("request-")]
        for byte in payload:
            os.write(4, bytes([byte]))
            await asyncio.sleep(0.001)
        os.close(4)
        if mode.endswith("fragmented"):
            # This mode tests the parent's incremental request parser only.
            await asyncio.sleep(0.03)
            print("{}")
        else:
            await asyncio.sleep(30)
        return
    if mode == "reply":
        try:
            await request_session(timeout=0.3)
            print(json.dumps({"ok": True}))
        except SessionProtocolError as error:
            print(json.dumps({"error": str(error)}))
        return

    async def transfer(book, directory, *, filename, publication_hook):
        target = root / "synthetic.epub"
        assert (
            json.loads(Path(str(target) + ".acq.json").read_text())["state"] == "intent"
        )
        try:
            with DestinationLease(target, 0):
                raise AssertionError("lease was not held")
        except AcquisitionError as error:
            assert error.reason == "breaker_open"
        (root / "admitted").write_text("intent+lease")
        private = await request_session(timeout=10)
        with (root / "transfers").open("a") as stream:
            stream.write("1\n")
        (root / "granted").write_text("yes")
        if mode == "stall":
            await asyncio.sleep(30)
        update = {k: v for k, v in private.items() if k != "action"}
        update["validate_next"] = True
        if mode == "leaked-error":
            update["remix_userkey"] = "recovered-private-canary"
        payload = (json.dumps(update) + "\n").encode()
        for part in (payload[:7], payload[7:]):
            os.write(3, part)
            await asyncio.sleep(0.005)
        if mode == "leaked-error":
            print(private["remix_userkey"], update["remix_userkey"], file=sys.stderr)
            raise ValueError("Synthetic failure")
        if mode == "duplicate-update":
            os.write(3, payload)
        stage = root / "stage"
        stage.write_bytes(b"offline-synthetic-document")
        publication_hook(stage, target)
        os.replace(stage, target)
        return {"file_path": str(target)}

    result = await acquire(
        {
            "source": "zlibrary",
            "id": "1",
            "hash": "hash1",
            "title": "Synthetic",
            "extension": "epub",
        },
        str(root),
        "synthetic.epub",
        transfer=transfer,
    )
    print(json.dumps(result))


async def run():
    task = asyncio.current_task()
    if os.name == "posix":
        asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, task.cancel)
    try:
        await main()
    except asyncio.CancelledError:
        pass
    except Exception:
        print("Synthetic private worker failed", file=sys.stderr)
        sys.exit(1)


asyncio.run(run())
