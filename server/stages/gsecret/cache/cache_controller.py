import datetime
from threading import Lock
from typing import Dict, Optional

from interfaces.gsecret import Secret, TokenID


class CacheEntry:
    """Represents a cached secret with metadata"""

    def __init__(self, secret: Secret):
        self.secret = secret
        self.cached_at = datetime.datetime.now(tz=datetime.timezone.utc)
        self.access_count = 0
        self.last_accessed = self.cached_at

    def access(self) -> Secret:
        """Record an access and return the secret"""
        self.access_count += 1
        self.last_accessed = datetime.datetime.now(tz=datetime.timezone.utc)
        return self.secret

    def update(self, secret: Secret):
        """Update the cached secret"""
        self.secret = secret
        self.cached_at = datetime.datetime.now(tz=datetime.timezone.utc)

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if the cache entry has expired"""
        if ttl_seconds <= 0:
            return False  # TTL disabled
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        age = (now - self.cached_at).total_seconds()
        return age > ttl_seconds


class TokenCache:
    """Cache for secrets associated with a specific token"""

    def __init__(self):
        self.id_cache: Dict[str, CacheEntry] = {}
        self.key_cache: Dict[str, CacheEntry] = {}
        self.lock = Lock()

    @property
    def ids(self) -> set[str]:
        """Get all cached secret IDs"""
        with self.lock:
            return set(self.id_cache.keys())

    @property
    def keys(self) -> set[str]:
        """Get all cached secret keys"""
        with self.lock:
            return set(self.key_cache.keys())

    def remove_by_id(self, key_id: str):
        """Remove a secret from cache by ID"""
        with self.lock:
            if key_id in self.id_cache:
                del self.id_cache[key_id]

    def remove_by_key(self, key: str):
        """Remove a secret from cache by key"""
        with self.lock:
            if key in self.key_cache:
                del self.key_cache[key]

    def get_by_id(self, key_id: str, ttl_seconds: int) -> Optional[Secret]:
        """Get a secret by ID from cache"""
        with self.lock:
            entry = self.id_cache.get(key_id)
            if entry and not entry.is_expired(ttl_seconds):
                return entry.access()
            elif entry and entry.is_expired(ttl_seconds):
                # Remove expired entry
                del self.id_cache[key_id]
                if entry.secret.key in self.key_cache:
                    del self.key_cache[entry.secret.key]
            return None

    def get_by_key(self, key: str, ttl_seconds: int) -> Optional[Secret]:
        """Get a secret by key from cache"""
        with self.lock:
            entry = self.key_cache.get(key)
            if entry and not entry.is_expired(ttl_seconds):
                return entry.access()
            elif entry and entry.is_expired(ttl_seconds):
                # Remove expired entry
                del self.key_cache[key]
                if entry.secret.key_id in self.id_cache:
                    del self.id_cache[entry.secret.key_id]
            return None

    def update_by_id(self, secret: Secret, key_id: str):
        """Update an existing secret in cache by ID"""
        with self.lock:
            # Update ID cache
            if key_id in self.id_cache:
                self.id_cache[key_id].update(secret)
            else:
                self.id_cache[key_id] = CacheEntry(secret)

    def update_by_key(self, secret: Secret, key: str):
        """Update an existing secret in cache by key"""
        with self.lock:
            # Update key cache
            if key in self.key_cache:
                self.key_cache[key].update(secret)
            else:
                self.key_cache[key] = CacheEntry(secret)

    def invalidate_by_id(self, key_id: str):
        """Remove a secret from cache by ID"""
        with self.lock:
            if key_id in self.id_cache:
                entry = self.id_cache[key_id]
                del self.id_cache[key_id]
                if entry.secret.key in self.key_cache:
                    del self.key_cache[entry.secret.key]

    def invalidate_by_key(self, key: str):
        """Remove a secret from cache by key"""
        with self.lock:
            if key in self.key_cache:
                entry = self.key_cache[key]
                del self.key_cache[key]
                if entry.secret.key_id in self.id_cache:
                    del self.id_cache[entry.secret.key_id]

    def clear(self):
        """Clear all cached secrets"""
        with self.lock:
            self.id_cache.clear()
            self.key_cache.clear()


class CacheController:
    """Controller for managing caches across multiple tokens"""

    def __init__(self):
        self.token_caches: Dict[str, TokenCache] = {}
        self.lock = Lock()

    def get_token_cache(self, token_hash: TokenID) -> TokenCache:
        """Get or create a cache for a specific token"""
        with self.lock:
            if token_hash.token_id not in self.token_caches:
                self.token_caches[token_hash.token_id] = TokenCache()
            return self.token_caches[token_hash.token_id]

    def clear_token_cache(self, token_hash: TokenID):
        """Clear all cached secrets for a specific token"""
        with self.lock:
            if token_hash.token_id in self.token_caches:
                self.token_caches[token_hash.token_id].clear()

    def clear_all(self):
        """Clear all caches"""
        with self.lock:
            for cache in self.token_caches.values():
                cache.clear()
            self.token_caches.clear()
