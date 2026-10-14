# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

"""Process-local TTL cache for dashboard item payloads.

Keys must include the user (and related ACL context) so cached values never
cross access-right boundaries. Entries expire by TTL; there is no cross-worker
invalidation when source records change — intended for wall-screen boards that
already poll on a refresh interval.
"""

import hashlib
import json
import threading
import time
from collections import OrderedDict

_LOCK = threading.Lock()
# Keep insertion order so eviction can drop the oldest keys under pressure.
_CACHE = OrderedDict()
_MAX_ENTRIES = 2000


def fingerprint_params(params):
    """Stable fingerprint for the client filter payload."""
    payload = params or {}
    encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def cache_get(key):
    """Return a cached value or ``None`` when missing/expired."""
    now = time.monotonic()
    with _LOCK:
        entry = _CACHE.get(key)
        if entry is None:
            return None
        value, expires = entry
        if expires <= now:
            _CACHE.pop(key, None)
            return None
        _CACHE.move_to_end(key)
        return value


def cache_set(key, value, ttl):
    """Store ``value`` for ``ttl`` seconds (no-op when ttl <= 0)."""
    if ttl <= 0:
        return
    expires = time.monotonic() + ttl
    with _LOCK:
        _CACHE[key] = (value, expires)
        _CACHE.move_to_end(key)
        while len(_CACHE) > _MAX_ENTRIES:
            _CACHE.popitem(last=False)


def cache_clear():
    """Drop every entry (tests / maintenance)."""
    with _LOCK:
        _CACHE.clear()
