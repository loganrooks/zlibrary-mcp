"""
Pytest fixtures for integration tests.

Provides a module-scoped zlib_client fixture that authenticates
with Z-Library via EAPIClient for test methods that declare it.
"""

import os
import sys

import pytest
import pytest_asyncio

# Add project lib/ to path so zlibrary imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "lib"))

from zlibrary.eapi import EAPIClient  # noqa: E402

import python_bridge  # noqa: E402


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def zlib_client():
    """Pre-authenticated EAPIClient for integration tests.

    Reads credentials from environment variables.
    Yields the client, then closes it during teardown.

    Also installs the client as python_bridge's module-level EAPI client:
    python_bridge functions (search, get_book_metadata_complete, ...) resolve
    their client via the module-level singleton — the ``client=`` keyword is
    kept only for backward compatibility and is ignored — so without this the
    bridge-level tests would fail with "EAPI client not initialized".
    """
    email = os.environ.get("ZLIBRARY_EMAIL", "")
    password = os.environ.get("ZLIBRARY_PASSWORD", "")
    domain = os.environ.get("ZLIBRARY_EAPI_DOMAIN", "z-library.sk")

    client = EAPIClient(domain)
    login_result = await client.login(email, password)
    assert login_result.get("success") == 1, (
        f"zlib_client fixture: login failed — {login_result}"
    )

    previous_global = python_bridge._eapi_client
    python_bridge._eapi_client = client

    yield client

    python_bridge._eapi_client = previous_global
    await client.close()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def known_book(zlib_client):
    """A live (id, hash) pair for a book that exists right now.

    Z-Library book hashes drift when files are replaced (e.g. book 1252896's
    hash changed from 882753 to ef25bc), so metadata tests resolve a book from
    a live search instead of hardcoding a pair.
    """
    result = await zlib_client.search(
        "Hegel Encyclopaedia Philosophical Sciences", limit=5
    )
    for book in result.get("books", []):
        if book.get("id") and book.get("hash"):
            return {"id": str(book["id"]), "hash": str(book["hash"])}
    result = await zlib_client.search("philosophy", limit=5)
    for book in result.get("books", []):
        if book.get("id") and book.get("hash"):
            return {"id": str(book["id"]), "hash": str(book["hash"])}
    pytest.skip("No searchable book with id+hash available to test metadata against")
