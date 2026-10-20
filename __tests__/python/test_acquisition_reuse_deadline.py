"""A candidate's collision comparison precedes commit, even for identical bytes."""

import hashlib
from pathlib import Path

import pytest

from lib import acquisition as acq
from lib import python_bridge as bridge
from lib.sources.net import WalkDeadline

PAYLOAD = b"%PDF-1.7\n" + b"x" * (2 * 65536)
BOOK = {"source": "libgen", "md5": hashlib.md5(PAYLOAD).hexdigest(), "extension": "pdf"}
CASES = [(True, 1, 1), (False, 1, 1), (False, 2, 1), (True, 1, 3)]


@pytest.mark.asyncio
@pytest.mark.parametrize("catalog_md5,expire_hash,expire_chunk", CASES)
@pytest.mark.parametrize("expire", [True, False])
async def test_existing_matching_destination_comparison_uses_remaining_budget(
    tmp_path, monkeypatch, catalog_md5, expire_hash, expire_chunk, expire
):
    """Catch missing checks in either comparison pass, including after its last chunk."""
    now = [0.0]
    monkeypatch.setattr(
        acq, "WalkDeadline", lambda budget: WalkDeadline(budget, clock=lambda: now[0])
    )
    original_digest = bridge._md5_digest
    hashes = []
    target, stage = tmp_path / "chosen.pdf", tmp_path / ".source-collision.pdf"
    scope = []
    inode = []

    class TimedDigest:
        def __init__(self):
            self.digest = original_digest()
            self.chunks = 0
            hashes.append(self)
            self.ordinal = len(hashes)

        def update(self, data):
            self.digest.update(data)
            self.chunks += 1
            if expire and self.ordinal == expire_hash and self.chunks == expire_chunk:
                now[0] += 10000.0

        def hexdigest(self):
            return self.digest.hexdigest()

    monkeypatch.setattr(bridge, "_md5_digest", TimedDigest)

    async def transfer(book, directory, *, filename, publication_hook):
        stage.write_bytes(PAYLOAD)
        publication_hook(stage, target)
        # Model an identical competing file appearing after our checkpoint.
        target.write_bytes(PAYLOAD)
        inode.append(target.stat().st_ino)
        scope.append(acq._acquisition_scope.get())
        reused = bridge._publish_or_reuse(
            stage, target, BOOK["md5"] if catalog_md5 else ""
        )
        return {"file_path": str(target), "publication_reused": reused}

    if expire:
        with pytest.raises(acq.AcquisitionError) as error:
            await acq.acquire(
                BOOK, str(tmp_path), filename="chosen.pdf", transfer=transfer
            )
        assert error.value.to_dict() == {
            "reason": "walk_budget_exhausted",
            "request_issued": True,
        }
        assert scope[0]["published"] is False
        assert hashes[expire_hash - 1].chunks == expire_chunk
    else:
        reply = await acq.acquire(
            BOOK, str(tmp_path), filename="chosen.pdf", transfer=transfer
        )
        assert reply["reused"] is True
        assert Path(reply["path"]) == target
        assert scope[0]["published"] is True

    assert target.read_bytes() == PAYLOAD
    assert target.stat().st_ino == inode[0]
    assert not stage.exists()
    async with acq.destination_lock(target, 0):
        pass
