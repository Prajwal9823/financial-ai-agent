"""
Minimal in-memory TTL cache.

Free data APIs (yfinance, SEC EDGAR) are rate-limited or simply slow, so
every tool call should pass through this cache first. This is intentionally
dependency-free (no Redis required) so the project runs with zero extra
infrastructure; swap `TTLCache` for a Redis-backed version later without
touching any calling code, since the public interface (get/set) stays the same.
"""
import time
from threading import Lock
from typing import Any, Optional

from app.core.config import get_settings

settings = get_settings()


class TTLCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.time() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else settings.cache_ttl_seconds
        with self._lock:
            self._store[key] = (time.time() + ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


# Single shared cache instance for the whole process.
cache = TTLCache()


def cache_key(*parts: str) -> str:
    """Build a stable cache key from arbitrary string parts."""
    return "::".join(p.upper() for p in parts)
