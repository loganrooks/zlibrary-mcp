"""Helpers for replacing RAG output files atomically.

An uncatchable interruption can leave sibling ``.rag-output-*.tmp`` files.
After stopping all writers for an output directory, an operator may remove
files matching that glob. Never sweep while writers are active: their live
staging files share the same prefix. Each final file is replaced independently;
this does not make a set of body/sidecar files one atomic transaction.
"""

import logging
import os
import secrets
import stat
from collections.abc import Callable
from pathlib import Path


def _create_temporary_path(destination: Path) -> Path:
    for _ in range(100):
        temporary_path = destination.with_name(
            f".rag-output-{secrets.token_hex(16)}.tmp"
        )
        try:
            with temporary_path.open("x", encoding="utf-8"):
                pass
        except FileExistsError:
            continue
        return temporary_path

    raise FileExistsError(f"Could not allocate a temporary file beside {destination}")


def atomic_write(path: Path, write_temporary: Callable[[Path], None]) -> Path:
    """Write a sibling temporary file, then atomically replace ``path``."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    directory_fd: int | None = None

    try:
        temporary_path = _create_temporary_path(destination)
        write_temporary(temporary_path)
        try:
            destination_mode = stat.S_IMODE(destination.stat().st_mode) & 0o777
        except FileNotFoundError:
            destination_mode = None

        # The callback has closed its writer; persist content and mode before
        # publishing it. On POSIX also persist the temporary directory entry,
        # then the rename itself. Pre-publication sync errors fail the write.
        # Open for writing before applying a possibly read-only destination mode;
        # Windows FlushFileBuffers requires a handle with write access.
        with temporary_path.open("r+b") as handle:
            if destination_mode is not None:
                os.chmod(temporary_path, destination_mode)
            os.fsync(handle.fileno())
        if os.name == "posix":
            directory_fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
            os.fsync(directory_fd)
        os.replace(temporary_path, destination)
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            except OSError as exc:
                # The path is already published. Report reduced durability without
                # misreporting a failed acquisition that callers might replay.
                logging.getLogger(__name__).warning(
                    "Published %s, but directory fsync failed: %s", destination, exc
                )
        return destination
    finally:
        if directory_fd is not None:
            os.close(directory_fd)
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> Path:
    """Atomically replace a text file with ``content``."""

    def write_temporary(temporary_path: Path) -> None:
        temporary_path.write_text(content, encoding=encoding)

    return atomic_write(path, write_temporary)
