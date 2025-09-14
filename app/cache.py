# app/cache.py
from collections import OrderedDict
import threading
import time

class MemoryCache:
    """
    Cache LRU com TTL por item.
    - Thread-safe (RLock)
    - Limites: número de itens e opcionalmente bytes totais
    """
    def __init__(self, max_items=128, max_bytes=None, default_ttl=30):
        self.max_items = max_items
        self.max_bytes = max_bytes
        self.default_ttl = default_ttl

        self._lock = threading.RLock()
        self._store = OrderedDict()  # key -> (value, expiry_ts, size)
        self._bytes_in_use = 0
        self._hits = 0
        self._misses = 0

    def stats(self):
        with self._lock:
            return {
                "items": len(self._store),
                "bytes_in_use": self._bytes_in_use,
                "hits": self._hits,
                "misses": self._misses,
            }

    def _evict_if_needed(self):
        while self.max_items and len(self._store) > self.max_items:
            k, (v, expiry, sz) = self._store.popitem(last=False)
            self._bytes_in_use -= sz
        if self.max_bytes is not None:
            while self._bytes_in_use > self.max_bytes and self._store:
                k, (v, expiry, sz) = self._store.popitem(last=False)
                self._bytes_in_use -= sz

    def _expired(self, expiry_ts):
        return expiry_ts is not None and time.time() >= expiry_ts

    def get(self, key):
        with self._lock:
            if key not in self._store:
                self._misses += 1
                return None
            value, expiry_ts, sz = self._store.pop(key)
            if self._expired(expiry_ts):
                # expirado: remove
                self._bytes_in_use -= sz
                self._misses += 1
                return None
            # LRU: re-insere como mais recente
            self._store[key] = (value, expiry_ts, sz)
            self._hits += 1
            return value

    def set(self, key, value, ttl_seconds=None):
        if ttl_seconds is None:
            ttl_seconds = self.default_ttl
        expiry = time.time() + ttl_seconds if ttl_seconds > 0 else None
        sz = len(value) if hasattr(value, "__len__") else 0
        with self._lock:
            if key in self._store:
                _, _, old_sz = self._store.pop(key)
                self._bytes_in_use -= old_sz
            self._store[key] = (value, expiry, sz)
            self._bytes_in_use += sz
            self._evict_if_needed()

    def invalidate(self, key):
        with self._lock:
            if key in self._store:
                _, _, sz = self._store.pop(key)
                self._bytes_in_use -= sz
