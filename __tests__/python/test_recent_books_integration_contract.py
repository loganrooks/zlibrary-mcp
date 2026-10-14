"""Check the exact credential-gated live method offline, without importing it."""

import ast
from pathlib import Path

import httpx
import pytest

from zlibrary.eapi import EAPIClient


@pytest.mark.parametrize(
    "payload,accepted",
    [
        ({"success": 1, "books": []}, True),
        ({"success": 1, "books": [{"id": "1"}]}, True),
        ({"success": 1}, False),
        ({"success": 1, "books": None}, False),
        ({"success": 1, "books": [1]}, False),
        ({"success": 0, "books": []}, False),
        (["not-an-object"], False),
    ],
)
async def test_live_recent_method_uses_existing_client_and_checks_shape(
    monkeypatch, payload, accepted
):
    # No live module import, credential reads, fixture login or provider calls.
    monkeypatch.delenv("ZLIBRARY_EMAIL", raising=False)
    monkeypatch.delenv("ZLIBRARY_PASSWORD", raising=False)
    source = Path(__file__).parent / "integration" / "test_real_zlibrary.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    basic_search = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "TestRealBasicSearch"
    )
    method = next(
        node
        for node in basic_search.body
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name == "test_recent_books_contract"
    )
    namespace = {}
    exec(
        compile(ast.Module(body=[method], type_ignores=[]), str(source), "exec"),
        namespace,
    )
    requests = []

    def respond(request):
        requests.append((request.method, request.url.path))
        assert request.method == "GET"
        assert request.url.path == "/eapi/book/recently"
        return httpx.Response(200, json=payload)

    # Real EAPI method over a pre-existing client. Any login/new request path
    # fails the stub and the explicit request-count assertion, even on bad data.
    eapi = EAPIClient(
        "zlibrary.example", remix_userid="7", remix_userkey="offline-session"
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(respond), cookies=eapi._cookies
    ) as client:
        eapi._client = client
        if accepted:
            await namespace[method.name](None, eapi)
        else:
            with pytest.raises(AssertionError):
                await namespace[method.name](None, eapi)
    assert requests == [("GET", "/eapi/book/recently")]
