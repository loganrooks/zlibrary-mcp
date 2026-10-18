"""Single-account session contract against real EAPI JSON decoding, offline only.

Breaks caught: unconditional login, wrong-account reuse, refresh on uncertainty,
blind failure-envelope acceptance, missing lock/re-read, non-private/torn writes.
"""

import asyncio
import json
import os
from pathlib import Path
import sys

import httpx
import pytest

import python_bridge
from zlibrary import eapi


@pytest.fixture
def service(monkeypatch, tmp_path):
    monkeypatch.setenv("ZLIBRARY_SESSION_CACHE", "on")
    monkeypatch.setenv("ZLIBRARY_SESSION_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("ZLIBRARY_EMAIL", "reader@example.test")
    monkeypatch.setenv("ZLIBRARY_PASSWORD", "fake-password-marker")
    monkeypatch.setenv("ZLIBRARY_EAPI_DOMAIN", "a.example.test")
    monkeypatch.setattr(
        eapi, "DEFAULT_EAPI_DOMAINS", ["a.example.test", "b.example.test"]
    )
    monkeypatch.setattr(python_bridge, "_eapi_client", None)
    state = {
        "logins": 0,
        "requests": [],
        "profile": None,
        "operation": None,
        "failures": {},
        "clients": [],
        "login_result": None,
    }

    def handle(request):
        host, path = request.url.host, request.url.path
        state["requests"].append((host, path, request.headers.get("cookie", "")))
        failure = state["failures"].get(host)
        if failure == "network":
            raise httpx.ConnectError("offline", request=request)
        if failure == "timeout":
            raise httpx.ReadTimeout("offline", request=request)
        if failure == "wall":
            return httpx.Response(513, text="DiamWall")
        if failure == "http":
            return httpx.Response(503, text="unavailable")
        if path == "/eapi/user/login":
            state["logins"] += 1
            return httpx.Response(
                200,
                json=state["login_result"]
                or {
                    "success": 1,
                    "user": {
                        "id": str(state["logins"]),
                        "remix_userkey": f"fake-cookie-marker-{state['logins']}",
                    },
                },
            )
        if path == "/eapi/info/domains":
            return httpx.Response(200, json={"domains": []})
        payload = (
            state["profile"] if path == "/eapi/user/profile" else state["operation"]
        )
        if callable(payload):
            payload = payload(request)
        if isinstance(payload, Exception):
            raise payload
        if isinstance(payload, httpx.Response):
            return payload
        if payload is None:
            if path == "/eapi/user/profile":
                # Independent server view of the authenticated identity.
                payload = {"success": 1, "user": {"id": str(state["logins"])}}
            else:
                payload = {"success": 1, "books": []}
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handle)

    async def get_client(self):
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(transport=transport, cookies=self._cookies)
            state["clients"].append(self._client)
        return self._client

    async def resolve():
        return await eapi.resolve_eapi_domain(transport=transport)

    monkeypatch.setattr(eapi.EAPIClient, "_get_client", get_client)
    monkeypatch.setattr(python_bridge, "resolve_eapi_domain", resolve)
    state["root"] = tmp_path / "state"
    return state


async def initialize_and_close():
    client = await python_bridge.initialize_eapi_client()
    await client.close()
    python_bridge._eapi_client = None
    return client


def record(service):
    return next(service["root"].glob("*.json"))


async def test_sequential_calls_reuse_cookies(service):
    await initialize_and_close()
    await initialize_and_close()
    assert service["logins"] == 1
    profiles = [r for r in service["requests"] if r[1] == "/eapi/user/profile"]
    assert len(profiles) == 1
    assert "remix_userkey=fake-cookie-marker-1" in profiles[0][2]


async def test_identity_change_never_sends_previous_cookies(service, monkeypatch):
    await initialize_and_close()
    service["requests"].clear()
    monkeypatch.setenv("ZLIBRARY_EMAIL", "other@example.test")
    await initialize_and_close()
    assert service["logins"] == 2
    assert all(
        "fake-cookie-marker-1" not in cookies for _, _, cookies in service["requests"]
    )


async def test_password_change_is_password_free_and_manual_removal_refreshes(
    service, monkeypatch
):
    await initialize_and_close()
    original = record(service).read_bytes()
    monkeypatch.setenv("ZLIBRARY_PASSWORD", "replacement-fake-password")
    await initialize_and_close()
    assert service["logins"] == 1
    assert record(service).read_bytes() == original
    record(service).unlink()
    await initialize_and_close()
    assert service["logins"] == 2


async def test_private_atomic_record_allowlist(service, monkeypatch):
    import hashlib

    await initialize_and_close()
    path = record(service)
    data = json.loads(path.read_text())
    assert set(data) == {
        "identity",
        "domain",
        "remix_userid",
        "remix_userkey",
        "created_at",
    }
    assert data["identity"] == "reader@example.test"
    assert isinstance(data["created_at"], (int, float))
    assert service["root"].stat().st_mode & 0o777 == 0o700
    assert path.stat().st_mode & 0o777 == 0o600
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in service["root"].iterdir())
    assert "fake-password-marker" not in path.read_text()
    assert hashlib.sha256(b"fake-password-marker").hexdigest() not in path.read_text()

    # Interrupted replace must leave the complete previous record, no partial file.
    from lib import eapi_session

    original = path.read_bytes()
    monkeypatch.setattr(
        eapi_session.os,
        "replace",
        lambda *_: (_ for _ in ()).throw(OSError("fake replace failure")),
    )
    with pytest.raises(OSError):
        eapi_session._write(path, {**data, "remix_userkey": "replacement"})
    assert path.read_bytes() == original
    assert sorted(p.name for p in service["root"].iterdir()) == [
        "eapi-session.json",
        "eapi-session.lock",
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {"success": 0, "error": "Please login"},
        {"success": 0, "error": "Please login", "user": {"id": "1"}},
        httpx.Response(401, json={"error": "rejected"}),
        httpx.Response(400, json={"success": 0, "error": "Please login"}),
    ],
)
async def test_explicit_profile_rejection_refreshes_once(service, payload):
    await initialize_and_close()
    service["profile"] = payload
    await initialize_and_close()
    assert service["logins"] == 2
    assert (
        json.loads(record(service).read_text())["remix_userkey"]
        == "fake-cookie-marker-2"
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"success": 0, "user": {"id": "1"}},
        {"success": 0, "error": "maintenance", "user": {"id": "1"}},
        {"success": 1, "user": {"id": "different"}},
        {},
        [],
    ],
)
async def test_ambiguous_profile_never_logs_in_or_changes_cache(service, payload):
    await initialize_and_close()
    original = record(service).read_bytes()
    service["profile"] = payload
    with pytest.raises(RuntimeError):
        await initialize_and_close()
    assert service["logins"] == 1
    assert record(service).read_bytes() == original
    assert all(c.is_closed for c in service["clients"])


@pytest.mark.parametrize("failure", ["network", "timeout", "wall", "http"])
async def test_pinned_transport_failure_preserves_cache(service, failure):
    await initialize_and_close()
    original = record(service).read_bytes()
    service["failures"]["a.example.test"] = failure
    with pytest.raises((httpx.HTTPError, eapi.DiamWallError)):
        await initialize_and_close()
    assert service["logins"] == 1
    assert record(service).read_bytes() == original
    assert all(host == "a.example.test" for host, _, _ in service["requests"])


@pytest.mark.parametrize("failure", ["network", "timeout", "wall", "http"])
async def test_domain_recovery_uses_same_cookies_without_login(
    service, monkeypatch, failure
):
    monkeypatch.delenv("ZLIBRARY_EAPI_DOMAIN")
    await initialize_and_close()
    service["failures"]["a.example.test"] = failure
    client = await initialize_and_close()
    assert client.domain == "b.example.test"
    assert service["logins"] == 1
    data = json.loads(record(service).read_text())
    assert data["domain"] == "b.example.test"
    assert data["remix_userkey"] == "fake-cookie-marker-1"
    assert all(c.is_closed for c in service["clients"])


async def test_failed_domain_recovery_keeps_cache(service, monkeypatch):
    monkeypatch.delenv("ZLIBRARY_EAPI_DOMAIN")
    await initialize_and_close()
    original = record(service).read_bytes()
    service["failures"] = {"a.example.test": "network", "b.example.test": "wall"}
    with pytest.raises(httpx.ConnectError):
        await initialize_and_close()
    assert service["logins"] == 1
    assert record(service).read_bytes() == original


async def test_changed_pin_is_honored_without_login(service, monkeypatch):
    await initialize_and_close()
    monkeypatch.setenv("ZLIBRARY_EAPI_DOMAIN", "b.example.test")
    service["requests"].clear()
    await initialize_and_close()
    assert service["logins"] == 1
    assert {r[0] for r in service["requests"]} == {"b.example.test"}


async def test_rejection_during_operation_refreshes_and_retries_only_once(service):
    await initialize_and_close()
    client = await python_bridge.initialize_eapi_client()
    service["requests"].clear()
    service["operation"] = {"success": 0, "error": "Please login"}
    with pytest.raises(RuntimeError):
        await client.search("offline")
    await client.close()
    assert service["logins"] == 2
    assert len([r for r in service["requests"] if r[1] == "/eapi/book/search"]) == 2


async def test_operation_refresh_reuses_another_process_new_session(service):
    await initialize_and_close()
    stale = await python_bridge.initialize_eapi_client()
    record(service).unlink()
    await initialize_and_close()  # emulate another bridge replacing the session
    service["operation"] = lambda request: (
        {"success": 0, "error": "Please login"}
        if "fake-cookie-marker-1" in request.headers.get("cookie", "")
        else {"success": 1, "books": [{"id": "offline-result"}]}
    )
    result = await stale.search("offline")
    await stale.close()
    assert result["books"] == [{"id": "offline-result"}]
    assert service["logins"] == 2


async def test_off_switch_does_not_create_state(service, monkeypatch):
    monkeypatch.setenv("ZLIBRARY_SESSION_CACHE", "off")
    await initialize_and_close()
    await initialize_and_close()
    assert service["logins"] == 2
    assert not service["root"].exists()


async def test_login_failure_never_leaks_response_or_credentials(service, caplog):
    service["login_result"] = {
        "success": 0,
        "user": {"remix_userkey": "fake-cookie-marker"},
        "error": "fake-password-marker reader@example.test",
    }
    with pytest.raises(RuntimeError) as caught:
        await initialize_and_close()
    diagnostic = str(caught.value) + caplog.text
    for value in ("fake-cookie-marker", "fake-password-marker", "reader@example.test"):
        assert value not in diagnostic
    assert not list(service["root"].glob("*.json"))
    assert all(c.is_closed for c in service["clients"])


async def test_concurrent_cold_processes_login_once(service, tmp_path):
    """Falsifier: removing lock or locked re-read causes two login counter lines.

    Both children reach initialize together; the fake login waits for the other
    login for one second. Correct serialization lets only one reach it; unlocked
    code deterministically overlaps, not merely when the scheduler gets lucky.
    """
    script = r"""
import asyncio, os, sys, time
from pathlib import Path
import httpx
sys.path.insert(0, "lib")
import python_bridge
from zlibrary.eapi import EAPIClient
root = Path(os.environ["TEST_BARRIER"])
async def handle(request):
    if request.url.path == "/eapi/user/login":
        with (root / "login-count").open("a") as out:
            out.write("login\n")
        deadline = time.monotonic() + 1
        while len((root / "login-count").read_text().splitlines()) < 2 and time.monotonic() < deadline:
            await asyncio.sleep(.02)
        return httpx.Response(200, json={"success":1,"user":{"id":"1","remix_userkey":"offline-cookie"}})
    assert request.url.path == "/eapi/user/profile"
    assert "remix_userkey=offline-cookie" in request.headers["cookie"]
    return httpx.Response(200, json={"success":1,"user":{"id":"1"}})
async def get_client(self):
    if self._client is None or self._client.is_closed:
        self._client = httpx.AsyncClient(transport=httpx.MockTransport(handle), cookies=self._cookies)
    return self._client
EAPIClient._get_client = get_client
async def run():
    (root / ("ready-" + str(os.getpid()))).touch()
    deadline = time.monotonic() + 10
    while len(list(root.glob("ready-*"))) < 2:
        if time.monotonic() > deadline:
            raise TimeoutError("test barrier")
        await asyncio.sleep(.02)
    client = await python_bridge.initialize_eapi_client()
    await client.close()
asyncio.run(run())
"""

    async def child():
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            script,
            cwd=Path(__file__).resolve().parents[2],
            env={**os.environ, "TEST_BARRIER": str(tmp_path)},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), 20)
        finally:
            if proc.returncode is None:
                proc.kill()
                await proc.wait()
        assert proc.returncode == 0, stderr.decode()
        assert stdout == b""

    await asyncio.gather(child(), child())
    assert (tmp_path / "login-count").read_text().splitlines() == ["login"]


@pytest.mark.parametrize(
    "kind", ["directory", "symlink", "public-file", "symlink-file"]
)
async def test_nonprivate_state_rejected_before_login(service, tmp_path, kind):
    root = service["root"]
    if kind == "directory":
        root.mkdir(mode=0o755)
        root.chmod(0o755)
    elif kind == "symlink":
        target = tmp_path / "target"
        target.mkdir(mode=0o700)
        root.symlink_to(target, target_is_directory=True)
    else:
        root.mkdir(mode=0o700)
        path = root / "eapi-session.json"
        if kind == "public-file":
            path.write_text("{}")
            path.chmod(0o644)
        else:
            target = tmp_path / "target.json"
            target.write_text("{}")
            target.chmod(0o600)
            path.symlink_to(target)
    with pytest.raises((RuntimeError, OSError)):
        await initialize_and_close()
    assert service["logins"] == 0


async def test_cancelled_lock_releases_for_next_caller(service):
    from lib.eapi_session import _locked, _private_directory

    path = _private_directory() / "eapi-session.lock"
    entered = asyncio.Event()

    async def hold():
        async with _locked(path):
            entered.set()
            await asyncio.Event().wait()

    task = asyncio.create_task(hold())
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.wait_for(initialize_and_close(), 2)
    assert service["logins"] == 1


@pytest.mark.parametrize("failure", ["network", "wall", "http"])
async def test_recovered_domain_validation_failure_preserves_bytes(
    service, monkeypatch, failure
):
    monkeypatch.delenv("ZLIBRARY_EAPI_DOMAIN")
    await initialize_and_close()
    original = record(service).read_bytes()
    service["failures"]["a.example.test"] = "network"

    def bad_profile(request):
        if failure == "network":
            return httpx.ConnectError("offline", request=request)
        return httpx.Response(513 if failure == "wall" else 503, text="unavailable")

    service["profile"] = bad_profile
    with pytest.raises((httpx.HTTPError, eapi.DiamWallError)):
        await initialize_and_close()
    assert record(service).read_bytes() == original
    assert service["logins"] == 1
    assert all(c.is_closed for c in service["clients"])


async def test_successful_operation_retry_returns_new_result(service):
    await initialize_and_close()
    client = await python_bridge.initialize_eapi_client()
    service["operation"] = lambda request: (
        {"success": 0, "error": "Please login"}
        if "fake-cookie-marker-1" in request.headers.get("cookie", "")
        else {"success": 1, "books": [{"id": "new-session-result"}]}
    )
    assert (await client.search("offline"))["books"] == [{"id": "new-session-result"}]
    await client.close()
    assert service["logins"] == 2


async def test_operation_transport_uncertainty_never_refreshes(service):
    await initialize_and_close()
    client = await python_bridge.initialize_eapi_client()
    original = record(service).read_bytes()
    service["operation"] = httpx.ReadTimeout("offline")
    with pytest.raises(httpx.ReadTimeout):
        await client.search("offline")
    await client.close()
    assert record(service).read_bytes() == original
    assert service["logins"] == 1


async def test_xdg_default_and_corrupt_cache_recovery(service, monkeypatch, tmp_path):
    monkeypatch.delenv("ZLIBRARY_SESSION_DIR")
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg"))
    service["root"] = tmp_path / "xdg" / "zlibrary-mcp"
    await initialize_and_close()
    path = record(service)
    path.write_text("not-json")
    await initialize_and_close()
    assert service["logins"] == 2
    assert json.loads(path.read_text())["identity"] == "reader@example.test"


async def test_wall_marker_on_401_is_not_auth_rejection(service):
    """An upstream wall's status must not become a fresh login."""
    await initialize_and_close()
    original = record(service).read_bytes()
    service["profile"] = httpx.Response(401, text="<html>DiamWall challenge</html>")
    with pytest.raises(eapi.DiamWallError):
        await initialize_and_close()
    assert service["logins"] == 1
    assert record(service).read_bytes() == original


async def test_ambiguous_operation_envelope_fails_without_refresh_or_secret_leak(
    service, caplog
):
    await initialize_and_close()
    client = await python_bridge.initialize_eapi_client()
    original = record(service).read_bytes()
    service["operation"] = {
        "success": 0,
        "error": "fake-cookie-marker-1 fake-password-marker",
    }
    with pytest.raises(RuntimeError) as caught:
        await client.search("offline")
    await client.close()
    assert service["logins"] == 1
    assert record(service).read_bytes() == original
    assert "fake-cookie-marker" not in str(caught.value) + caplog.text
    assert "fake-password-marker" not in str(caught.value) + caplog.text
