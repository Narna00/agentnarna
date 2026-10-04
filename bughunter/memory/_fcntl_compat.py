"""Windows implementation of the tiny ``fcntl.flock`` subset we use.

Windows byte-range locks are not POSIX advisory locks and prevent this project
from reopening/rotating its own file.  A named kernel mutex keyed by the file's
resolved path gives the required cross-process serialization without locking
the file handle itself.
"""
from __future__ import annotations

import ctypes
import functools
import hashlib
import msvcrt
import os
import threading
from ctypes import wintypes

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
_kernel32.CreateMutexW.restype = wintypes.HANDLE
_kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
_kernel32.WaitForSingleObject.restype = wintypes.DWORD
_kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
_kernel32.ReleaseMutex.restype = wintypes.BOOL
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.CloseHandle.restype = wintypes.BOOL
_kernel32.GetFinalPathNameByHandleW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
_kernel32.GetFinalPathNameByHandleW.restype = wintypes.DWORD
_kernel32.CreateFileW.argtypes = [
    wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
    wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
]
_kernel32.CreateFileW.restype = wintypes.HANDLE

_INFINITE = 0xFFFFFFFF
_WAIT_OBJECT_0 = 0
_FILE_APPEND_DATA = 0x0004
_FILE_SHARE_READ = 0x00000001
_FILE_SHARE_WRITE = 0x00000002
_FILE_SHARE_DELETE = 0x00000004
_OPEN_ALWAYS = 4
_FILE_ATTRIBUTE_NORMAL = 0x00000080
_INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
_held: dict[int, int] = {}
_mutex_cache: dict[str, int] = {}
_guard = threading.Lock()


def _mutex_name(fd: int) -> str:
    os_handle = msvcrt.get_osfhandle(fd)
    buffer = ctypes.create_unicode_buffer(32768)
    length = _kernel32.GetFinalPathNameByHandleW(os_handle, buffer, len(buffer), 0)
    if 0 < length < len(buffer):
        identity = os.path.normcase(buffer.value)
    else:
        # Fallback remains stable enough within a process; the normal path call
        # succeeds for disk files used by the journals.
        identity = f"fd:{os.getpid()}:{fd}"
    digest = hashlib.sha256(identity.encode("utf-8", "surrogatepass")).hexdigest()
    return "Local\\agentnarna-file-" + digest


@functools.lru_cache(maxsize=512)
def _path_mutex_name(path: str | os.PathLike) -> str:
    identity = os.path.normcase(os.path.abspath(os.fspath(path)))
    digest = hashlib.sha256(identity.encode("utf-8", "surrogatepass")).hexdigest()
    return "Local\\agentnarna-file-" + digest


def acquire_path(path: str | os.PathLike) -> int:
    """Acquire the named mutex for a path without opening the data file."""
    name = _path_mutex_name(path)
    with _guard:
        handle = _mutex_cache.get(name)
        if not handle:
            handle = _kernel32.CreateMutexW(None, False, name)
            if not handle:
                raise OSError(ctypes.get_last_error(), "CreateMutexW failed")
            _mutex_cache[name] = handle
    result = _kernel32.WaitForSingleObject(handle, _INFINITE)
    if result != _WAIT_OBJECT_0:
        raise OSError(ctypes.get_last_error(), "WaitForSingleObject failed")
    return handle


def release_path(handle: int) -> None:
    if handle:
        _kernel32.ReleaseMutex(handle)


def open_shared_append_fd(path: str | os.PathLike) -> int:
    """Open an unbuffered append fd while permitting another writer to rotate it.

    The CRT ``os.open`` path does not request ``FILE_SHARE_DELETE``. Keeping
    such a descriptor open is fast, but prevents atomic rotation on Windows.
    This handle has append-only access and shares read/write/delete; callers
    can therefore retain it and compare its file identity with the live path
    after taking the path mutex.
    """
    handle = _kernel32.CreateFileW(
        os.path.abspath(os.fspath(path)),
        _FILE_APPEND_DATA,
        _FILE_SHARE_READ | _FILE_SHARE_WRITE | _FILE_SHARE_DELETE,
        None,
        _OPEN_ALWAYS,
        _FILE_ATTRIBUTE_NORMAL,
        None,
    )
    if handle == _INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return msvcrt.open_osfhandle(handle, os.O_APPEND | os.O_WRONLY)
    except Exception:
        _kernel32.CloseHandle(handle)
        raise


class _FcntlCompat:
    LOCK_EX = 2
    LOCK_UN = 8

    @staticmethod
    def flock(fd: int, operation: int) -> None:
        if operation == _FcntlCompat.LOCK_UN:
            with _guard:
                handle = _held.pop(fd, None)
            if handle:
                _kernel32.ReleaseMutex(handle)
            return

        name = _mutex_name(fd)
        with _guard:
            handle = _mutex_cache.get(name)
            if not handle:
                handle = _kernel32.CreateMutexW(None, False, name)
                if not handle:
                    raise OSError(ctypes.get_last_error(), "CreateMutexW failed")
                _mutex_cache[name] = handle
        result = _kernel32.WaitForSingleObject(handle, _INFINITE)
        if result != _WAIT_OBJECT_0:
            raise OSError(ctypes.get_last_error(), "WaitForSingleObject failed")
        with _guard:
            _held[fd] = handle


fcntl = _FcntlCompat()
