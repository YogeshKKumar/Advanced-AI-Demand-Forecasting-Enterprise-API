from __future__ import annotations

from threading import Lock
from time import monotonic
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: int = 20):
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, tuple[float, Any]] = {}
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            item = self._items.get(key)
            if not item:
                return None
            expires_at, value = item
            if monotonic() >= expires_at:
                self._items.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any) -> Any:
        with self._lock:
            self._items[key] = (monotonic() + self.ttl_seconds, value)
        return value

    def invalidate_prefix(self, prefix: str) -> None:
        with self._lock:
            for key in [key for key in self._items if key.startswith(prefix)]:
                self._items.pop(key, None)


dashboard_cache = TTLCache()
