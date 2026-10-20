"""Offline failures used to record pytest JUnit exception shapes (2026-10-20)."""

import httpx
import pytest
from zlibrary.eapi import decode_eapi_json


@pytest.fixture(params=[httpx.ConnectError, httpx.ConnectTimeout])
def refused(request):
    raise request.param("")


def test_connect_setup(refused):
    pass


@pytest.fixture
def refused_message():
    raise httpx.ConnectError("All connection attempts failed")


def test_connect_message_setup(refused_message):
    pass


@pytest.fixture
def refused_teardown():
    yield
    raise httpx.ConnectError("")


def test_connect_teardown(refused_teardown):
    pass


def test_connect_call():
    raise httpx.ConnectError("")


@pytest.mark.parametrize("domain", ["z-library.ec", "z-library.sk", "z-library.ec.evil"])
def test_wall_call(domain):
    decode_eapi_json(httpx.Response(513, text="DiamWall"), domain)


@pytest.fixture
def walled():
    decode_eapi_json(httpx.Response(517, text="DiamWall"), "z-library.ec")


def test_wall_setup(walled):
    pass


@pytest.mark.parametrize("status", [403, 513, 517])
def test_bare_status(status):
    decode_eapi_json(httpx.Response(status, text="Access denied"), "z-library.ec")


def test_drift():
    raise KeyError("books")
