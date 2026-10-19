"""Bounded private lazy-v2 demand / v1 reply handoff; no authentication or provider work here."""

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


def _emit(diagnostic, phase, state, *, error=None, count=None, loop_kind=None):
    """Opt-in synthetic diagnostics: fixed enums/numbers, never exception text."""
    if diagnostic is None:
        return
    try:
        phases = {
            "request-write",
            "request-close",
            "input-duplicate",
            "input-handle",
            "loop",
            "input-connect",
            "input-read",
            "input-eof",
            "parse",
            "connection-lost",
            "transport-close",
            "primary",
            "cleanup",
        }
        states = {"start", "done", "error", "cancelled", "invalid", "denied", "timeout"}
        event = {
            "phase": phase if phase in phases else "unknown",
            "state": state if state in states else "unknown",
        }
        if error is not None:
            name = type(error).__name__
            event["error_type"] = (
                name
                if name
                in {
                    "OSError",
                    "PermissionError",
                    "BrokenPipeError",
                    "ConnectionResetError",
                    "ConnectionAbortedError",
                    "TimeoutError",
                    "CancelledError",
                    "ValueError",
                    "NotImplementedError",
                    "SessionProtocolError",
                }
                else "OtherError"
            )
            for field in ("errno", "winerror"):
                value = getattr(error, field, None)
                if type(value) is int and -(2**31) <= value < 2**32:
                    event[field] = value
        if type(count) is int:
            event["count"] = min(MAX_FRAME + 1, max(0, count))
        if loop_kind is not None:
            event["loop_kind"] = (
                loop_kind
                if loop_kind
                in {
                    "ProactorEventLoop",
                    "_WindowsSelectorEventLoop",
                    "_UnixSelectorEventLoop",
                }
                else "OtherLoop"
            )
        diagnostic(event)
    except Exception:
        pass  # Observation failure must not change protocol control flow.


class _WindowsReadPipe:
    """Own one CRT duplicate, expose its HANDLE to Proactor, never CloseHandle it.

    A plain class is intentionally weak-referenceable for IOCP registration.
    Original stdin retains its original owner; only this duplicate is closed.
    """

    def __init__(self, input_fd, diagnostic=None):
        self._fd = os.dup(input_fd)
        self._diagnostic = diagnostic

    def fileno(self):
        if self._fd is None:
            raise ValueError("Closed private session pipe")
        import msvcrt

        _emit(self._diagnostic, "input-handle", "start")
        try:
            handle = msvcrt.get_osfhandle(self._fd)
        except OSError as error:
            _emit(self._diagnostic, "input-handle", "error", error=error)
            raise
        _emit(self._diagnostic, "input-handle", "done")
        return handle

    def close(self):
        owned, self._fd = self._fd, None
        if owned is not None:
            os.close(
                owned
            )  # Detach first: even failure cannot double-close a reused CRT slot.


def _open_input_pipe(input_fd, diagnostic=None):
    if os.name == "nt":
        return _WindowsReadPipe(input_fd, diagnostic)
    return os.fdopen(os.dup(input_fd), "rb", buffering=0)


class _SessionReader(asyncio.StreamReaderProtocol):
    def __init__(self, reader, closed, diagnostic=None):
        super().__init__(reader)
        self.closed = closed
        self.diagnostic = diagnostic

    def data_received(self, data):
        _emit(self.diagnostic, "input-read", "done", count=len(data))
        super().data_received(data)

    def eof_received(self):
        _emit(self.diagnostic, "input-eof", "done")
        return super().eof_received()

    def connection_lost(self, error):
        _emit(
            self.diagnostic,
            "connection-lost",
            "error" if error else "done",
            error=error,
        )
        try:
            super().connection_lost(error)
        finally:
            if not self.closed.done():
                self.closed.set_result(None)


async def request_session(*, timeout=240, input_fd=0, request_fd=4, diagnostic=None):
    """One demand then bounded frame+EOF; async pipes on POSIX/Windows3.10+."""
    transport = None
    pipe = None
    primary = None
    phase = "request-write"
    try:
        try:
            body = b'{"type":"session_needed","terminal":true}'
            request = b"ZLAD\x02" + len(body).to_bytes(2, "big") + body
            write_error = None
            try:
                _emit(diagnostic, phase, "start")
                written = os.write(request_fd, request)
                _emit(diagnostic, phase, "done", count=written)
                if written != len(request):
                    raise OSError()
            except BaseException as error:
                write_error = error
                _emit(diagnostic, "request-write", "error", error=error)
                raise
            finally:
                phase = "request-close"
                _emit(diagnostic, phase, "start")
                try:
                    os.close(request_fd)
                    _emit(diagnostic, phase, "done")
                except BaseException as error:
                    _emit(diagnostic, phase, "error", error=error)
                    if write_error is None:
                        raise
                if write_error is not None:
                    phase = "request-write"
            loop = asyncio.get_running_loop()
            _emit(diagnostic, "loop", "done", loop_kind=type(loop).__name__)
            closed = loop.create_future()
            reader = asyncio.StreamReader(limit=MAX_FRAME + 1)
            phase = "input-duplicate"
            _emit(diagnostic, phase, "start")
            pipe = _open_input_pipe(input_fd, diagnostic)
            _emit(diagnostic, phase, "done")
            phase = "input-connect"
            _emit(diagnostic, phase, "start")
            try:
                transport, _ = await loop.connect_read_pipe(
                    lambda: _SessionReader(reader, closed, diagnostic), pipe
                )
            except (OSError, NotImplementedError, ValueError) as error:
                _emit(diagnostic, phase, "error", error=error)
                raise SessionProtocolError(
                    "Asynchronous private session pipe unavailable"
                ) from None
            _emit(diagnostic, phase, "done")

            async def receive():
                nonlocal phase
                data = bytearray()
                while True:
                    phase = "input-read"
                    _emit(diagnostic, phase, "start")
                    chunk = await reader.read(min(4096, MAX_FRAME + 1 - len(data)))
                    if not chunk:
                        phase = "parse"
                        try:
                            value = parse_session_frame(bytes(data))
                        except SessionProtocolError as error:
                            _emit(
                                diagnostic,
                                phase,
                                "denied"
                                if str(error) == "Private session request denied"
                                else "invalid",
                            )
                            raise
                        _emit(diagnostic, phase, "done")
                        return value
                    data.extend(chunk)
                    if len(data) > MAX_FRAME:
                        _emit(diagnostic, "parse", "invalid")
                        raise SessionProtocolError("Invalid private session reply")

            try:
                result = await asyncio.wait_for(receive(), timeout)
            except asyncio.TimeoutError:
                _emit(diagnostic, phase, "timeout")
                raise SessionProtocolError(
                    "Private session reply deadline exceeded"
                ) from None
            _emit(diagnostic, "primary", "done")
            return result
        except OSError as error:
            _emit(diagnostic, phase, "error", error=error)
            raise SessionProtocolError("Private session parent unavailable") from None
    except BaseException as error:
        primary = error
        _emit(
            diagnostic,
            "primary",
            "cancelled" if isinstance(error, asyncio.CancelledError) else "error",
            error=error,
        )
        raise
    finally:
        _emit(diagnostic, "cleanup", "start")
        try:
            if transport is not None:
                _emit(diagnostic, "transport-close", "start")
                transport.close()
                _emit(diagnostic, "transport-close", "done")
                await asyncio.wait_for(asyncio.shield(closed), 1)
            elif pipe is not None:
                pipe.close()
            _emit(diagnostic, "cleanup", "done")
        except BaseException as error:
            _emit(diagnostic, "cleanup", "error", error=error)
            if primary is None:
                if not isinstance(error, Exception):
                    raise
                raise SessionProtocolError("Private session cleanup failed") from None
            # Preserve the primary rejection/cancellation; cleanup cannot turn it
            # into a different protocol failure (nor a valid result into success).
