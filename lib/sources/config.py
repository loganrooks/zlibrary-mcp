"""Configuration for multi-source book search system.

Environment variables:
    ANNAS_SECRET_KEY: API key for Anna's Archive fast downloads
    ANNAS_BASE_URL: Anna's Archive base URL (default: https://annas-archive.li)
    LIBGEN_MIRROR: LibGen mirror to use (default: li)
    BOOK_SOURCE_DEFAULT: Default source selection (auto|annas|libgen)
    BOOK_SOURCE_FALLBACK_ENABLED: Enable fallback to other source (default: true)
"""

import os
from dataclasses import dataclass


@dataclass
class SourceConfig:
    """Configuration for book source adapters.

    Attributes:
        annas_secret_key: API key for Anna's Archive fast downloads
        annas_base_url: Anna's Archive base URL
        libgen_mirror: LibGen mirror suffix (e.g., 'li', 'rs')
        default_source: Which source to try first ('auto', 'annas', 'libgen')
        fallback_enabled: Whether to try other source if primary fails
    """

    annas_secret_key: str = ""
    annas_base_url: str = "https://annas-archive.li"
    libgen_mirror: str = "li"
    default_source: str = "auto"  # 'auto' | 'annas' | 'libgen'
    fallback_enabled: bool = True

    @property
    def has_annas_key(self) -> bool:
        """Check if Anna's Archive API key is configured."""
        return bool(self.annas_secret_key)


def get_source_config() -> SourceConfig:
    """Load configuration from environment variables.

    Returns a fresh SourceConfig each call (not cached) to support
    environment variable changes during testing.
    """
    return SourceConfig(
        annas_secret_key=os.environ.get("ANNAS_SECRET_KEY", ""),
        annas_base_url=os.environ.get("ANNAS_BASE_URL", "https://annas-archive.li"),
        libgen_mirror=os.environ.get("LIBGEN_MIRROR", "li"),
        default_source=os.environ.get("BOOK_SOURCE_DEFAULT", "auto"),
        fallback_enabled=os.environ.get("BOOK_SOURCE_FALLBACK_ENABLED", "true").lower()
        == "true",
    )
