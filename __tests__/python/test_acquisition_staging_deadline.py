"""Exercise real source streaming: a private staging link is not publication."""

import hashlib
import json
from pathlib import Path

import httpx
import pytest

from lib import acquisition as acq
from lib import python_bridge as bridge
from lib.sources.net import WalkDeadline

PAYLOAD = b"%PDF-1.7\n" + b"x" * 4096
MD5 = hashlib.md5(PAYLOAD).hexdigest()
BOOK = {"md5": MD5, "extension": "pdf", "title": "Fixture"}


@pytest.fixture
def mock_source_stream(monkeypatch):
    real = httpx.AsyncClient

    def handler(request):
        assert request.url.host == "mirror.invalid"
        return httpx.Response(
            200, content=PAYLOAD, headers={"content-type": "application/pdf"}
        )

    class Client(real):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", Client)


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["libgen", "annas"])
async def test_real_source_staging_does_not_commit_destination(
    tmp_path, monkeypatch, mock_source_stream, provider
):
    """Catch marking committed at the stager's .part -> response-extension link."""
    observed = []

    async def fetch(book, directory):
        path = await bridge._download_url_to_file(
            "https://mirror.invalid/book",
            directory,
            MD5,
            provider,
            enforce_timeout=False,
        )
        observed.append(
            (
                acq._acquisition_scope.get()["published"],
                (tmp_path / "chosen.pdf").exists(),
            )
        )
        return path

    monkeypatch.setattr(bridge, "_fetch_from_source", fetch)
    reply = await acq.acquire(
        {**BOOK, "source": provider},
        str(tmp_path),
        filename="chosen.pdf",
        transfer=bridge.download_book,
    )
    assert observed == [(False, False)]
    assert Path(reply["path"]).read_bytes() == PAYLOAD
    assert json.loads(Path(reply["record"]).read_text())["state"] == "complete"


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["libgen", "annas"])
async def test_spent_clock_after_real_stream_refuses_before_checkpoint(
    tmp_path, monkeypatch, mock_source_stream, provider
):
    """The real stream's staging rename must not disable the checkpoint deadline."""
    now = [0.0]
    monkeypatch.setattr(
        acq, "WalkDeadline", lambda budget: WalkDeadline(budget, clock=lambda: now[0])
    )

    async def fetch(book, directory):
        path = await bridge._download_url_to_file(
            "https://mirror.invalid/book",
            directory,
            MD5,
            provider,
            enforce_timeout=False,
        )
        now[0] += 10000.0
        return path

    monkeypatch.setattr(bridge, "_fetch_from_source", fetch)
    with pytest.raises(acq.AcquisitionError) as error:
        await acq.acquire(
            {**BOOK, "source": provider},
            str(tmp_path),
            filename="chosen.pdf",
            transfer=bridge.download_book,
        )
    assert error.value.to_dict() == {
        "reason": "walk_budget_exhausted",
        "request_issued": True,
    }
    assert not (tmp_path / "chosen.pdf").exists()
    intent = json.loads((tmp_path / "chosen.pdf.acq.json").read_text())
    assert intent["state"] == "intent" and intent["sha256"] is None
    assert not list(tmp_path.glob(".source-*"))
    async with acq.destination_lock(tmp_path / "chosen.pdf", 0):
        pass


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["libgen", "annas"])
async def test_real_stream_finishes_receipt_when_clock_expires_at_final_link(
    tmp_path, monkeypatch, mock_source_stream, provider
):
    """Control: the true commit point still ends cooperative refusal (round 1)."""
    now = [0.0]
    monkeypatch.setattr(
        acq, "WalkDeadline", lambda budget: WalkDeadline(budget, clock=lambda: now[0])
    )
    link = bridge.os.link
    target = tmp_path / "chosen.pdf"

    def expire_at_final(source, destination):
        link(source, destination)
        if Path(destination) == target:
            now[0] += 10000.0

    async def fetch(book, directory):
        return await bridge._download_url_to_file(
            "https://mirror.invalid/book",
            directory,
            MD5,
            provider,
            enforce_timeout=False,
        )

    monkeypatch.setattr(bridge.os, "link", expire_at_final)
    monkeypatch.setattr(bridge, "_fetch_from_source", fetch)
    reply = await acq.acquire(
        {**BOOK, "source": provider},
        str(tmp_path),
        filename="chosen.pdf",
        transfer=bridge.download_book,
    )
    record = json.loads(Path(reply["record"]).read_text())
    assert record["state"] == "complete"
    assert record["sha256"] == hashlib.sha256(PAYLOAD).hexdigest()

    async def forbidden(*args, **kwargs):
        pytest.fail("completed real-stream acquisition replayed a transfer")

    reused = await acq.acquire(
        {**BOOK, "source": provider},
        str(tmp_path),
        filename="chosen.pdf",
        transfer=forbidden,
    )
    assert reused["transfer_skipped"] is True
    assert reused["path"] == str(target)
