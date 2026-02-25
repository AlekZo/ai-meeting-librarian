"""
Utilities for safe JSON storage with atomic writes and lock files.
"""

from __future__ import annotations

import json
import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_LOCK_TIMEOUT = 10.0
DEFAULT_LOCK_POLL = 0.1


@contextmanager
def file_lock(lock_path: str, timeout: float = DEFAULT_LOCK_TIMEOUT, poll: float = DEFAULT_LOCK_POLL):
    """Simple cross-process lock using an exclusive lock file.

    Args:
        lock_path: Path to lock file.
        timeout: Max seconds to wait for lock.
        poll: Poll interval.
    """
    start = time.time()
    lock_fd = None
    while True:
        try:
            lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if (time.time() - start) >= timeout:
                raise TimeoutError(f"Timeout acquiring lock: {lock_path}")
            time.sleep(poll)

    try:
        yield
    finally:
        try:
            if lock_fd is not None:
                os.close(lock_fd)
            if os.path.exists(lock_path):
                os.remove(lock_path)
        except Exception as e:
            logger.warning(f"Failed to release lock {lock_path}: {e}")


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def atomic_write_json(path: str, data: Any, indent: int = 2, ensure_ascii: bool = False) -> None:
    """Atomically write JSON to a file.

    Uses a temp file in the same directory and os.replace for atomic swap.
    """
    _ensure_parent_dir(path)
    temp_path = f"{path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_path, path)


def load_json(path: str, default: Any) -> Any:
    """Load JSON from file or return default on error."""
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON from {path}: {e}")
        return default


def locked_load_json(path: str, default: Any, timeout: float = DEFAULT_LOCK_TIMEOUT) -> Any:
    """Load JSON waiting for any active writer lock to clear."""
    lock_path = f"{path}.lock"
    start = time.time()
    while os.path.exists(lock_path):
        if (time.time() - start) >= timeout:
            logger.warning(f"Timeout waiting for lock to clear: {lock_path}")
            break
        time.sleep(DEFAULT_LOCK_POLL)
    return load_json(path, default)


def locked_save_json(path: str, data: Any, indent: int = 2, ensure_ascii: bool = False) -> None:
    """Write JSON with a lock and atomic replace."""
    lock_path = f"{path}.lock"
    _ensure_parent_dir(path)
    with file_lock(lock_path):
        atomic_write_json(path, data, indent=indent, ensure_ascii=ensure_ascii)
