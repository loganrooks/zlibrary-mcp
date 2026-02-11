"""
Pytest fixtures for integration tests.

Provides a module-scoped zlib_client fixture that authenticates
with Z-Library via EAPIClient for test methods that declare it.
"""

import os
import sys

import pytest

# Add project lib/ to path so zlibrary imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "lib"))

from zlibrary.eapi import EAPIClient  # noqa: E402


@pytest.fixture(scope="module")
async def zlib_client():
    """Pre-authenticated EAPIClient for integration tests.

    Reads credentials from environment variables.
    Yields the client, then closes it during teardown.
    """
    email = os.environ.get("ZLIBRARY_EMAIL", "")
    password = os.environ.get("ZLIBRARY_PASSWORD", "")
    domain = os.environ.get("ZLIBRARY_EAPI_DOMAIN", "z-library.sk")

    client = EAPIClient(domain)
    login_result = await client.login(email, password)
    assert login_result.get("success") == 1, (
        f"zlib_client fixture: login failed — {login_result}"
    )

    yield client

    await client.close()
