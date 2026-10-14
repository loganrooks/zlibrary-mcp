"""Exercise the exact live invalid-login method without importing its module."""

import ast
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest


class FakeClient:
    def __init__(self, result=None, login_error=None, close_error=None):
        self.result = result
        self.login_error = login_error
        self.close_error = close_error
        self.closed = 0

    async def login(self, email, password):
        assert (email, password) == ("invalid@example.com", "wrongpassword")
        if self.login_error:
            raise self.login_error
        return self.result

    async def close(self):
        self.closed += 1
        if self.close_error:
            raise self.close_error


@pytest.fixture
def invalid_login(monkeypatch):
    source = Path(__file__).parent / "integration" / "test_real_zlibrary.py"
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    auth_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "TestRealAuthentication"
    )
    method = next(
        node
        for node in auth_class.body
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name == "test_authentication_fails_with_invalid_credentials"
    )
    # Only this AST node executes, never module imports, decorators or fixtures.
    namespace = {"os": SimpleNamespace(environ={})}
    exec(
        compile(ast.Module(body=[method], type_ignores=[]), str(source), "exec"),
        namespace,
    )
    extracted = namespace[method.name]

    async def run(client):
        module = ModuleType("zlibrary.eapi")

        def make_client(domain):
            assert domain == "z-library.sk"  # Empty environment, no operator secrets.
            return client

        module.EAPIClient = make_client
        monkeypatch.setitem(sys.modules, "zlibrary.eapi", module)
        await extracted(None)

    return run


async def test_unexpected_success_fails_and_closes(invalid_login):
    # Mutation caught: swallowing AssertionError inside the login try/except.
    client = FakeClient(result={"success": 1})
    with pytest.raises(AssertionError):
        await invalid_login(client)
    assert client.closed == 1


@pytest.mark.parametrize("result", [{"success": 0}, {}])
async def test_returned_rejection_is_accepted_and_closed(invalid_login, result):
    client = FakeClient(result=result)
    await invalid_login(client)
    assert client.closed == 1


async def test_login_exception_is_accepted_and_closed(invalid_login):
    client = FakeClient(login_error=RuntimeError("rejected"))
    await invalid_login(client)
    assert client.closed == 1


@pytest.mark.parametrize("login_error", [None, RuntimeError("rejected")])
async def test_cleanup_failure_propagates(invalid_login, login_error):
    client = FakeClient(
        result={"success": 0}, login_error=login_error, close_error=OSError("cleanup")
    )
    with pytest.raises(OSError, match="cleanup"):
        await invalid_login(client)
    assert client.closed == 1
