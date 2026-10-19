"""Lease semantics: real POSIX processes; native Windows tests are explicitly scoped."""

import asyncio
import errno
import os
from pathlib import Path

import pytest
from lib import acquisition as acq


@pytest.mark.asyncio
async def test_unlink_failure_always_closes_the_held_descriptor(tmp_path, monkeypatch):
    target = tmp_path / "book.pdf"
    lock = Path(str(target) + ".lock")
    opened = []
    original_open, original_unlink = os.open, Path.unlink

    def track(path, *args, **kwargs):
        fd = original_open(path, *args, **kwargs)
        if Path(path) == lock:
            opened.append(fd)
        return fd

    def refuse(path, *args, **kwargs):
        if path == lock:
            raise PermissionError("synthetic unlink of open lock refused")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(acq.os, "open", track)
    monkeypatch.setattr(Path, "unlink", refuse)
    try:
        if os.name == "nt":
            async with acq.destination_lock(target, 1):
                pass  # persistent Windows backend must never unlink
        else:
            with pytest.raises((OSError, acq.AcquisitionError)):
                async with acq.destination_lock(target, 1):
                    pass
        assert opened
        for fd in opened:
            with pytest.raises(OSError) as error:
                os.fstat(fd)
            assert error.value.errno == errno.EBADF
    finally:
        for fd in opened:
            try:
                os.close(fd)
            except OSError:
                pass
        original_unlink(lock, missing_ok=True)


@pytest.mark.asyncio
async def test_missing_native_backend_fails_closed_before_entering_lease(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(acq, "fcntl", None)
    monkeypatch.setattr(acq, "msvcrt", None, raising=False)
    with pytest.raises(acq.AcquisitionError) as error:
        async with acq.destination_lock(tmp_path / "book.pdf", 0):
            pytest.fail("unsupported backend entered a lease")
    assert error.value.reason == "output_refused"
    assert error.value.issued is False
    assert not list(tmp_path.iterdir())


@pytest.mark.asyncio
async def test_active_holder_is_not_stolen_and_reacquires_after_release(tmp_path):
    target = tmp_path / "book.pdf"
    async with acq.destination_lock(target, 1):
        with pytest.raises(acq.AcquisitionError) as error:
            async with acq.destination_lock(target, 0):
                pytest.fail("active lease stolen")
        assert error.value.reason == "breaker_open"
        await asyncio.sleep(0)
    async with acq.destination_lock(target, 0):
        pass


@pytest.mark.skipif(os.name == "nt", reason="POSIX inode/stale-reaper contract")
def test_stale_reaper_does_not_delete_replacement_inode(tmp_path, monkeypatch):
    lock = tmp_path / "book.lock"
    lock.write_text('{"pid":123}')

    def replace(_pid):
        old = tmp_path / "old-lock"
        lock.rename(old)
        lock.write_text("replacement")
        return False

    monkeypatch.setattr(acq, "_alive", replace)
    acq._remove_stale(lock, 0)
    assert lock.read_text() == "replacement"


class WindowsLeaseEmulator:
    LK_NBLCK, LK_UNLCK = 2, 0

    def __init__(self):
        self.held = {}
        self.calls = []
        self.lock_error = self.unlock_error = None

    def locking(self, fd, mode, size):
        self.calls.append((os.lseek(fd, 0, os.SEEK_CUR), mode, size))
        st = os.fstat(fd)
        key = (st.st_dev, st.st_ino)
        if mode == self.LK_NBLCK:
            if self.lock_error:
                raise OSError(self.lock_error, "synthetic native lock failure")
            if key in self.held:
                raise OSError(errno.EACCES, "synthetic held byte range")
            self.held[key] = fd
        else:
            if self.unlock_error:
                raise OSError(self.unlock_error, "synthetic unlock failure")
            assert self.held.pop(key) == fd


@pytest.fixture
def windows_emulator(monkeypatch):
    backend = WindowsLeaseEmulator()
    monkeypatch.setattr(acq, "_WINDOWS", True)
    monkeypatch.setattr(acq, "msvcrt", backend)

    def forbidden(*args):
        pytest.fail("Windows lease used POSIX PID/stale-reaper logic")

    monkeypatch.setattr(acq, "_alive", forbidden)
    monkeypatch.setattr(acq, "_remove_stale", forbidden)
    return backend


def test_windows_emulator_persistent_fixed_offset_and_nonwaiting_exclusion(
    tmp_path, monkeypatch, windows_emulator
):
    target = tmp_path / "book.pdf"
    lock = Path(str(target) + ".lock")
    original = Path.unlink

    def no_unlink(path, *args, **kwargs):
        assert path != lock, "Windows persistent coordination file was unlinked"
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", no_unlink)
    with acq.DestinationLease(target, 0):
        with pytest.raises(acq.AcquisitionError) as error:
            with acq.DestinationLease(target, 0, issued=True):
                pytest.fail("held region acquired")
        assert error.value.to_dict() == {
            "reason": "breaker_open",
            "request_issued": True,
        }
    assert lock.exists() and lock.read_bytes() == b""
    with acq.DestinationLease(target, 0):
        pass
    assert all(offset == 0 and size == 1 for offset, _, size in windows_emulator.calls)
    assert not windows_emulator.held


@pytest.mark.parametrize("failure", [errno.EBADF, errno.ENOSYS, errno.EPERM, errno.EIO])
def test_windows_unexpected_lock_errors_fail_closed_not_busy(
    tmp_path, windows_emulator, failure
):
    windows_emulator.lock_error = failure
    lease = acq.DestinationLease(tmp_path / "book.pdf", 0)
    with pytest.raises(acq.AcquisitionError) as error:
        with lease:
            pytest.fail("failed backend entered")
    assert error.value.reason == "output_refused"
    assert lease.descriptor is None


def test_windows_unlock_failure_still_closes_fd(tmp_path, windows_emulator):
    lease = acq.DestinationLease(tmp_path / "book.pdf", 0)
    with pytest.raises(OSError):
        with lease:
            fd = lease.descriptor
            os.lseek(fd, 7, os.SEEK_SET)
            windows_emulator.unlock_error = errno.EIO
    with pytest.raises(OSError):
        os.fstat(fd)
    assert windows_emulator.calls[-1] == (0, windows_emulator.LK_UNLCK, 1)


def test_windows_open_permission_failure_is_not_contention(
    tmp_path, monkeypatch, windows_emulator
):
    def denied(*args, **kwargs):
        raise PermissionError(errno.EACCES, "synthetic open permission failure")

    monkeypatch.setattr(acq.os, "open", denied)
    with pytest.raises(acq.AcquisitionError) as error:
        with acq.DestinationLease(tmp_path / "book.pdf", 0):
            pytest.fail("permission failure entered")
    assert error.value.reason == "output_refused"
    assert not windows_emulator.calls


@pytest.mark.asyncio
async def test_native_backend_process_exclusion_death_and_reacquisition(
    tmp_path, monkeypatch
):
    import json
    import subprocess
    import sys
    import time

    helper = Path(__file__).with_name("acquisition_process_worker.py")
    child = subprocess.Popen(
        [
            sys.executable,
            "-B",
            str(helper),
            str(tmp_path),
            json.dumps({"lease_only": True}),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    target = tmp_path / "held.pdf"
    lock = Path(str(target) + ".lock")
    try:
        deadline = time.monotonic() + 7
        while not (tmp_path / "held").exists():
            assert time.monotonic() < deadline and child.poll() is None, (
                "lease worker did not become ready"
            )
            time.sleep(0.01)
        if os.name == "nt":

            def forbidden(*args):
                pytest.fail("native Windows invoked POSIX stale/PID logic")

            monkeypatch.setattr(acq, "_alive", forbidden)
            monkeypatch.setattr(acq, "_remove_stale", forbidden)
            assert lock.stat().st_size == 0
        with pytest.raises(acq.AcquisitionError) as error:
            async with acq.destination_lock(target, 0):
                pytest.fail("other process did not exclude acquisition")
        assert error.value.reason == "breaker_open"
        child.kill()
        child.communicate(timeout=5)
        # OS release after process death can be resource-delayed on Windows.
        # The active-holder refusal above remains strictly zero-budget.
        async with acq.destination_lock(target, 5):
            pass
        if os.name == "nt":
            assert lock.exists() and lock.read_bytes() == b""
        else:
            assert not lock.exists()
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=5)


@pytest.mark.skipif(
    os.name != "nt",
    reason="requires native Windows msvcrt runtime; emulator cannot qualify it",
)
def test_windows_native_backend_is_available():
    assert acq._WINDOWS and acq.msvcrt is not None


@pytest.mark.skipif(os.name == "nt", reason="POSIX creator/reaper actual-FD schedule")
def test_fresh_failed_creator_is_immediately_reclaimable_without_age_wait(
    tmp_path, monkeypatch
):
    target = tmp_path / "book.pdf"
    lock = Path(str(target) + ".lock")
    original = acq.fcntl.flock
    creator_fds = []

    def second_fd_wins(fd, mode):
        creator_fds.append(fd)
        other = os.open(lock, os.O_RDWR)
        try:
            original(other, acq.fcntl.LOCK_EX | acq.fcntl.LOCK_NB)
            return original(fd, mode)
        finally:
            os.close(other)

    with monkeypatch.context() as patch:
        patch.setattr(acq.fcntl, "flock", second_fd_wins)
        with pytest.raises(acq.AcquisitionError) as error:
            with acq.DestinationLease(target, 600):
                pytest.fail("creator entered while the second FD held its inode")
        assert error.value.to_dict() == {
            "reason": "breaker_open",
            "request_issued": False,
        }
    assert lock.read_bytes() == b""  # failed-flock cleanup must not unlink
    with pytest.raises(OSError):
        os.fstat(creator_fds[0])
    with acq.DestinationLease(target, 600):
        pass  # no mtime manipulation or full-budget stale wait


@pytest.mark.skipif(os.name == "nt", reason="POSIX creator/reaper actual-FD schedule")
@pytest.mark.parametrize("replace", [False, True])
@pytest.mark.parametrize("issued", [False, True])
def test_detached_creator_refuses_before_metadata_and_preserves_replacement(
    tmp_path, monkeypatch, replace, issued
):
    target = tmp_path / "book.pdf"
    lock = Path(str(target) + ".lock")
    original = acq.fcntl.flock
    replacement = []
    old = []
    metadata = []

    def detach(fd, mode):
        if not old:
            old.append(fd)
            # A real second FD reaps under flock, not an unconditional test unlink.
            acq._remove_stale(lock, 0)
            assert not lock.exists()
            if replace:
                holder = acq.DestinationLease(target, 600).__enter__()
                replacement.append((holder, lock.read_bytes(), lock.stat()))
        return original(fd, mode)

    write = os.write

    def observe_metadata(fd, data):
        if old and fd == old[0]:
            metadata.append(data)
        return write(fd, data)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(acq.fcntl, "flock", detach)
            patch.setattr(acq.os, "write", observe_metadata)
            with pytest.raises(acq.AcquisitionError) as error:
                with acq.DestinationLease(target, 600, issued=issued):
                    pytest.fail(
                        "detached creator admitted without current pathname ownership"
                    )
            assert error.value.to_dict() == {
                "reason": "breaker_open",
                "request_issued": issued,
            }
        assert metadata == []
        with pytest.raises(OSError):
            os.fstat(old[0])
        if replace:
            holder, contents, stat = replacement[0]
            assert lock.read_bytes() == contents
            assert (lock.stat().st_dev, lock.stat().st_ino) == (
                stat.st_dev,
                stat.st_ino,
            )
            assert holder.held
            with pytest.raises(acq.AcquisitionError):
                with acq.DestinationLease(target, 0):
                    pytest.fail("replacement OS lease was lost")
        else:
            assert not lock.exists()
    finally:
        for holder, _, _ in replacement:
            holder.close()


@pytest.mark.skipif(os.name == "nt", reason="POSIX stale metadata policy")
@pytest.mark.parametrize(
    "raw",
    [
        "",
        "[1]",
        "null",
        "true",
        "1",
        '"scalar"',
        "{bad",
        "{}",
        '{"pid":true}',
        '{"pid":false}',
        '{"pid":0}',
        '{"pid":-1}',
        '{"pid":"123"}',
        '{"pid":1.5}',
    ],
)
def test_unlocked_inode_without_usable_pid_is_immediately_reclaimed(
    tmp_path, monkeypatch, raw
):
    lock = tmp_path / "book.lock"
    lock.write_text(raw)
    monkeypatch.setattr(
        acq, "_alive", lambda _: pytest.fail("invalid PID reached OS liveness check")
    )
    acq._remove_stale(lock, 600)
    assert not lock.exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX stale metadata policy")
def test_valid_dead_pid_is_reclaimed_but_live_pid_without_flock_is_conservative(
    tmp_path, monkeypatch
):
    import json

    lock = tmp_path / "book.lock"
    lock.write_text(json.dumps({"pid": os.getpid()}))
    acq._remove_stale(lock, 0)
    assert lock.exists()  # no flock holder, but valid live PID remains conservative
    monkeypatch.setattr(acq, "_alive", lambda pid: False)
    acq._remove_stale(lock, 600)
    assert not lock.exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX active empty inode lease")
@pytest.mark.parametrize("aged", [False, True])
def test_active_flock_protects_empty_inode_regardless_of_age(tmp_path, aged):
    lock = tmp_path / "book.lock"
    lock.touch()
    if aged:
        os.utime(lock, (1, 1))
    fd = os.open(lock, os.O_RDWR)
    try:
        acq.fcntl.flock(fd, acq.fcntl.LOCK_EX | acq.fcntl.LOCK_NB)
        before = lock.stat()
        acq._remove_stale(lock, 0)
        assert lock.read_bytes() == b""
        assert (lock.stat().st_dev, lock.stat().st_ino) == (
            before.st_dev,
            before.st_ino,
        )
    finally:
        os.close(fd)


@pytest.mark.skipif(
    os.name == "nt", reason="POSIX actual-process detached creator schedule"
)
def test_process_creator_cannot_overlap_admitted_replacement(tmp_path):
    import json
    import subprocess
    import sys
    import time

    child = subprocess.Popen(
        [
            sys.executable,
            "-B",
            str(Path(__file__).with_name("acquisition_process_worker.py")),
            str(tmp_path),
            json.dumps({"paused_creator": True}),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    target = tmp_path / "book.pdf"
    lock = Path(str(target) + ".lock")
    try:
        deadline = time.monotonic() + 7
        while not (tmp_path / "created").exists():
            assert time.monotonic() < deadline and child.poll() is None, (
                "creator never reached barrier"
            )
            time.sleep(0.01)
        os.utime(
            lock, (1, 1)
        )  # schedule a delayed creator; separate control covers fresh immediate reap
        acq._remove_stale(lock, 600)
        assert not lock.exists()
        with acq.DestinationLease(target, 600) as holder:
            before = lock.read_bytes(), lock.stat()
            (tmp_path / "resume").touch()
            out, err = child.communicate(timeout=7)
            assert child.returncode == 0, err[-600:]
            assert json.loads(out) == {
                "status": "refused",
                "reason": "breaker_open",
                "request_issued": True,
                "old_fd_closed": True,
            }
            assert not (tmp_path / "admitted").exists()
            assert holder.held
            assert lock.read_bytes() == before[0]
            assert (lock.stat().st_dev, lock.stat().st_ino) == (
                before[1].st_dev,
                before[1].st_ino,
            )
            with pytest.raises(acq.AcquisitionError):
                with acq.DestinationLease(target, 0):
                    pytest.fail("replacement lease lost while child resumed")
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=5)


@pytest.mark.skipif(os.name == "nt", reason="POSIX lock metadata failure cleanup")
@pytest.mark.parametrize("operation", ["write", "fsync"])
def test_posix_metadata_failure_closes_fd_and_releases_inode(
    tmp_path, monkeypatch, operation
):
    target = tmp_path / "book.pdf"
    lease = acq.DestinationLease(target, 600)
    descriptors = []

    def fail(fd, *args):
        descriptors.append(fd)
        raise OSError(errno.EIO, "synthetic metadata failure")

    with monkeypatch.context() as patch:
        patch.setattr(acq.os, operation, fail)
        with pytest.raises(acq.AcquisitionError) as error:
            with lease:
                pytest.fail("metadata failure admitted creator")
        assert error.value.reason == "output_refused"
    assert descriptors and lease.descriptor is None
    for fd in descriptors:
        with pytest.raises(OSError):
            os.fstat(fd)
    with acq.DestinationLease(target, 600):
        pass
