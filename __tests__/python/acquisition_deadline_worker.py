"""Synthetic acquisition under the real Node bridge timer; no provider I/O."""

import asyncio
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lib import acquisition as acq


async def main():
    with tempfile.TemporaryDirectory(prefix="deadline-worker-") as directory:
        target = Path(directory) / "chosen.pdf"
        issued = []
        lease = acq.DestinationLease(target, 4).__enter__()

        async def release():
            await asyncio.sleep(2.3 if sys.argv[1] == "late" else 0.4)
            lease.close()

        async def transfer(*args, **kwargs):
            issued.append(True)
            await asyncio.sleep(3.5)
            raise AssertionError("transfer outlived its remaining allowance")

        holder = asyncio.create_task(release())
        try:
            try:
                await acq.acquire(
                    {"source": "libgen", "md5": "a" * 32, "extension": "pdf"},
                    directory,
                    filename="chosen.pdf",
                    transfer=transfer,
                )
            except acq.AcquisitionError as error:
                print(json.dumps({**error.to_dict(), "transfers": len(issued)}))
        finally:
            await holder
            lease.close()


asyncio.run(main())
