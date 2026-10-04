"""Cross-platform path lock that does not keep the data file open."""
from __future__ import annotations

import contextlib
import os
from pathlib import Path


@contextlib.contextmanager
def exclusive_path_lock(path: str | os.PathLike):
    """Serialize writers/rotation for ``path`` across processes."""
    if os.name == "nt":
        from memory._fcntl_compat import acquire_path, release_path

        handle = acquire_path(path)
        try:
            yield
        finally:
            release_path(handle)
        return

    import fcntl

    lock_path = Path(str(path) + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
