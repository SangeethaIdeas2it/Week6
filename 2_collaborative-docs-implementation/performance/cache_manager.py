import asyncio
import aioredis
import time
import zlib
import pickle
import logging
from typing import Any, Callable, Optional, Dict, List
from collections import OrderedDict, defaultdict
from threading import Lock

# --- Logging ---
logger = logging.getLogger("CacheManager")
logging.basicConfig(level=logging.INFO)

# --- In-Memory LRU Cache ---
class LRUCache:
    def __init__(self, max_size=1000):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.lock = Lock()

    def get(self, key):
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
            return None

    def set(self, key, value):
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = value
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)

    def delete(self, key):
        with self.lock:
            if key in self.cache:
                del self.cache[key]

    def clear(self):
        with self.lock:
            self.cache.clear()

# --- Redis Async Cache Layer ---
class RedisCache:
    def __init__(self, redis_url="redis://localhost:6379/0", namespace="cache", compress=True):
        self.redis_url = redis_url
        self.namespace = namespace
        self.compress = compress
        self.redis = None

    async def connect(self):
        import redis.asyncio as aioredis  # Use redis-py for Python 3.12+
        self.redis = await aioredis.from_url(self.redis_url, decode_responses=False)

    def _key(self, key, version=None):
        v = f":v{version}" if version else ""
        return f"{self.namespace}:{key}{v}"

    def _serialize(self, value):
        data = pickle.dumps(value)
        if self.compress and len(data) > 1024:
            data = zlib.compress(data)
        return data

    def _deserialize(self, data):
        try:
            try:
                return pickle.loads(zlib.decompress(data))
            except zlib.error:
                return pickle.loads(data)
        except Exception as e:
            logger.error(f"Deserialization error: {e}")
            return None

    async def get(self, key, version=None):
        k = self._key(key, version)
        try:
            data = await self.redis.get(k)
            if data:
                return self._deserialize(data)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
        return None

    async def set(self, key, value, ttl=300, version=None):
        k = self._key(key, version)
        try:
            data = self._serialize(value)
            await self.redis.setex(k, ttl, data)
        except Exception as e:
            logger.error(f"Redis set error: {e}")

    async def delete(self, key, version=None):
        k = self._key(key, version)
        try:
            await self.redis.delete(k)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")

    async def clear(self):
        try:
            keys = await self.redis.keys(f"{self.namespace}:*")
            if keys:
                await self.redis.delete(*keys)
        except Exception as e:
            logger.error(f"Redis clear error: {e}")

# --- CDN/Edge Cache (Stub) ---
class CDNCache:
    def __init__(self):
        # Integrate with real CDN provider in production
        self.cache = {}

    def get(self, key):
        return self.cache.get(key)

    def set(self, key, value, ttl=3600):
        self.cache[key] = value  # Stub: no expiry

    def invalidate(self, key):
        if key in self.cache:
            del self.cache[key]

# --- Predictive Cache Warming ---
class PredictiveCacheWarmer:
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.access_patterns = defaultdict(int)

    def record_access(self, key):
        self.access_patterns[key] += 1

    async def warm_top_n(self, n=10, fetch_fn: Callable = None):
        top_keys = sorted(self.access_patterns, key=self.access_patterns.get, reverse=True)[:n]
        for key in top_keys:
            if fetch_fn:
                value = await fetch_fn(key)
                await self.cache_manager.set(key, value)

# --- Cache Dependency Tracking ---
class CacheDependencyTracker:
    def __init__(self):
        self.dependencies = defaultdict(set)

    def add_dependency(self, key, depends_on):
        self.dependencies[depends_on].add(key)

    def get_dependents(self, key):
        return self.dependencies.get(key, set())

    def invalidate_dependents(self, key, cache_manager):
        for dep in self.get_dependents(key):
            cache_manager.invalidate(dep)

# --- Main Cache Manager ---
class CacheManager:
    """
    Multi-layer, production-ready cache manager for collaborative docs platform.
    Supports Redis, in-memory, CDN, predictive warming, dependency tracking, and monitoring.
    """
    def __init__(self, redis_url="redis://localhost:6379/0", namespace="cache", lru_size=1000):
        self.memory_cache = LRUCache(max_size=lru_size)
        self.redis_cache = RedisCache(redis_url, namespace)
        self.cdn_cache = CDNCache()
        self.dependency_tracker = CacheDependencyTracker()
        self.warmer = PredictiveCacheWarmer(self)
        self.metrics = defaultdict(list)
        self.lock = Lock()

    async def connect(self):
        await self.redis_cache.connect()

    def _record_metric(self, name, value):
        with self.lock:
            self.metrics[name].append((time.time(), value))

    async def get(self, key, version=None, layer="auto"):
        start = time.time()
        value = None
        # Try in-memory first
        if layer in ("auto", "memory"):
            value = self.memory_cache.get(key)
            if value:
                self._record_metric("hit_memory", time.time() - start)
                self.warmer.record_access(key)
                return value
        # Try Redis
        if layer in ("auto", "redis") and not value:
            value = await self.redis_cache.get(key, version)
            if value:
                self.memory_cache.set(key, value)
                self._record_metric("hit_redis", time.time() - start)
                self.warmer.record_access(key)
                return value
        # Try CDN (stub)
        if layer in ("auto", "cdn") and not value:
            value = self.cdn_cache.get(key)
            if value:
                self.memory_cache.set(key, value)
                self._record_metric("hit_cdn", time.time() - start)
                self.warmer.record_access(key)
                return value
        self._record_metric("miss", time.time() - start)
        return None

    async def set(self, key, value, ttl=300, version=None, layer="auto"):
        self.memory_cache.set(key, value)
        await self.redis_cache.set(key, value, ttl, version)
        self.cdn_cache.set(key, value, ttl)

    async def invalidate(self, key, version=None):
        self.memory_cache.delete(key)
        await self.redis_cache.delete(key, version)
        self.cdn_cache.invalidate(key)
        # Invalidate dependents
        self.dependency_tracker.invalidate_dependents(key, self)

    async def clear(self):
        self.memory_cache.clear()
        await self.redis_cache.clear()
        # CDN clear not implemented

    async def warm_cache(self, keys: List[str], fetch_fn: Callable):
        for key in keys:
            value = await fetch_fn(key)
            await self.set(key, value)

    def get_metrics(self):
        """Return cache performance metrics."""
        return dict(self.metrics)

    def recommend_optimizations(self):
        """Analyze metrics and recommend optimizations."""
        # Example: recommend increasing LRU size if many misses
        miss_count = len(self.metrics["miss"])
        hit_mem = len(self.metrics["hit_memory"])
        hit_redis = len(self.metrics["hit_redis"])
        if miss_count > (hit_mem + hit_redis):
            return "Consider increasing LRU cache size or improving cache warming."
        return "Cache performance is optimal."

# --- Example Usage ---
# async def main():
#     cache = CacheManager()
#     await cache.connect()
#     await cache.set("user:1", {"id": 1, "name": "Alice"})
#     user = await cache.get("user:1")
#     print(user)
#
# if __name__ == "__main__":
#     asyncio.run(main())
