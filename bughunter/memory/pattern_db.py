"""
Pattern database — successful techniques indexed by vuln class + tech stack.

Patterns are stored in a JSONL file, one entry per line.
Matching supports partial tech stack overlap for cross-target learning.
"""

try:
    import fcntl
except ImportError:  # Windows
    from memory._fcntl_compat import fcntl
import json
import os
import sys
from pathlib import Path

from memory.rotation import DEFAULT_KEEP, DEFAULT_MAX_BYTES, rotate_if_needed
from memory.file_lock import exclusive_path_lock
from memory.schemas import validate_pattern_entry, SchemaError


class PatternDB:
    """Read/write/match successful hunt patterns."""

    def __init__(
        self,
        path: str | Path,
        max_bytes: int = DEFAULT_MAX_BYTES,
        keep_backups: int = DEFAULT_KEEP,
    ):
        """
        Args:
            path: Path to the patterns.jsonl file. Parent dirs are created if needed.
            max_bytes: Rotate the file when it exceeds this size.
            keep_backups: Number of rotated backups to retain.
        """
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max_bytes
        self.keep_backups = keep_backups
        try:
            self._approx_bytes = self.path.stat().st_size
        except FileNotFoundError:
            self._approx_bytes = 0
        self._append_fd: int | None = None
        # Dedup index of (target, vuln_class, technique) keys. Populated lazily
        # on first save() so re-opening an existing DB stays correct without
        # paying the read cost up-front. Cross-process dedup is best-effort:
        # two processes with independent instances can each pass the dedup
        # check before either writes. The cost is one wasted JSONL row.
        self._dedup_keys: set[tuple[str, str, str]] | None = None

    def _close_append_fd(self) -> None:
        if self._append_fd is not None:
            try:
                os.close(self._append_fd)
            finally:
                self._append_fd = None

    def close(self) -> None:
        """Release the cached Windows append handle, if one is open."""
        self._close_append_fd()

    def __del__(self):
        try:
            self._close_append_fd()
        except Exception:
            # Interpreter shutdown may already have torn down ``os``.
            pass

    def _windows_append_fd(self) -> int:
        """Return a live append fd, reopening after another process rotates."""
        if self._append_fd is not None:
            try:
                live = self.path.stat()
                opened = os.fstat(self._append_fd)
                if (live.st_dev, live.st_ino) != (opened.st_dev, opened.st_ino):
                    self._close_append_fd()
            except (FileNotFoundError, OSError):
                self._close_append_fd()

        if self._append_fd is None:
            from memory._fcntl_compat import open_shared_append_fd

            self._append_fd = open_shared_append_fd(self.path)
        return self._append_fd

    @staticmethod
    def _dedup_key(entry: dict) -> tuple[str, str, str]:
        return (entry.get("target", ""), entry.get("vuln_class", ""), entry.get("technique", ""))

    def _load_dedup_keys(self) -> set[tuple[str, str, str]]:
        """Build the dedup key set by streaming the file once.

        Skips corrupted lines silently — they cannot collide with a valid
        save, and ``read_all`` already warns about them.
        """
        keys: set[tuple[str, str, str]] = set()
        if not self.path.exists():
            return keys
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                keys.add(self._dedup_key(entry))
        return keys

    def save(self, entry: dict) -> bool:
        """Validate and save a pattern entry. Returns True if saved, False if duplicate.

        A duplicate is defined as same target + vuln_class + technique.
        """
        validated = validate_pattern_entry(entry)

        if self._dedup_keys is None:
            self._dedup_keys = self._load_dedup_keys()

        key = self._dedup_key(validated)
        if key in self._dedup_keys:
            return False

        line = json.dumps(validated, separators=(",", ":")) + "\n"
        encoded = line.encode("utf-8")

        with exclusive_path_lock(self.path):
            # Reconcile our fast local counter with the live file while under
            # the cross-process mutex. Another hunter process may have appended
            # since this instance was created.
            try:
                self._approx_bytes = self.path.stat().st_size
            except FileNotFoundError:
                self._approx_bytes = 0
            if self._approx_bytes >= self.max_bytes:
                self._close_append_fd()
                if rotate_if_needed(
                    self.path, max_bytes=self.max_bytes,
                    keep=self.keep_backups, already_locked=True,
                ):
                    self._approx_bytes = 0
            if os.name == "nt":
                fd = self._windows_append_fd()
                close_after_write = False
            else:
                fd = os.open(str(self.path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
                close_after_write = True
            try:
                written = os.write(fd, encoded)
                if written != len(encoded):
                    raise OSError(f"Partial write: {written}/{len(encoded)} bytes")
            finally:
                if close_after_write:
                    os.close(fd)

        self._dedup_keys.add(key)
        self._approx_bytes += len(encoded)
        return True

    def read_all(self, *, validate: bool = True) -> list[dict]:
        """Read all pattern entries. Corrupted lines are skipped with a warning."""
        if not self.path.exists():
            return []

        entries = []
        with open(self.path, "r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError as e:
                    print(
                        f"WARNING: {self.path} line {lineno} is corrupted "
                        f"(skipping): {e}",
                        file=sys.stderr,
                    )
                    continue

                if validate:
                    try:
                        validate_pattern_entry(entry)
                    except SchemaError as e:
                        print(
                            f"WARNING: {self.path} line {lineno} failed "
                            f"validation (skipping): {e}",
                            file=sys.stderr,
                        )
                        continue

                entries.append(entry)

        return entries

    def match(self, *, vuln_class: str | None = None,
              tech_stack: list[str] | None = None) -> list[dict]:
        """Find patterns matching vuln class and/or overlapping tech stack.

        Args:
            vuln_class: Exact match on vuln_class field.
            tech_stack: Partial overlap match — returns patterns where ANY tech in
                        the query overlaps with the pattern's tech_stack.

        Returns:
            Matching patterns sorted by payout (highest first), then recency.
        """
        patterns = self.read_all()

        if vuln_class is not None:
            patterns = [p for p in patterns if p.get("vuln_class") == vuln_class]

        if tech_stack is not None:
            query_set = {t.lower() for t in tech_stack}
            patterns = [
                p for p in patterns
                if query_set & {t.lower() for t in p.get("tech_stack", [])}
            ]

        # Sort: highest payout first, then most recent
        patterns.sort(
            key=lambda p: (p.get("payout", 0), p.get("ts", "")),
            reverse=True,
        )

        return patterns
