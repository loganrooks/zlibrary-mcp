"""Single-account, process-shared EAPI cookies; never persist password material."""

import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import stat
import tempfile
import time

import httpx
from zlibrary.eapi import DiamWallError, EAPIAuthenticationError

if os.name == "nt":
    import msvcrt
else:
    import fcntl


def _private_directory():
    override = os.environ.get("ZLIBRARY_SESSION_DIR")
    state = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    root = Path(override).expanduser() if override else state / "zlibrary-mcp"
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or (
        os.name != "nt" and (info.st_uid != os.getuid() or info.st_mode & 0o077)
    ):
        raise RuntimeError(
            "EAPI session directory must be a private owned directory (0700), not a symlink"
        )
    return root


def _open_private(path, flags):
    fd = os.open(path, flags | getattr(os, "O_NOFOLLOW", 0), 0o600)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or (
        os.name != "nt" and (info.st_uid != os.getuid() or info.st_mode & 0o077)
    ):
        os.close(fd)
        raise RuntimeError(
            "EAPI session files must be private owned regular files (0600)"
        )
    return fd


@asynccontextmanager
async def _locked(path):
    """Nonblocking OS lock: waits are cancellable; OS releases it on process exit."""
    fd = _open_private(path, os.O_CREAT | os.O_RDWR)
    acquired = False
    try:
        if os.name == "nt" and os.fstat(fd).st_size == 0:
            os.write(fd, b"\0")
        deadline = time.monotonic() + 30
        while not acquired:
            try:
                if os.name == "nt":
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except (BlockingIOError, PermissionError):
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        "Timed out waiting for EAPI session lock"
                    ) from None
                await asyncio.sleep(0.05)
        yield
    finally:
        if acquired:
            if os.name == "nt":
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _read(path, identity):
    try:
        fd = _open_private(path, os.O_RDONLY)
    except FileNotFoundError:
        return None
    with os.fdopen(fd, encoding="utf-8") as handle:
        try:
            value = json.load(handle)
        except (ValueError, UnicodeError):
            return None
    if not isinstance(value, dict) or value.get("identity") != identity:
        return None
    if not all(
        isinstance(value.get(k), str) and value[k]
        for k in ("domain", "remix_userid", "remix_userkey")
    ):
        return None
    return value


def _write(path, value):
    fd, temporary = tempfile.mkstemp(prefix=".eapi-session-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


async def _validate(client):
    profile = await client.get_profile()
    # A populated user must never override an explicit failure flag.
    if (
        not isinstance(profile, dict)
        or profile.get("success") != 1
        or not isinstance(profile.get("user"), dict)
        or str(profile["user"].get("id", "")) != client.remix_userid
    ):
        raise RuntimeError("Unexpected EAPI profile response; cached session retained")


async def _restore(record, client_factory, resolve_domain):
    pin = os.environ.get("ZLIBRARY_EAPI_DOMAIN", "").strip()
    domain = pin or record["domain"]
    client = client_factory(
        domain,
        remix_userid=record["remix_userid"],
        remix_userkey=record["remix_userkey"],
    )
    try:
        try:
            await _validate(client)
        except (httpx.RequestError, httpx.HTTPStatusError, DiamWallError):
            # Never re-login on uncertainty. One unpinned recovery may try the
            # SAME cookies on a healthy domain; validation must succeed to save.
            if pin:
                raise
            target = await resolve_domain()
            if target == domain:
                raise
            await client.close()
            client = client_factory(
                target,
                remix_userid=record["remix_userid"],
                remix_userkey=record["remix_userkey"],
            )
            await _validate(client)
        return client
    except BaseException:
        await client.close()
        raise


async def authenticated_client(
    identity, login, client_factory, resolve_domain, rejected=None
):
    """Re-read under lock, validate shared cookies, or perform one cold login.

    `rejected` is the cookie pair explicitly rejected by an operation. A newer
    record written by another bridge is validated and reused instead of erased.
    The login closure owns the password; this module never receives it.
    """
    root = _private_directory()
    path = root / "eapi-session.json"
    async with _locked(root / "eapi-session.lock"):
        record = _read(path, identity)
        if record and rejected == (record["remix_userid"], record["remix_userkey"]):
            path.unlink(missing_ok=True)
            record = None
        if record:
            try:
                client = await _restore(record, client_factory, resolve_domain)
            except EAPIAuthenticationError:
                path.unlink(missing_ok=True)
            else:
                if client.domain != record["domain"]:
                    try:
                        _write(path, {**record, "domain": client.domain})
                    except BaseException:
                        await client.close()
                        raise
                return _attach_refresh(
                    client, identity, login, client_factory, resolve_domain
                )
        client = await login()
        try:
            if not client.remix_userid or not client.remix_userkey:
                raise RuntimeError("EAPI login returned no session cookies")
            _write(
                path,
                {
                    "identity": identity,
                    "domain": client.domain,
                    "remix_userid": str(client.remix_userid),
                    "remix_userkey": str(client.remix_userkey),
                    "created_at": time.time(),
                },
            )
        except BaseException:
            await client.close()
            raise
        return _attach_refresh(client, identity, login, client_factory, resolve_domain)


def _attach_refresh(client, identity, login, client_factory, resolve_domain):
    async def refresh():
        replacement = await authenticated_client(
            identity,
            login,
            client_factory,
            resolve_domain,
            rejected=(client.remix_userid, client.remix_userkey),
        )
        try:
            await client.close()
            client.domain = replacement.domain
            client.remix_userid = replacement.remix_userid
            client.remix_userkey = replacement.remix_userkey
        finally:
            await replacement.close()

    client.on_auth_rejected = refresh
    return client
