"""Exercise each live login path offline so stale defaults cannot hide as walls."""

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import zlibrary.eapi


ROOT = Path(__file__).resolve().parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "entrypoint",
    [
        "fixture",
        "test_authentication_succeeds",
        "test_authentication_fails_with_invalid_credentials",
        "test_session_persistence",
    ],
)
async def test_live_login_uses_runtime_default_and_override(monkeypatch, entrypoint):
    live = load_module(
        "offline_real_zlibrary", ROOT / "integration/test_real_zlibrary.py"
    )
    fixtures = load_module("offline_live_conftest", ROOT / "integration/conftest.py")
    monkeypatch.setattr(live.asyncio, "sleep", AsyncMock())
    monkeypatch.setenv("ZLIBRARY_EMAIL", "offline@example.test")
    monkeypatch.setenv("ZLIBRARY_PASSWORD", "offline")

    for override, expected in [
        (None, zlibrary.eapi.DEFAULT_EAPI_DOMAINS[0]),
        ("library.example.test", "library.example.test"),
    ]:
        if override:
            monkeypatch.setenv("ZLIBRARY_EAPI_DOMAIN", override)
        else:
            monkeypatch.delenv("ZLIBRARY_EAPI_DOMAIN", raising=False)

        class OfflineClient:
            def __init__(self, domain):
                assert domain == expected

            async def login(self, email, password):
                return {"success": int(email != "invalid@example.com")}

            async def search(self, *args, **kwargs):
                return {"books": []}

            async def close(self):
                pass

        monkeypatch.setattr(zlibrary.eapi, "EAPIClient", OfflineClient)
        monkeypatch.setattr(fixtures, "EAPIClient", OfflineClient)
        if entrypoint == "fixture":
            generator = fixtures.zlib_client.__wrapped__()
            await anext(generator)
            with pytest.raises(StopAsyncIteration):
                await anext(generator)
        else:
            test = getattr(live.TestRealAuthentication(), entrypoint)
            if entrypoint == "test_authentication_fails_with_invalid_credentials":
                await test()
            else:
                await test({"email": "offline@example.test", "password": "offline"})
