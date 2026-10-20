"""Expose a synthetic acquisition's actual deadline/watchdog through the API bridge."""

import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lib import acquisition as acq
from lib.sources.net import WalkDeadline


async def main():
    assert sys.argv[1] == "acquire_book"
    args = json.loads(sys.argv[2])
    observed = {}
    # Stable accounting values, while retaining the real asyncio watchdog.
    acq.WalkDeadline = lambda budget: WalkDeadline(budget, clock=lambda: 0.0)
    wait_for = asyncio.wait_for

    async def observe_wait(task, timeout):
        observed["transfer_slice"] = timeout
        return await wait_for(task, timeout)

    asyncio.wait_for = observe_wait

    async def transfer(book, directory, *, filename, publication_hook):
        observed["budget"] = acq._acquisition_scope.get()["deadline"].budget
        stage, target = Path(directory) / ".stage", Path(directory) / filename
        stage.write_bytes(b"synthetic book")
        publication_hook(stage, target)
        stage.rename(target)
        return {"file_path": str(target)}

    await acq.acquire(**args, transfer=transfer)
    print(json.dumps({"content": [{"type": "text", "text": json.dumps(observed)}]}))


asyncio.run(main())
