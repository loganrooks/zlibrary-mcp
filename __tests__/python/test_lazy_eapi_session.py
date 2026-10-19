"""Bounded lazy-v1 frame and deferred bridge initialization controls."""

import asyncio
import json

import httpx
import pytest
import python_bridge
from eapi_session_protocol import MAX_FRAME, SessionProtocolError, parse_session_frame

PRIVATE = {
    "identity": "synthetic@example.invalid",
    "generation": 0,
    "action": "operation",
    "domain": "synthetic.invalid",
    "remix_userid": "7",
    "remix_userkey": "private-canary",
}


def frame(value):
    return (json.dumps(value) + "\n").encode()


def test_exact_grant():
    assert (
        parse_session_frame(frame({"v": 1, "type": "session", "input": PRIVATE}))
        == PRIVATE
    )


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"{}",
        b"{}\n",
        b"\xff\n",
        b"x" * (MAX_FRAME + 1),
        frame({"v": 2, "type": "session", "input": PRIVATE}),
        frame({"v": True, "type": "session", "input": PRIVATE}),
        frame({"v": 1, "type": "session", "input": {**PRIVATE, "action": "login"}}),
        frame({"v": 1, "type": "session", "input": {**PRIVATE, "generation": True}}),
        frame(
            {"v": 1, "type": "session", "input": {**PRIVATE, "extra": "private-canary"}}
        ),
        frame({"v": 1, "type": "session", "input": PRIVATE}) * 2,
        frame({"v": 1, "type": "denied", "code": "auth_unavailable"}),
    ],
)
def test_invalid_or_denied_is_fixed_and_redacted(data):
    with pytest.raises(SessionProtocolError) as error:
        parse_session_frame(data)
    assert "private-canary" not in str(error.value)
    assert str(error.value) in {
        "Invalid private session reply",
        "Private session request denied",
    }


@pytest.mark.asyncio
async def test_lazy_grant_recovers_domain_and_publishes_exactly_once(monkeypatch):
    from lib import eapi_session_protocol

    monkeypatch.setenv("ZLIBRARY_EMAIL", PRIVATE["identity"])
    monkeypatch.setenv("ZLIBRARY_PASSWORD", "synthetic-password")
    monkeypatch.delenv("ZLIBRARY_EAPI_DOMAIN", raising=False)
    monkeypatch.setattr(python_bridge, "_lazy_session", True)
    monkeypatch.setattr(python_bridge, "_session_input", None)
    monkeypatch.setattr(python_bridge, "_eapi_client", None)
    monkeypatch.setattr(python_bridge, "_session_published", False)
    demands, requests, updates = [], [], []

    async def demand(**kwargs):
        demands.append(kwargs)
        await asyncio.sleep(0)
        return {**PRIVATE, "domain": "old.invalid"}

    monkeypatch.setattr(eapi_session_protocol, "request_session", demand)

    async def resolve():
        return "new.invalid"

    monkeypatch.setattr(python_bridge, "resolve_eapi_domain", resolve)

    def handler(request):
        requests.append((request.url.host, request.url.path))
        assert "/login" not in request.url.path
        if request.url.host == "old.invalid":
            raise httpx.ConnectError("synthetic offline", request=request)
        return httpx.Response(200, json={"success": 1, "user": {"id": 7}, "books": []})

    original = httpx.AsyncClient

    def client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client)
    monkeypatch.setattr(
        python_bridge.os,
        "write",
        lambda fd, data: updates.append((fd, json.loads(data))) or len(data),
    )
    try:
        client = await python_bridge.initialize_eapi_client()
        assert (await client.search("offline"))["books"] == []
        python_bridge._publish_eapi_session()
        python_bridge._publish_eapi_session()
        assert len(demands) == 1
        assert len(updates) == 1
        assert updates[0][0] == 3
        assert updates[0][1]["domain"] == "new.invalid"
        assert updates[0][1].get("validate_next", False) is False
        assert ("new.invalid", "/eapi/user/profile") in requests
    finally:
        if python_bridge._eapi_client:
            await python_bridge._eapi_client.close()
