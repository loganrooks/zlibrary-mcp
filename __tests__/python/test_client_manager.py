"""
Unit tests for ZLibraryClient manager.

Tests the lifecycle management, context manager protocol,
and resource cleanup of the ZLibraryClient class.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from lib.client_manager import (
    ZLibraryClient,
    get_default_client,
    reset_default_client
)


class TestZLibraryClientInitialization:
    """Test client initialization and configuration."""

    def test_init_with_explicit_credentials(self):
        """Should initialize with explicit credentials."""
        client = ZLibraryClient(
            email="test@example.com",
            password="testpass"
        )

        assert client.email == "test@example.com"
        assert client.password == "testpass"
        assert client._client is None
        assert client._initialized is False

    def test_init_with_env_credentials(self):
        """Should fall back to environment variables."""
        with patch.dict(os.environ, {
            'ZLIBRARY_EMAIL': 'env@example.com',
            'ZLIBRARY_PASSWORD': 'envpass'
        }):
            client = ZLibraryClient()

            assert client.email == "env@example.com"
            assert client.password == "envpass"

    def test_init_without_credentials_raises(self):
        """Should raise ValueError if no credentials available."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                ZLibraryClient()

            assert "credentials required" in str(exc_info.value).lower()

    def test_init_with_mirror(self):
        """Should accept custom mirror URL."""
        client = ZLibraryClient(
            email="test@example.com",
            password="testpass",
            mirror="https://custom-mirror.org"
        )

        assert client.mirror == "https://custom-mirror.org"


class TestZLibraryClientLifecycle:
    """Test client lifecycle management."""

    @patch('lib.client_manager.AsyncZlib')
    @pytest.mark.asyncio
    async def test_get_client_initializes_once(self, mock_zlib_class):
        """Should initialize client only once."""
        from unittest.mock import AsyncMock

        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib

        # Use AsyncMock to preserve MagicMock methods
        mock_zlib.login = AsyncMock()

        client_manager = ZLibraryClient(
            email="test@example.com",
            password="testpass"
        )

        # First call should initialize
        client1 = await client_manager.get_client()
        assert client_manager.is_initialized()

        # Second call should return same instance
        client2 = await client_manager.get_client()
        assert client1 is client2

        # Login should only be called once
        mock_zlib.login.assert_called_once()

    @patch('lib.client_manager.AsyncZlib')
    @pytest.mark.asyncio
    async def test_cleanup_resets_state(self, mock_zlib_class):
        """Should reset state on cleanup."""
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib

        async def mock_login(*args, **kwargs):
            return None
        mock_zlib.login = mock_login

        client_manager = ZLibraryClient(
            email="test@example.com",
            password="testpass"
        )

        # Initialize
        await client_manager.get_client()
        assert client_manager.is_initialized()

        # Cleanup
        await client_manager.cleanup()
        assert not client_manager.is_initialized()
        assert client_manager._client is None

    @patch('lib.client_manager.AsyncZlib')
    @pytest.mark.asyncio
    async def test_cleanup_is_idempotent(self, mock_zlib_class):
        """Should safely handle multiple cleanup calls."""
        client_manager = ZLibraryClient(
            email="test@example.com",
            password="testpass"
        )

        # Cleanup without initialization
        await client_manager.cleanup()

        # Should not raise
        await client_manager.cleanup()
        await client_manager.cleanup()


class TestZLibraryClientContextManager:
    """Test async context manager protocol."""

    @patch('lib.client_manager.AsyncZlib')
    @pytest.mark.asyncio
    async def test_context_manager_initializes(self, mock_zlib_class):
        """Should initialize client on context entry."""
        from unittest.mock import AsyncMock

        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib

        # Use AsyncMock
        mock_zlib.login = AsyncMock()

        async with ZLibraryClient("test@example.com", "testpass") as client:
            assert client is not None
            assert client is mock_zlib

        # Login should have been called
        mock_zlib.login.assert_called_once()

    @patch('lib.client_manager.AsyncZlib')
    @pytest.mark.asyncio
    async def test_context_manager_cleans_up(self, mock_zlib_class):
        """Should cleanup on context exit."""
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib

        async def mock_login(*args, **kwargs):
            return None
        mock_zlib.login = mock_login

        client_manager = ZLibraryClient("test@example.com", "testpass")

        async with client_manager as client:
            assert client_manager.is_initialized()

        # Should be cleaned up after exit
        assert not client_manager.is_initialized()

    @patch('lib.client_manager.AsyncZlib')
    @pytest.mark.asyncio
    async def test_context_manager_cleanup_on_exception(self, mock_zlib_class):
        """Should cleanup even if exception occurs."""
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib

        async def mock_login(*args, **kwargs):
            return None
        mock_zlib.login = mock_login

        client_manager = ZLibraryClient("test@example.com", "testpass")

        try:
            async with client_manager as client:
                assert client_manager.is_initialized()
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Should still be cleaned up
        assert not client_manager.is_initialized()


class TestDefaultClientManagement:
    """Test module-level default client functions."""

    @patch('lib.client_manager.AsyncZlib')
    @pytest.mark.asyncio
    async def test_get_default_client_creates_instance(self, mock_zlib_class):
        """Should create default client if none exists."""
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib

        async def mock_login(*args, **kwargs):
            return None
        mock_zlib.login = mock_login

        with patch.dict(os.environ, {
            'ZLIBRARY_EMAIL': 'test@example.com',
            'ZLIBRARY_PASSWORD': 'testpass'
        }):
            # Reset first
            await reset_default_client()

            client = await get_default_client()
            assert client is not None
            assert client is mock_zlib

    @patch('lib.client_manager.AsyncZlib')
    @pytest.mark.asyncio
    async def test_reset_default_client_cleans_up(self, mock_zlib_class):
        """Should cleanup default client on reset."""
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib

        async def mock_login(*args, **kwargs):
            return None
        mock_zlib.login = mock_login

        with patch.dict(os.environ, {
            'ZLIBRARY_EMAIL': 'test@example.com',
            'ZLIBRARY_PASSWORD': 'testpass'
        }):
            # Create default client
            await get_default_client()

            # Reset should cleanup
            await reset_default_client()

            # Next call should create new instance
            client2 = await get_default_client()
            assert client2 is not None


class TestErrorHandling:
    """Test error handling in client manager."""

    @patch('lib.client_manager.AsyncZlib')
    @pytest.mark.asyncio
    async def test_login_failure_propagates(self, mock_zlib_class):
        """Should propagate login failures as AuthenticationError."""
        from zlibrary.exception import LoginFailed
        from lib.client_manager import AuthenticationError

        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib

        async def mock_login(*args, **kwargs):
            raise LoginFailed("Invalid credentials")
        mock_zlib.login = mock_login

        client_manager = ZLibraryClient("test@example.com", "wrongpass")

        # Client manager wraps LoginFailed in AuthenticationError
        with pytest.raises(AuthenticationError):
            await client_manager.get_client()

        # Should not be initialized after failure
        assert not client_manager.is_initialized()

    @patch('lib.client_manager.AsyncZlib')
    @pytest.mark.asyncio
    async def test_context_manager_propagates_exceptions(self, mock_zlib_class):
        """Should not suppress exceptions from async with block."""
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib

        async def mock_login(*args, **kwargs):
            return None
        mock_zlib.login = mock_login

        with pytest.raises(RuntimeError):
            async with ZLibraryClient("test@example.com", "testpass") as client:
                raise RuntimeError("Test error")


class TestClientReinitializationAfterCleanup:
    """Test that client can be reinitialized after cleanup."""

    @patch('lib.client_manager.AsyncZlib')
    @pytest.mark.asyncio
    async def test_can_reinitialize_after_cleanup(self, mock_zlib_class):
        """Should be able to create new client after cleanup."""
        from unittest.mock import AsyncMock

        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib

        # Use AsyncMock
        mock_zlib.login = AsyncMock()

        client_manager = ZLibraryClient("test@example.com", "testpass")

        # Initialize
        client1 = await client_manager.get_client()
        assert client_manager.is_initialized()

        # Cleanup
        await client_manager.cleanup()
        assert not client_manager.is_initialized()

        # Reinitialize
        client2 = await client_manager.get_client()
        assert client_manager.is_initialized()

        # Should have called login twice (once per initialization)
        assert mock_zlib.login.call_count == 2

    @patch('lib.client_manager.AsyncZlib')
    @pytest.mark.asyncio
    async def test_multiple_context_manager_uses(self, mock_zlib_class):
        """Should support multiple context manager uses."""
        from unittest.mock import AsyncMock

        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib

        # Use AsyncMock
        mock_zlib.login = AsyncMock()

        client_manager = ZLibraryClient("test@example.com", "testpass")

        # First use
        async with client_manager as client1:
            assert client1 is not None

        # Second use (after cleanup)
        async with client_manager as client2:
            assert client2 is not None

        # Should have logged in twice
        assert mock_zlib.login.call_count == 2
