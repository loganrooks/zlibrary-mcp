"""Bounded private lazy-v1 handoff; no authentication or provider work here."""

import asyncio
import json
import os

MAX_FRAME = 8192


class SessionProtocolError(ValueError):
    pass


def parse_session_frame(data):
    """Reject unknown framing without retaining or echoing private bytes."""
    try:
        if not data or len(data) > MAX_FRAME or not data.endswith(b"\n"):
            raise ValueError()
        frame = json.loads(data.decode("utf-8"))
        if (
            type(frame) is not dict
            or frame.get("v") != 1
            or type(frame.get("v")) is not int
        ):
            raise ValueError()
        if frame == {"v": 1, "type": "denied", "code": "auth_unavailable"}:
            raise SessionProtocolError("Private session request denied")
        if set(frame) != {"v", "type", "input"} or frame["type"] != "session":
            raise ValueError()
        value = frame["input"]
        if type(value) is not dict or set(value) - {
            "identity",
            "generation",
            "action",
            "authRetry",
            "domain",
            "remix_userid",
            "remix_userkey",
        }:
            raise ValueError()
        if (
            value.get("action") != "operation"
            or type(value.get("generation")) is not int
            or value["generation"] < 0
            or not all(
                type(value.get(k)) is str and value[k]
                for k in ("identity", "domain", "remix_userid", "remix_userkey")
            )
            or ("authRetry" in value and type(value["authRetry"]) is not bool)
        ):
            raise ValueError()
        return value
    except SessionProtocolError:
        raise
    except (ValueError, TypeError, KeyError):
        raise SessionProtocolError("Invalid private session reply") from None


class _SessionReader(asyncio.StreamReaderProtocol):
    def __init__(self, reader, closed):
        super().__init__(reader)
        self.closed = closed

    def connection_lost(self, error):
        try:
            super().connection_lost(error)
        finally:
            if not self.closed.done():
                self.closed.set_result(None)


async def request_session(*, timeout=240, input_fd=0, request_fd=4):
    """Demand once, then asynchronously read one bounded frame plus EOF.

    Node supplies overlapped stdin on Windows for ProactorEventLoop (Python3.10+);
    SelectorEventLoop manages a nonblocking pipe on POSIX. No reader thread.
    """
    transport = None
    pipe = None
    try:
        request = b'{"v":1,"type":"session_needed"}\n'
        try:
            if os.write(request_fd, request) != len(request):
                raise OSError()
        finally:
            os.close(request_fd)
        loop = asyncio.get_running_loop()
        closed = loop.create_future()
        reader = asyncio.StreamReader(limit=MAX_FRAME + 1)
        pipe = os.fdopen(os.dup(input_fd), "rb", buffering=0)
        try:
            transport, _ = await loop.connect_read_pipe(
                lambda: _SessionReader(reader, closed), pipe
            )
        except (OSError, NotImplementedError, ValueError):
            raise SessionProtocolError(
                "Asynchronous private session pipe unavailable"
            ) from None

        async def receive():
            data = bytearray()
            while True:
                chunk = await reader.read(min(4096, MAX_FRAME + 1 - len(data)))
                if not chunk:
                    return parse_session_frame(bytes(data))
                data.extend(chunk)
                if len(data) > MAX_FRAME:
                    raise SessionProtocolError("Invalid private session reply")

        try:
            return await asyncio.wait_for(receive(), timeout)
        except asyncio.TimeoutError:
            raise SessionProtocolError(
                "Private session reply deadline exceeded"
            ) from None
    except OSError:
        raise SessionProtocolError("Private session parent unavailable") from None
    finally:
        if transport is not None:
            transport.close()
            await asyncio.wait_for(asyncio.shield(closed), 1)
        elif pipe is not None:
            pipe.close()
