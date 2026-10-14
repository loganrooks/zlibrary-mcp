"""Regression tests for deterministic, collision-resistant RAG output files."""

import hashlib
import logging
import os
import stat
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import lib.rag.orchestrator as rag_orchestrator
from filename_utils import create_unified_filename
from lib.rag.pipeline.models import DocumentOutput
from lib.rag.orchestrator_pdf import process_pdf_structured
from lib.rag.utils.atomic_write import atomic_write, atomic_write_text
from lib.rag.utils.exceptions import FileSaveError


@pytest.mark.asyncio
async def test_no_book_details_outputs_are_unique_stable_and_absolute(
    tmp_path, monkeypatch
):
    inputs = tmp_path / "inputs"
    (inputs / "a").mkdir(parents=True)
    (inputs / "b").mkdir()
    sources = {
        inputs / "Платон.txt": "Plato source",
        inputs / "Аристотель.txt": "Aristotle source",
        inputs / "a" / "notes.txt": "Notes from A",
        inputs / "b" / "notes.txt": "Notes from B",
    }
    for source, content in sources.items():
        source.write_text(content, encoding="utf-8")

    working_dir = tmp_path / "working"
    working_dir.mkdir()
    monkeypatch.chdir(working_dir)
    monkeypatch.setattr(rag_orchestrator, "PROCESSED_OUTPUT_DIR", Path("processed"))
    replacements = []
    original_replace = os.replace

    def record_replace(source, target):
        source_path = Path(source)
        target_path = Path(target)
        assert source_path.parent == target_path.parent
        replacements.append(target_path)
        return original_replace(source, target)

    monkeypatch.setattr(os, "replace", record_replace)

    results = {}
    for source in sources:
        results[source] = await rag_orchestrator.process_document(str(source))

    paths = [Path(result["processed_file_path"]) for result in results.values()]
    assert all(path.is_absolute() for path in paths)
    assert len({path.name for path in paths}) == len(sources)
    for source, result in results.items():
        path = Path(result["processed_file_path"])
        slug = "notes" if source.stem == "notes" else "doc"
        digest = hashlib.sha256(str(source.resolve()).encode("utf-8")).hexdigest()[:8]
        assert path.name == f"{slug}-{digest}.txt.processed.txt"
    for source, content in sources.items():
        assert content in Path(results[source]["processed_file_path"]).read_text(
            encoding="utf-8"
        )

    repeated_source = inputs / "a" / "notes.txt"
    first_path = results[repeated_source]["processed_file_path"]
    repeated_source.write_text("Updated notes from A", encoding="utf-8")
    repeated = await rag_orchestrator.process_document(str(repeated_source))

    assert repeated["processed_file_path"] == first_path
    assert "Updated notes from A" in Path(first_path).read_text(encoding="utf-8")
    expected_targets = {
        Path(path)
        for result in [*results.values(), repeated]
        for path in (result["processed_file_path"], result["metadata_file_path"])
    }
    assert set(replacements) == expected_targets


@pytest.mark.asyncio
async def test_book_details_keep_existing_filename_shape(tmp_path, monkeypatch):
    output_dir = tmp_path / "processed"
    monkeypatch.setattr(rag_orchestrator, "PROCESSED_OUTPUT_DIR", output_dir)
    source = tmp_path / "source.txt"
    source.write_text("source", encoding="utf-8")
    details = {"author": "Jane Doe", "title": "A Latin Title", "id": "12345"}

    result = await rag_orchestrator.process_document(str(source), book_details=details)

    expected_name = (
        f"{create_unified_filename(details, extension=None)}.txt.processed.txt"
    )
    assert Path(result["processed_file_path"]).name == expected_name


@pytest.mark.integration
def test_real_pdf_output_files_use_sibling_atomic_replacements(
    tmp_path, monkeypatch, lfs_fixture
):
    pdf_candidates = (
        PROJECT_ROOT / "test_files" / "heidegger_pages_22-23_primary_footnote_test.pdf",
        PROJECT_ROOT / "test_files" / "derrida_footnote_pages_120_125.pdf",
    )
    pdf = next((path for path in pdf_candidates if path.exists()), None)
    if pdf is None:
        pytest.skip("No real PDF fixture available")
    lfs_fixture(pdf)  # require_real_fixture: missing/LFS pointer fixtures skip.
    document = process_pdf_structured(pdf, output_format="markdown")
    replacements = []
    original_replace = os.replace

    def record_replace(source, target):
        source_path = Path(source)
        target_path = Path(target)
        assert source_path.parent == target_path.parent
        assert source_path.exists()
        replacements.append(target_path)
        return original_replace(source, target)

    monkeypatch.setattr(os, "replace", record_replace)
    written = document.write_files(tmp_path / pdf.name)

    assert written["body"].read_text(encoding="utf-8") == document.body_text
    assert written["metadata"].is_file()
    assert set(replacements) == {path for path in written.values()}
    assert all(path.parent == tmp_path for path in replacements)
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted(
        path.name for path in written.values()
    )


def test_footnote_replace_failure_preserves_old_file_and_cleans_temp(
    tmp_path, monkeypatch
):
    body_path = tmp_path / "book.processed.markdown"
    footnote_path = tmp_path / "book.processed_footnotes.markdown"
    body_path.write_text("old body", encoding="utf-8")
    footnote_path.write_text("old footnotes", encoding="utf-8")
    document = DocumentOutput(body_text="new body", footnotes="new footnotes")
    original_replace = os.replace

    def fail_footnote_replace(source, target):
        if Path(target) == footnote_path:
            raise OSError("simulated replacement failure")
        return original_replace(source, target)

    monkeypatch.setattr(os, "replace", fail_footnote_replace)

    with pytest.raises(OSError, match="simulated replacement failure"):
        document.write_files(body_path)

    assert body_path.read_text(encoding="utf-8") == "new body"
    assert footnote_path.read_text(encoding="utf-8") == "old footnotes"
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted(
        [body_path.name, footnote_path.name]
    )


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission modes are unavailable")
def test_atomic_writes_preserve_existing_mode_and_keep_new_files_private(tmp_path):
    regular_path = tmp_path / "regular.txt"
    regular_path.write_text("regular", encoding="utf-8")

    existing_path = tmp_path / "existing.txt"
    existing_path.write_text("old", encoding="utf-8")
    os.chmod(existing_path, 0o640)
    atomic_write_text(existing_path, "new")

    new_path = tmp_path / "new.txt"
    atomic_write_text(new_path, "new")

    assert stat.S_IMODE(existing_path.stat().st_mode) == 0o640
    assert stat.S_IMODE(new_path.stat().st_mode) == 0o600


def test_concurrent_atomic_writes_leave_one_complete_last_write(tmp_path):
    destination = tmp_path / "shared.txt"
    contents = ("first" * 100_000, "second" * 100_000)
    start_together = threading.Barrier(len(contents))

    def write(content):
        start_together.wait()
        atomic_write_text(destination, content)

    with ThreadPoolExecutor(max_workers=len(contents)) as executor:
        futures = [executor.submit(write, content) for content in contents]
        for future in futures:
            future.result()

    assert destination.read_text(encoding="utf-8") in contents
    assert sorted(path.name for path in tmp_path.iterdir()) == [destination.name]


@pytest.mark.skipif(os.name == "nt", reason="Directory fsync is POSIX-only")
def test_atomic_write_syncs_file_and_directory_around_replacement(
    tmp_path, monkeypatch
):
    events = []
    original_fsync = os.fsync
    original_replace = os.replace

    def record_fsync(fd):
        events.append("directory" if stat.S_ISDIR(os.fstat(fd).st_mode) else "file")
        original_fsync(fd)

    def record_replace(source, target):
        events.append("replace")
        original_replace(source, target)

    monkeypatch.setattr(os, "fsync", record_fsync)
    monkeypatch.setattr(os, "replace", record_replace)
    destination = tmp_path / "durable.txt"
    atomic_write_text(destination, "complete")
    assert destination.read_text(encoding="utf-8") == "complete"
    assert events == ["file", "directory", "replace", "directory"]


def test_file_sync_failure_keeps_previous_output_and_cleans_temp(tmp_path, monkeypatch):
    destination = tmp_path / "book.txt"
    destination.write_text("old", encoding="utf-8")

    def fail_sync(_fd):
        raise OSError("simulated sync failure")

    monkeypatch.setattr(os, "fsync", fail_sync)
    with pytest.raises(OSError, match="simulated sync failure"):
        atomic_write_text(destination, "new")
    assert destination.read_text(encoding="utf-8") == "old"
    assert list(tmp_path.glob(".rag-output-*.tmp")) == []


def test_interrupted_writer_leaves_only_documented_sweepable_temporary(tmp_path):
    destination = tmp_path / "book.txt"
    destination.write_text("old", encoding="utf-8")
    script = (
        "import os\nfrom lib.rag.utils.atomic_write import atomic_write\n"
        "from pathlib import Path\n"
        "def interrupted(path):\n"
        "    path.write_text('partial', encoding='utf-8')\n"
        "    os._exit(23)\n"
        f"atomic_write(Path({str(destination)!r}), interrupted)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=PROJECT_ROOT, timeout=10
    )
    assert result.returncode == 23
    assert destination.read_text(encoding="utf-8") == "old"
    leftovers = list(tmp_path.glob(".rag-output-*.tmp"))
    assert len(leftovers) == 1
    # The writer has exited: an operator can now sweep the documented glob.
    for leftover in leftovers:
        leftover.unlink()
    assert list(tmp_path.iterdir()) == [destination]


@pytest.mark.skipif(os.name == "nt", reason="Directory fsync is POSIX-only")
def test_post_replace_directory_sync_failure_reports_warning_and_published_path(
    tmp_path, monkeypatch, caplog
):
    destination = tmp_path / "published.txt"
    destination.write_text("old", encoding="utf-8")
    original_fsync = os.fsync
    directory_syncs = 0

    def fail_after_publish(fd):
        nonlocal directory_syncs
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            directory_syncs += 1
            if directory_syncs == 2:
                raise OSError("simulated post-publication sync failure")
        original_fsync(fd)

    monkeypatch.setattr(os, "fsync", fail_after_publish)
    with caplog.at_level(logging.WARNING):
        result = atomic_write_text(destination, "new")
    assert result == destination
    assert destination.read_text(encoding="utf-8") == "new"
    assert "simulated post-publication sync failure" in caplog.text
    assert str(destination) in caplog.text
    assert list(tmp_path.glob(".rag-output-*.tmp")) == []


@pytest.mark.parametrize("destination_mode", [0o640, 0o444])
def test_file_sync_uses_writable_descriptor_before_preserving_mode(
    tmp_path, monkeypatch, destination_mode
):
    destination = tmp_path / "writable-sync.txt"
    destination.write_text("old", encoding="utf-8")
    if os.name == "posix":
        os.chmod(destination, destination_mode)
    original_fsync = os.fsync
    writable_file_syncs = []

    def require_write_access(fd):
        if stat.S_ISREG(os.fstat(fd).st_mode):
            # A zero-byte write leaves content unchanged but rejects a read-only fd.
            assert os.write(fd, b"") == 0
            writable_file_syncs.append(fd)
        original_fsync(fd)

    monkeypatch.setattr(os, "fsync", require_write_access)
    assert atomic_write_text(destination, "new") == destination
    assert destination.read_text(encoding="utf-8") == "new"
    assert len(writable_file_syncs) == 1
    if os.name == "posix":
        assert stat.S_IMODE(destination.stat().st_mode) == destination_mode


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits")
def test_staging_is_private_before_and_during_callback(tmp_path):
    destination = tmp_path / "restricted.txt"
    destination.write_text("old", encoding="utf-8")
    destination.chmod(0o640)

    def write(path):
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        path.write_text("private document", encoding="utf-8")
        assert stat.S_IMODE(path.stat().st_mode) == 0o600

    previous_umask = os.umask(0o022)
    try:
        atomic_write(destination, write)
    finally:
        os.umask(previous_umask)
    assert destination.read_text(encoding="utf-8") == "private document"
    assert stat.S_IMODE(destination.stat().st_mode) == 0o640


@pytest.mark.asyncio
@pytest.mark.parametrize("output_format", ["../../escaped", "txt/../../escaped", "TXT", ""])
async def test_output_format_rejected_before_any_output_write(
    tmp_path, monkeypatch, output_format
):
    output_dir = tmp_path / "processed"
    monkeypatch.setattr(rag_orchestrator, "PROCESSED_OUTPUT_DIR", output_dir)
    with pytest.raises(FileSaveError, match="Unsupported output format"):
        await rag_orchestrator.save_processed_text(
            tmp_path / "source.txt", "content", output_format=output_format
        )
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_resolved_output_symlink_cannot_escape_output_directory(tmp_path, monkeypatch):
    output_dir = tmp_path / "processed"
    output_dir.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("untouched", encoding="utf-8")
    source = tmp_path / "source.txt"
    digest = hashlib.sha256(str(source.resolve()).encode("utf-8")).hexdigest()[:8]
    (output_dir / f"source-{digest}.txt.processed.txt").symlink_to(outside)
    monkeypatch.setattr(rag_orchestrator, "PROCESSED_OUTPUT_DIR", output_dir)
    with pytest.raises(FileSaveError, match="outside the output directory"):
        await rag_orchestrator.save_processed_text(source, "replacement")
    assert outside.read_text(encoding="utf-8") == "untouched"


@pytest.mark.asyncio
@pytest.mark.parametrize("stem_length", [229, 237])
@pytest.mark.parametrize("output_format", ["txt", "markdown"])
async def test_long_source_names_reserve_digest_and_sidecar_space(
    tmp_path, monkeypatch, stem_length, output_format
):
    source = tmp_path / ("a" * stem_length + ".txt")
    source.write_text("source content", encoding="utf-8")
    output_dir = tmp_path / "processed"
    monkeypatch.setattr(rag_orchestrator, "PROCESSED_OUTPUT_DIR", output_dir)
    result = await rag_orchestrator.process_document(str(source), output_format)
    digest = hashlib.sha256(str(source.resolve()).encode("utf-8")).hexdigest()[:8]
    path = Path(result["processed_file_path"])
    assert path.name.endswith(f"-{digest}.txt.processed.{output_format}")
    assert len(os.fsencode(path.name)) <= 200
    assert "source content" in path.read_text(encoding="utf-8")
    assert Path(result["metadata_file_path"]).is_file()
