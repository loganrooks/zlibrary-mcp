"""
DEPRECATED: Z-Library Client Manager (AsyncZlib wrapper).

This module is no longer used by production code as of plan 08-02.
All downloads now route through EAPIClient.download_file() in eapi_client.py.
The module is retained only for backward compatibility with existing tests.

Previously provided a managed Z-Library client that handles:
- Authentication lifecycle
- Resource cleanup
- Session management
- Test isolation
"""

import os
import logging
from typing import Optional
import sys

# Add zlibrary to path
zlibrary_path = os.path.join(os.path.dirname(__file__), "..", "zlibrary")
sys.path.insert(0, zlibrary_path)

from zlibrary import AsyncZlib

logger = logging.getLogger("zlibrary")


class RateLimitError(Exception):
    """Raised when Z-Library rate limiting is detected."""

    pass


class AuthenticationError(Exception):
    """Raised when Z-Library authentication fails."""

    pass


class ZLibraryClient:
    """
    Managed Z-Library client with async context manager support.

    Provides proper lifecycle management for Z-Library sessions,
    enabling test isolation and resource cleanup.

    Usage:
        # Context manager (recommended):
        async with ZLibraryClient(email, password) as client:
            result = await client.search("query")

        # Manual lifecycle:
        manager = ZLibraryClient(email, password)
        client = await manager.get_client()
        # ... use client ...
        await manager.cleanup()

        # Test injection:
        result = await search(query="test", client=client)
    """

    def __init__(
        self,
        email: Optional[str] = None,
        password: Optional[str] = None,
        mirror: Optional[str] = None,
    ):
        """
        Initialize client manager.

        Args:
            email: Z-Library email (defaults to ZLIBRARY_EMAIL env var)
            password: Z-Library password (defaults to ZLIBRARY_PASSWORD env var)
            mirror: Optional mirror URL (defaults to ZLIBRARY_MIRROR env var)
        """
        self.email = email or os.getenv("ZLIBRARY_EMAIL")
        self.password = password or os.getenv("ZLIBRARY_PASSWORD")
        self.mirror = mirror or os.getenv("ZLIBRARY_MIRROR", "")

        if not self.email or not self.password:
            raise ValueError(
                "Z-Library credentials required. "
                "Provide email/password or set ZLIBRARY_EMAIL/ZLIBRARY_PASSWORD environment variables."
            )

        self._client: Optional[AsyncZlib] = None
        self._initialized = False

    async def __aenter__(self) -> AsyncZlib:
        """
        Async context manager entry.

        Initializes and authenticates the Z-Library client.

        Returns:
            Authenticated AsyncZlib instance
        """
        return await self.get_client()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit.

        Cleans up resources and closes the client session.

        Returns:
            False (doesn't suppress exceptions)
        """
        await self.cleanup()
        return False

    async def get_client(self) -> AsyncZlib:
        """
        Get or create an authenticated Z-Library client.

        Lazy initialization - only creates and authenticates on first call.

        Returns:
            Authenticated AsyncZlib instance

        Raises:
            RateLimitError: If Z-Library rate limiting detected
            AuthenticationError: If login fails
            LoginFailed: If authentication fails (from zlibrary)
        """
        if self._client is None or not self._initialized:
            logger.info("Initializing new Z-Library client session")

            self._client = AsyncZlib()

            try:
                await self._client.login(self.email, self.password)
                self._initialized = True
                logger.info("Z-Library client authenticated successfully")

            except AttributeError as e:
                # This specific error indicates Z-Library rate limiting
                if "'NoneType' object has no attribute 'get'" in str(e):
                    logger.error("Z-Library rate limit detected during login")
                    raise RateLimitError(
                        "Z-Library rate limit detected. "
                        "Too many login attempts in short time. "
                        "Please wait 10-15 minutes before trying again."
                    ) from e
                raise

            except Exception as e:
                logger.error(f"Authentication failed: {e}")
                raise AuthenticationError(
                    f"Failed to authenticate with Z-Library: {e}"
                ) from e

        return self._client

    async def cleanup(self):
        """
        Clean up client resources.

        Closes session and resets state.
        Safe to call multiple times.
        """
        if self._client:
            logger.debug("Cleaning up Z-Library client session")
            # AsyncZlib doesn't have explicit close, but we can reset state
            self._client = None
            self._initialized = False

    def is_initialized(self) -> bool:
        """
        Check if client is initialized and authenticated.

        Returns:
            True if client is ready for use
        """
        return self._initialized and self._client is not None


# Module-level default client manager (for backward compatibility)
# DEPRECATED: Use dependency injection instead
_default_client_manager: Optional[ZLibraryClient] = None


async def get_default_client() -> AsyncZlib:
    """
    Get the module-level default client.

    DEPRECATED: This function maintains backward compatibility but uses
    global state. Prefer creating ZLibraryClient instances or using
    dependency injection.

    Returns:
        Authenticated AsyncZlib instance

    Raises:
        ValueError: If credentials not available
    """
    global _default_client_manager

    if _default_client_manager is None:
        logger.warning(
            "Using deprecated default client. "
            "Consider using ZLibraryClient() or dependency injection instead."
        )
        _default_client_manager = ZLibraryClient()

    return await _default_client_manager.get_client()


async def reset_default_client():
    """
    Reset the module-level default client.

    Useful for tests and cleanup scenarios.
    """
    global _default_client_manager

    if _default_client_manager:
        await _default_client_manager.cleanup()
        _default_client_manager = None
