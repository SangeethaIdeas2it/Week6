import httpx
import asyncio
import time
import random
import logging
import uuid
from typing import Any, Callable, Dict, Optional, List, Tuple
from collections import defaultdict
from datetime import datetime, timedelta

# --- Logging ---
logger = logging.getLogger("ServiceClient")
logging.basicConfig(level=logging.INFO)

# --- Circuit Breaker ---
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def allow_request(self):
        if self.state == "OPEN":
            if (time.time() - self.last_failure_time) > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        return True

    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

# --- Request Tracer ---
class RequestTracer:
    @staticmethod
    def generate_correlation_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def inject_headers(headers: dict, correlation_id: Optional[str] = None) -> dict:
        if not correlation_id:
            correlation_id = RequestTracer.generate_correlation_id()
        headers = dict(headers) if headers else {}
        headers["X-Correlation-ID"] = correlation_id
        headers["X-Request-Timestamp"] = datetime.utcnow().isoformat()
        return headers

# --- Cache Manager ---
class CacheManager:
    def __init__(self):
        self.cache: Dict[str, Tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        value = self.cache.get(key)
        if value:
            data, expiry = value
            if expiry > time.time():
                return data
            else:
                del self.cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int = 60):
        self.cache[key] = (value, time.time() + ttl)

    def invalidate(self, key: str):
        if key in self.cache:
            del self.cache[key]

# --- Service Registry ---
class ServiceRegistry:
    def __init__(self):
        self.services: Dict[str, List[str]] = defaultdict(list)
        self.health: Dict[str, Dict[str, Any]] = defaultdict(dict)

    def register(self, name: str, url: str):
        if url not in self.services[name]:
            self.services[name].append(url)
            self.health[name][url] = {"status": "unknown", "last_check": None, "response_time": None}

    def get_healthy_instance(self, name: str) -> Optional[str]:
        healthy = [url for url, meta in self.health[name].items() if meta["status"] == "healthy"]
        if healthy:
            return random.choice(healthy)
        # fallback to any instance
        return random.choice(self.services[name]) if self.services[name] else None

    async def health_check(self, name: str, timeout: float = 2.0):
        for url in self.services[name]:
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    start = time.time()
                    resp = await client.get(f"{url}/health")
                    elapsed = time.time() - start
                    self.health[name][url] = {
                        "status": "healthy" if resp.status_code == 200 else "unhealthy",
                        "last_check": datetime.utcnow(),
                        "response_time": elapsed
                    }
            except Exception as e:
                self.health[name][url] = {
                    "status": "unhealthy",
                    "last_check": datetime.utcnow(),
                    "response_time": None
                }

# --- Service Client ---
class ServiceClient:
    def __init__(self, registry: ServiceRegistry, cache: CacheManager = None, tracer: RequestTracer = None, breaker: CircuitBreaker = None):
        self.registry = registry
        self.cache = cache or CacheManager()
        self.tracer = tracer or RequestTracer()
        self.breakers: Dict[str, CircuitBreaker] = defaultdict(lambda: breaker or CircuitBreaker())
        self.metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"success": 0, "fail": 0, "latency": []})

    async def request(self, service: str, method: str, path: str, *, params=None, data=None, headers=None, json=None, cache_ttl=None, timeout=5.0, retries=3) -> httpx.Response:
        url = self.registry.get_healthy_instance(service)
        if not url:
            raise Exception(f"No healthy instance for service {service}")
        full_url = f"{url}{path}"
        cache_key = f"{service}:{method}:{path}:{str(params)}:{str(json)}"
        if method.upper() == "GET" and cache_ttl:
            cached = self.cache.get(cache_key)
            if cached:
                return cached
        breaker = self.breakers[service]
        attempt = 0
        last_exc = None
        while attempt < retries:
            if not breaker.allow_request():
                raise Exception(f"Circuit breaker open for {service}")
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    req_headers = self.tracer.inject_headers(headers or {})
                    start = time.time()
                    resp = await client.request(method, full_url, params=params, data=data, headers=req_headers, json=json)
                    latency = time.time() - start
                    self.metrics[service]["success"] += 1
                    self.metrics[service]["latency"].append(latency)
                    breaker.record_success()
                    if method.upper() == "GET" and cache_ttl:
                        self.cache.set(cache_key, resp, ttl=cache_ttl)
                    return resp
            except Exception as e:
                self.metrics[service]["fail"] += 1
                breaker.record_failure()
                last_exc = e
                logger.warning(f"Request to {service} failed (attempt {attempt+1}): {e}")
                await asyncio.sleep(2 ** attempt)
                attempt += 1
        raise last_exc

    def get_metrics(self):
        return self.metrics

# --- Example Usage ---
# registry = ServiceRegistry()
# registry.register('user_service', 'http://localhost:8003')
# registry.register('document_service', 'http://localhost:8001')
# client = ServiceClient(registry)
# response = await client.request('user_service', 'GET', '/auth/me', headers={'Authorization': 'Bearer ...'})

__all__ = [
    'ServiceClient', 'ServiceRegistry', 'CircuitBreaker', 'RequestTracer', 'CacheManager'
]
