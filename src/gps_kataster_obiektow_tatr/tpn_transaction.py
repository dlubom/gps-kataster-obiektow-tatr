"""Publish an entire data tree with one atomic directory exchange.

The exchange is the commit point: failures/crashes before it retain the old
catalog AND state; after it both are new. No multi-file rollback window.
"""

from __future__ import annotations

import ctypes
import fcntl
import os
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

from .tpn_api import require
from .tpn_snapshot import sha256


def tree_hashes(path: Path) -> dict:
    require(path.resolve() == path and path.is_dir(), "unsafe/missing data tree")
    result = {}
    for p in sorted(path.rglob("*")):
        require(not p.is_symlink(), "symlink in transaction tree")
        if p.is_dir():
            continue
        require(p.is_file(), "nonregular transaction file")
        result[p.relative_to(path).as_posix()] = sha256(p.read_bytes())
    return result


@contextmanager
def batch_lock(root: Path):
    # Lock survives atomic data replacement; flock is released even on SIGKILL.
    folder = root / "build"
    require(not folder.is_symlink(), "unsafe lock directory")
    folder.mkdir(exist_ok=True)
    path = folder / ".tpn-sync.lock"
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


def exchange_directories(left: Path, right: Path) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    a, b = os.fsencode(left), os.fsencode(right)
    if sys.platform == "darwin":
        result = libc.renamex_np(ctypes.c_char_p(a), ctypes.c_char_p(b), ctypes.c_uint(2))
    elif sys.platform.startswith("linux") and hasattr(libc, "renameat2"):
        result = libc.renameat2(-100, ctypes.c_char_p(a), -100, ctypes.c_char_p(b), 2)
    else:
        raise OSError("atomic directory exchange unavailable; no data written")
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def sync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def publish_tree(root: Path, files: dict[str, bytes], expected: dict, precommit=None) -> None:
    """Caller holds batch_lock and has completed semantic preflight."""
    require(tree_hashes(root / "data") == expected, "data changed before transaction")
    work = Path(tempfile.mkdtemp(prefix=".tpn-transaction-", dir=root / "build"))
    staged = work / "data"
    try:
        shutil.copytree(root / "data", staged)
        for relative, payload in files.items():
            require(
                relative.startswith("data/") and ".." not in Path(relative).parts,
                "unsafe transaction output",
            )
            path = staged / relative.removeprefix("data/")
            path.parent.mkdir(parents=True, exist_ok=True)
            if payload is None:
                path.unlink(missing_ok=True)
            else:
                with path.open("wb") as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
                require(path.read_bytes() == payload, "transaction readback mismatch")
        wanted = dict(expected)
        for path, raw in files.items():
            key = path.removeprefix("data/")
            if raw is None:
                wanted.pop(key, None)
            else:
                wanted[key] = sha256(raw)
        require(tree_hashes(staged) == wanted, "staged tree mismatch")
        # fsync copied files too: snapshots and previous decisions are durable evidence.
        for path in staged.rglob("*"):
            if path.is_file():
                with path.open("rb") as stream:
                    os.fsync(stream.fileno())
        for path in sorted((p for p in staged.rglob("*") if p.is_dir()), reverse=True):
            sync_directory(path)
        sync_directory(staged)
        require(tree_hashes(root / "data") == expected, "data changed during preflight")
        if precommit is not None:
            precommit()
        exchange_directories(root / "data", staged)  # Single commit point; never roll back.
        # A crash here leaves a complete new data tree and an obsolete copy in build.
        # Cleanup failure must not misreport an already committed batch as uncommitted.
        try:
            sync_directory(root)
            sync_directory(work)
        except OSError:
            pass
    finally:
        shutil.rmtree(work, ignore_errors=True)
