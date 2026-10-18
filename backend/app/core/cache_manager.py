from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path

DEFAULT_MAX_BYTES = 1024 * 1024 * 1024


class CacheError(Exception):
    """Base cache exception."""


class CacheCapacityError(CacheError):
    """The configured cache limit cannot accommodate an entry."""


class DiskCache:
    """Bounded, checksum-verified disk cache for application data."""

    def __init__(self, root: str | Path, max_bytes: int = DEFAULT_MAX_BYTES):
        if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes <= 0:
            raise ValueError("max_bytes must be a positive integer")
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max_bytes
        self._lock = threading.RLock()
        self._active: dict[str, int] = {}

    @staticmethod
    def _digest(key: str) -> str:
        if not isinstance(key, str) or not key.strip():
            raise ValueError("Cache key must be a non-empty string")
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def _paths(self, key: str) -> tuple[Path, Path]:
        digest = self._digest(key)
        return self.root / f"{digest}.bin", self.root / f"{digest}.json"

    def _remove(self, digest: str) -> None:
        (self.root / f"{digest}.bin").unlink(missing_ok=True)
        (self.root / f"{digest}.json").unlink(missing_ok=True)

    def _metadata(self, path: Path) -> dict | None:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                return None
            if not isinstance(value.get("key"), str):
                return None
            if not isinstance(value.get("size"), int) or value["size"] < 0:
                return None
            if not isinstance(value.get("sha256"), str):
                return None
            return value
        except (OSError, ValueError, TypeError):
            return None

    def _entries(self) -> list[dict]:
        result = []
        for path in self.root.glob("*.json"):
            digest = path.stem
            meta = self._metadata(path)
            data_path = self.root / f"{digest}.bin"
            if meta is None or self._digest(meta["key"]) != digest:
                self._remove(digest)
                continue
            try:
                if not data_path.is_file() or data_path.stat().st_size != meta["size"]:
                    self._remove(digest)
                    continue
            except OSError:
                continue
            result.append(meta)
        return result

    def get(self, key: str) -> bytes | None:
        data_path, meta_path = self._paths(key)
        with self._lock:
            meta = self._metadata(meta_path)
            if meta is None or meta["key"] != key:
                return None
            try:
                data = data_path.read_bytes()
            except OSError:
                return None
            if len(data) != meta["size"] or hashlib.sha256(data).hexdigest() != meta["sha256"]:
                self._remove(data_path.stem)
                return None
            meta["accessed_at"] = time.time()
            self._atomic_json(meta_path, meta)
            return data

    def _atomic_json(self, path: Path, value: dict) -> None:
        fd, temporary = tempfile.mkstemp(prefix=".cache-", dir=self.root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(value, handle, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _atomic_bytes(self, path: Path, data: bytes) -> None:
        fd, temporary = tempfile.mkstemp(prefix=".cache-", dir=self.root)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def put(self, key: str, data: bytes, category: str = "metadata") -> None:
        if not isinstance(data, bytes):
            raise TypeError("Cache data must be bytes")
        if not isinstance(category, str) or not category.strip():
            raise ValueError("Category must be non-empty")
        if len(data) > self.max_bytes:
            raise CacheCapacityError("Entry exceeds cache capacity")

        data_path, meta_path = self._paths(key)
        digest = data_path.stem
        with self._lock:
            if self._active.get(digest, 0):
                raise CacheError("Cannot replace an active entry")

            entries = self._entries()
            existing = next((e for e in entries if e["key"] == key), None)
            total = sum(e["size"] for e in entries)
            available = self.max_bytes - (total - (existing["size"] if existing else 0))
            candidates = sorted(
                (e for e in entries if e["key"] != key
                 and not self._active.get(self._digest(e["key"]), 0)),
                key=lambda e: e.get("accessed_at", 0),
            )
            evictions = []
            for entry in candidates:
                if available >= len(data):
                    break
                evictions.append(entry)
                available += entry["size"]
            if available < len(data):
                raise CacheCapacityError("Insufficient capacity; active entries are protected")

            for entry in evictions:
                self._remove(self._digest(entry["key"]))

            now = time.time()
            meta = {
                "key": key,
                "category": category,
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "created_at": existing.get("created_at", now) if existing else now,
                "accessed_at": now,
            }
            self._atomic_bytes(data_path, data)
            self._atomic_json(meta_path, meta)

    @contextmanager
    def lease(self, key: str):
        """Protect an entry from eviction while the caller is using it."""
        digest = self._digest(key)
        with self._lock:
            self._active[digest] = self._active.get(digest, 0) + 1
        try:
            yield
        finally:
            with self._lock:
                remaining = self._active.get(digest, 0) - 1
                if remaining > 0:
                    self._active[digest] = remaining
                else:
                    self._active.pop(digest, None)

    def cleanup(self, max_age_seconds: float | None = None) -> int:
        if max_age_seconds is not None and max_age_seconds < 0:
            raise ValueError("max_age_seconds cannot be negative")
        cutoff = time.time() - max_age_seconds if max_age_seconds is not None else None
        removed = 0
        with self._lock:
            for entry in self._entries():
                digest = self._digest(entry["key"])
                if self._active.get(digest, 0):
                    continue
                if cutoff is not None and entry.get("accessed_at", 0) > cutoff:
                    continue
                removed += entry["size"]
                self._remove(digest)
        return removed

    def stats(self) -> dict[str, int]:
        with self._lock:
            entries = self._entries()
            used = sum(e["size"] for e in entries)
            return {
                "entry_count": len(entries),
                "used_bytes": used,
                "max_bytes": self.max_bytes,
                "available_bytes": max(0, self.max_bytes - used),
            }
