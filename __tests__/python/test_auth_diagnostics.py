import json
import logging
import sys

import httpx
import pytest

import python_bridge


@pytest.mark.parametrize(
    "status,cleanup",
    [(200, False), (400, False), (503, False), (None, False), (400, True)],
)
async def test_main_bounds_untrusted_error_payloads(
    status, cleanup, monkeypatch, capsys, caplog
):
    """Catches arbitrary exception text/tracebacks in the real bridge envelope/log."""
    poison = "i251-password i251-cookie i251-token i251@example.test i251-body\n" * 2000
    request = httpx.Request("GET", "https://i251-token:i251-password@fake.test/")
    failure = (
        httpx.HTTPStatusError(
            poison, request=request, response=httpx.Response(status, request=request)
        )
        if status is not None
        else type("i251-token" * 1000, (RuntimeError,), {})(poison)
    )

    async def initialize():
        if cleanup:

            class Client:
                needs_profile_validation = False
                remix_userkey = "i251-cookie"
                remix_userid = "17"
                domain = "fake.test"

                async def close(self):
                    raise RuntimeError("i251-cleanup")

            python_bridge._eapi_client = Client()
        return None

    async def dispatch(*args):
        logging.getLogger("zlibrary").exception(poison)
        raise failure

    monkeypatch.setattr(python_bridge, "_eapi_client", None)
    monkeypatch.setattr(python_bridge, "_session_input", None)
    monkeypatch.setattr(python_bridge, "initialize_eapi_client", initialize)
    monkeypatch.setattr(python_bridge, "_dispatch_bridge_function", dispatch)
    monkeypatch.setattr(
        sys, "argv", ["python_bridge.py", "search", json.dumps({"query": poison})]
    )
    with pytest.raises(SystemExit) as stopped:
        await python_bridge.main()
    assert stopped.value.code == 1
    streams = capsys.readouterr()
    for sentinel in [
        "i251-password",
        "i251-cookie",
        "i251-token",
        "i251@example.test",
        "i251-body",
        "i251-cleanup",
    ]:
        assert sentinel not in streams.out + streams.err + caplog.text
    encoded = streams.err.strip().splitlines()[-1]
    assert len(encoded.encode()) <= 2048
    data = json.loads(encoded)
    assert "traceback" not in data
    assert data["diagnostics"]["failure_kind"] == "ambiguous_status"
    if status is not None:
        assert data["diagnostics"]["http_status"] == status
    else:
        assert "http_status" not in data["diagnostics"]
    assert len(json.dumps(data["diagnostics"]).encode()) <= 512


@pytest.mark.parametrize(
    "field,value",
    [
        ("request_id", "i251-token"),
        ("failure_kind", "i251-token"),
        ("attempt", True),
        ("http_status", "i251-token"),
    ],
)
def test_malformed_log_diagnostics_are_rejected_whole(field, value, caplog):
    diagnostics = {
        "failure_kind": "wall",
        "attempt": 1,
        "refresh_count": 0,
        "request_id": "00000000-0000-4000-8000-000000000001",
    }
    diagnostics[field] = value
    caplog.clear()
    logging.getLogger("zlibrary").warning("", extra={"auth_diagnostics": diagnostics})
    assert not caplog.records


async def test_health_failure_and_metadata_logging_do_not_bypass_projection(
    monkeypatch, caplog
):
    poison = "i251-body i251@example.test i251-token"

    class Client:
        async def search(self, *args, **kwargs):
            logging.getLogger("lib.enhanced_metadata").error(poison)
            raise httpx.ReadTimeout(poison)

    monkeypatch.setattr(python_bridge, "_session_input", None)
    monkeypatch.setattr(python_bridge, "_eapi_client", Client())
    result = await python_bridge.eapi_health_check()
    assert "i251" not in json.dumps(result) + caplog.text
    assert result["diagnostics"]["failure_kind"] == "transport"


@pytest.mark.parametrize("kind", ["auth_rejected", "transport"])
async def test_per_call_acquisition_failure_before_client_assignment(
    kind, tmp_path, monkeypatch, capsys
):
    from zlibrary.eapi import EAPIAuthenticationError

    failure = (
        EAPIAuthenticationError("i251-provider-prose", status_code=401)
        if kind == "auth_rejected"
        else httpx.ConnectTimeout("i251-provider-prose")
    )

    async def login(*args):
        raise failure

    monkeypatch.setenv("ZLIBRARY_EMAIL", "i251@example.test")
    monkeypatch.setenv("ZLIBRARY_PASSWORD", "i251-password")
    monkeypatch.setattr(python_bridge, "_lazy_session", False)
    monkeypatch.setattr(python_bridge, "_eapi_client", None)
    monkeypatch.setattr(python_bridge, "_session_input", None)
    monkeypatch.setattr(python_bridge, "_login_eapi_client", login)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "python_bridge.py",
            "acquire_book",
            json.dumps(
                {
                    "book_details": {
                        "source": "zlibrary",
                        "id": "17",
                        "book_hash": "hash",
                        "title": "offline",
                        "extension": "epub",
                    },
                    "output_dir": str(tmp_path),
                }
            ),
        ],
    )
    with pytest.raises(SystemExit) as stopped:
        await python_bridge.main()
    assert stopped.value.code == 1
    streams = capsys.readouterr()
    data = json.loads(streams.err.strip().splitlines()[-1])
    assert "i251-provider-prose" not in streams.err + streams.out
    assert data["diagnostics"]["failure_kind"] == kind
    assert python_bridge._eapi_client is None
    assert python_bridge._session_input is None


async def test_local_acquisition_refusal_does_not_gain_eapi_diagnostics(
    tmp_path, monkeypatch, capsys
):
    async def forbidden():
        pytest.fail("local admission must not initialize EAPI")

    monkeypatch.setattr(python_bridge, "_eapi_client", None)
    monkeypatch.setattr(python_bridge, "_session_input", None)
    monkeypatch.setattr(python_bridge, "initialize_eapi_client", forbidden)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "python_bridge.py",
            "acquire_book",
            json.dumps(
                {
                    "book_details": {"source": "zlibrary"},
                    "output_dir": str(tmp_path),
                    "filename": "../escape.epub",
                }
            ),
        ],
    )
    with pytest.raises(SystemExit) as stopped:
        await python_bridge.main()
    assert stopped.value.code == 1
    data = json.loads(capsys.readouterr().err.strip().splitlines()[-1])
    assert data["details"]["reason"] == "invalid_argument"
    assert "diagnostics" not in data


@pytest.mark.parametrize("issued", [False, True])
async def test_local_budget_after_eapi_setup_keeps_its_original_verdict(
    issued, monkeypatch, capsys
):
    from lib.acquisition import AcquisitionError

    class Client:
        needs_profile_validation = False
        remix_userkey = "fixture-secret"

        async def close(self):
            pass

    async def dispatch(*args):
        raise AcquisitionError(
            "walk_budget_exhausted", "Acquisition deadline exhausted", issued=issued
        )

    monkeypatch.setattr(python_bridge, "_eapi_client", Client())
    monkeypatch.setattr(python_bridge, "_session_input", None)
    monkeypatch.setattr(python_bridge, "_dispatch_bridge_function", dispatch)
    monkeypatch.setattr(sys, "argv", ["python_bridge.py", "acquire_book", "{}"])
    with pytest.raises(SystemExit) as stopped:
        await python_bridge.main()
    assert stopped.value.code == 1
    data = json.loads(capsys.readouterr().err.strip().splitlines()[-1])
    assert data["type"] == "AcquisitionError"
    assert data["details"]["reason"] == "walk_budget_exhausted"
    assert data["details"]["request_issued"] is issued
    assert "diagnostics" not in data


@pytest.mark.parametrize("name", ["zlibrary.sources", "zlibrary.sources.future"])
def test_child_logger_payloads_are_filtered_at_stderr_and_file_handlers(name):
    import io
    from lib.auth_diagnostics import DiagnosticLogFilter

    child = logging.getLogger(name)
    streams = [io.StringIO(), io.StringIO()]
    handlers = [logging.StreamHandler(stream) for stream in streams]
    root = logging.getLogger()
    originals = list(root.handlers)
    try:
        root.handlers = handlers
        python_bridge._configure_debug_logging()
        child.error("i286-provider-secret", exc_info=True, stack_info=True)
        assert all(
            "i286-provider-secret" not in stream.getvalue() for stream in streams
        )
        diagnostics = {
            "failure_kind": "transport",
            "attempt": 1,
            "refresh_count": 0,
            "request_id": "00000000-0000-4000-8000-000000000001",
        }
        child.warning("i286-provider-secret", extra={"auth_diagnostics": diagnostics})
        for stream in streams:
            assert json.loads(stream.getvalue().strip()) == diagnostics
            assert "Traceback" not in stream.getvalue()
        logging.getLogger("unrelated").warning("ordinary unrelated message")
        assert all(
            "ordinary unrelated message" in stream.getvalue() for stream in streams
        )
        assert any(
            isinstance(f, DiagnosticLogFilter) for f in python_bridge.logger.filters
        )
    finally:
        root.handlers = originals
        for handler in handlers:
            handler.close()


@pytest.mark.parametrize(
    "reason",
    [
        "invalid_argument",
        "output_refused",
        "configuration_error",
        "breaker_open",
        "walk_budget_exhausted",
    ],
)
async def test_local_refusal_after_setup_does_not_imply_a_provider_request(
    reason, monkeypatch, capsys
):
    from lib.acquisition import AcquisitionError

    async def initialize():
        pass

    async def dispatch(*args):
        raise AcquisitionError(reason, "local refusal", issued=False)

    monkeypatch.setattr(python_bridge, "_eapi_client", None)
    monkeypatch.setattr(python_bridge, "_session_input", None)
    monkeypatch.setattr(python_bridge, "initialize_eapi_client", initialize)
    monkeypatch.setattr(python_bridge, "_dispatch_bridge_function", dispatch)
    monkeypatch.setattr(
        sys,
        "argv",
        ["python_bridge.py", "download_book", '{"book_details":{"id":"17"}}'],
    )
    with pytest.raises(SystemExit) as stopped:
        await python_bridge.main()
    assert stopped.value.code == 1
    data = json.loads(capsys.readouterr().err.strip().splitlines()[-1])
    assert data["details"]["reason"] == reason
    assert data["details"]["request_issued"] is False
    assert "diagnostics" not in data
