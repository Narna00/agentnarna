"""
Size-based JSONL rotation for hunt memory files.

Append-only logs (audit.jsonl, patterns.jsonl, journal.jsonl) grow without bound
on active hunters. This module rotates them at a configurable size cap, keeping
N backups (file.1, file.2, ...) and dropping the oldest.

Rotation is performed under fcntl.LOCK_EX to be safe with concurrent writers.
"""

try:
    import fcntl
    _WINDOWS_COMPAT = False
except ImportError:  # Windows
    from memory._fcntl_compat import fcntl
    _WINDOWS_COMPAT = True
import os
from pathlib import Path

from memory.file_lock import exclusive_path_lock

DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
DEFAULT_KEEP = 3


def needs_rotation(path: Path, max_bytes: int) -> bool:
    """Return True if the file exists and exceeds max_bytes."""
    try:
        return path.stat().st_size >= max_bytes
    except FileNotFoundError:
        return False


def rotate(path: Path, keep: int = DEFAULT_KEEP) -> int:
    """Rotate ``path`` → ``path.1``, shifting older backups up by one.

    The oldest backup beyond ``keep`` is dropped. If ``path`` does not exist,
    this is a no-op. Returns the number of files rotated (including the drop).

    Caller should hold an exclusive lock on ``path`` (or a sibling) to avoid
    racing with concurrent writers.
    """
    if not path.exists():
        return 0

    # Drop the oldest: path.{keep} is removed if present
    oldest = path.with_suffix(path.suffix + f".{keep}")
    if oldest.exists():
        try:
            oldest.unlink()
        except OSError as e:
            raise OSError(f"Failed to remove oldest backup {oldest}: {e}") from e

    # Shift path.{i} → path.{i+1} for i from keep-1 down to 1
    for i in range(keep - 1, 0, -1):
        src = path.with_suffix(path.suffix + f".{i}")
        dst = path.with_suffix(path.suffix + f".{i + 1}")
        if src.exists():
            try:
                os.replace(str(src), str(dst))
            except OSError as e:
                raise OSError(f"Failed to shift backup {src} → {dst}: {e}") from e

    # Move the live file to .1
    first_backup = path.with_suffix(path.suffix + ".1")
    try:
        os.replace(str(path), str(first_backup))
    except OSError as e:
        raise OSError(f"Failed to rotate {path} → {first_backup}: {e}") from e
    return 1


def rotate_if_needed(
    path: Path,
    max_bytes: int = DEFAULT_MAX_BYTES,
    keep: int = DEFAULT_KEEP,
    *,
    already_locked: bool = False,
) -> bool:
    """Rotate ``path`` under an exclusive lock if it exceeds ``max_bytes``.

    Returns True if a rotation happened. This is safe to call from multiple
    processes — the second process to acquire the lock will observe the
    rotated file and become a no-op.
    """
    if not needs_rotation(path, max_bytes):
        return False

    if already_locked:
        if not needs_rotation(path, max_bytes):
            return False
        rotate(path, keep=keep)
        return True

    if _WINDOWS_COMPAT:
        with exclusive_path_lock(path):
            if not needs_rotation(path, max_bytes):
                return False
            rotate(path, keep=keep)
            return True

    with exclusive_path_lock(path):
        if not needs_rotation(path, max_bytes):
            return False
        rotate(path, keep=keep)
        return True


def list_backups(path: Path, keep: int = DEFAULT_KEEP) -> list[Path]:
    """Return existing backup paths for ``path``, ordered .1 → .keep."""
    out = []
    for i in range(1, keep + 1):
        bp = path.with_suffix(path.suffix + f".{i}")
        if bp.exists():
            out.append(bp)
    return out


def total_bytes(path: Path, keep: int = DEFAULT_KEEP) -> int:
    """Total bytes used by the live file plus all backups."""
    total = 0
    if path.exists():
        total += path.stat().st_size
    for bp in list_backups(path, keep=keep):
        total += bp.stat().st_size
    return total


def purge_backups(path: Path, keep: int = DEFAULT_KEEP) -> int:
    """Delete all backups for ``path``. Returns the number of files removed."""
    removed = 0
    for bp in list_backups(path, keep=keep):
        bp.unlink()
        removed += 1
    return removed
