import os
import json
import time
import hashlib
import asyncio
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, Request, Response, HTTPException, Depends, status
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
import httpx
import aioredis
import jwt
import logging
from datetime import datetime, timedelta
import uvicorn
from contextlib import asynccontextmanager

# --- Configuration ---
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user_service:8003")
DOCUMENT_SERVICE_URL = os.getenv("DOCUMENT_SERVICE_URL", "http://document_service:8001")
COLLABORATION_SERVICE_URL = os.getenv("COLLABORATION_SERVICE_URL", "http://collaboration_service:8002")
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# --- Redis Setup ---
redis = None

# --- Service Health Status ---
service_health = {
    "user_service": {"status": "unknown", "last_check": None, "response_time": None},
    "document_service": {"status": "unknown", "last_check": None, "response_time": None},
    "collaboration_service": {"status": "unknown", "last_check": None, "response_time": None}
}

# --- Rate Limiting Configuration ---
RATE_LIMITS = {
    "auth": {"requests": 100, "window": 3600},  # 100 requests per hour
    "documents": {"requests": 1000, "window": 3600},  # 1000 requests per hour
    "default": {"requests": 500, "window": 3600}  # 500 requests per hour
}

# --- Circuit Breaker Configuration ---
CIRCUIT_BREAKER = {
    "failure_threshold": 5,
    "recovery_timeout": 60,
    "expected_exception": (httpx.RequestError, httpx.TimeoutException)
}

# --- FastAPI App Setup ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global redis
    redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
    logger.info("API Gateway started.")
    yield
    # Shutdown
    await redis.close()
    logger.info("API Gateway shutdown.")

app = FastAPI(title="API Gateway", version="1.0.0", lifespan=lifespan)

# --- Middleware ---
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request Correlation ID Middleware ---
class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or f"req_{int(time.time() * 1000)}"
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response

app.add_middleware(CorrelationMiddleware)

# --- Rate Limiting Middleware ---
class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        user_id = getattr(request.state, 'user_id', 'anonymous')
        endpoint = request.url.path.split('/')[2] if len(request.url.path.split('/')) > 2 else 'default'
        
        # Get rate limit config
        limit_config = RATE_LIMITS.get(endpoint, RATE_LIMITS["default"])
        
        # Check rate limit
        key = f"rate_limit:{user_id}:{endpoint}"
        current = await redis.get(key)
        
        if current and int(current) >= limit_config["requests"]:
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "retry_after": limit_config["window"]}
            )
        
        # Increment counter
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, limit_config["window"])
        await pipe.execute()
        
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(limit_config["requests"] - int(current or 0))
        return response

app.add_middleware(RateLimitMiddleware)

# --- Authentication Middleware ---
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        # Skip auth for health checks and metrics
        if request.url.path in ["/api/v1/health", "/api/v1/metrics"]:
            return await call_next(request)
        
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"error": "Missing or invalid authorization header"}
            )
        
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            request.state.user_id = payload.get("sub")
            request.state.user_email = payload.get("email")
        except jwt.ExpiredSignatureError:
            return JSONResponse(
                status_code=401,
                content={"error": "Token expired"}
            )
        except jwt.InvalidTokenError:
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid token"}
            )
        
        return await call_next(request)

app.add_middleware(AuthMiddleware)

# --- Service Discovery and Health Monitoring ---
async def check_service_health(service_name: str, service_url: str):
    try:
        start_time = time.time()
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{service_url}/health")
            response_time = time.time() - start_time
            
            service_health[service_name] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "last_check": datetime.utcnow(),
                "response_time": response_time
            }
        return True
    except Exception as e:
        logger.error(f"Health check failed for {service_name}: {e}")
        service_health[service_name] = {
            "status": "unhealthy",
            "last_check": datetime.utcnow(),
            "response_time": None
        }
        return False

async def health_check_loop():
    while True:
        await asyncio.gather(
            check_service_health("user_service", USER_SERVICE_URL),
            check_service_health("document_service", DOCUMENT_SERVICE_URL),
            check_service_health("collaboration_service", COLLABORATION_SERVICE_URL)
        )
        await asyncio.sleep(30)  # Check every 30 seconds

# --- Circuit Breaker ---
class CircuitBreaker:
    def __init__(self, name: str):
        self.name = name
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > CIRCUIT_BREAKER["recovery_timeout"]:
                self.state = "HALF_OPEN"
            else:
                raise HTTPException(status_code=503, detail="Service temporarily unavailable")
        
        try:
            result = await func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except CIRCUIT_BREAKER["expected_exception"] as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= CIRCUIT_BREAKER["failure_threshold"]:
                self.state = "OPEN"
            
            raise HTTPException(status_code=503, detail=f"Service error: {str(e)}")

# Initialize circuit breakers
circuit_breakers = {
    "user_service": CircuitBreaker("user_service"),
    "document_service": CircuitBreaker("document_service"),
    "collaboration_service": CircuitBreaker("collaboration_service")
}

# --- Intelligent Routing ---
def get_service_route(path: str) -> tuple[str, str]:
    """Intelligent routing based on request path and analysis."""
    if path.startswith("/api/v1/auth"):
        return "user_service", USER_SERVICE_URL
    elif path.startswith("/api/v1/documents"):
        return "document_service", DOCUMENT_SERVICE_URL
    elif path.startswith("/api/v1/collaboration"):
        return "collaboration_service", COLLABORATION_SERVICE_URL
    else:
        # Default routing based on path analysis
        if "user" in path or "auth" in path:
            return "user_service", USER_SERVICE_URL
        elif "document" in path or "file" in path:
            return "document_service", DOCUMENT_SERVICE_URL
        else:
            return "document_service", DOCUMENT_SERVICE_URL  # Default fallback

# --- Request/Response Transformation ---
async def transform_request(request: Request) -> dict:
    """Transform incoming request for service consumption."""
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.json()
        except:
            body = await request.body()
    
    return {
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
        "body": body,
        "user_id": getattr(request.state, 'user_id', None),
        "correlation_id": getattr(request.state, 'correlation_id', None)
    }

async def transform_response(response: httpx.Response) -> Response:
    """Transform service response for client consumption."""
    content = response.content
    try:
        # Try to parse as JSON for transformation
        data = response.json()
        # Add gateway metadata
        data["_gateway"] = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": response.headers.get("X-Service-Name", "unknown")
        }
        content = json.dumps(data).encode()
    except:
        pass  # Keep original content if not JSON
    
    return Response(
        content=content,
        status_code=response.status_code,
        headers=dict(response.headers)
    )

# --- Caching ---
async def get_cached_response(cache_key: str) -> Optional[Response]:
    """Get cached response from Redis."""
    cached = await redis.get(cache_key)
    if cached:
        data = json.loads(cached)
        return Response(
            content=data["content"].encode(),
            status_code=data["status_code"],
            headers=data["headers"]
        )
    return None

async def cache_response(cache_key: str, response: Response, ttl: int = 300):
    """Cache response in Redis."""
    cache_data = {
        "content": response.body.decode(),
        "status_code": response.status_code,
        "headers": dict(response.headers)
    }
    await redis.setex(cache_key, ttl, json.dumps(cache_data))

# --- Main Gateway Logic ---
async def proxy_request(request: Request) -> Response:
    """Main gateway logic for routing and proxying requests."""
    start_time = time.time()
    
    # Get service route
    service_name, service_url = get_service_route(request.url.path)
    
    # Check circuit breaker
    circuit_breaker = circuit_breakers[service_name]
    
    # Generate cache key for GET requests
    cache_key = None
    if request.method == "GET":
        user_id = getattr(request.state, 'user_id', 'anonymous')
        cache_key = f"cache:{hashlib.md5(f'{request.url}{user_id}'.encode()).hexdigest()}"
        cached_response = await get_cached_response(cache_key)
        if cached_response:
            return cached_response
    
    # Transform request
    transformed_request = await transform_request(request)
    
    # Make request to service
    async def make_service_request():
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Prepare headers
            headers = dict(request.headers)
            headers["X-User-ID"] = str(getattr(request.state, 'user_id', ''))
            headers["X-Correlation-ID"] = getattr(request.state, 'correlation_id', '')
            headers["X-Service-Name"] = service_name
            
            # Make request
            response = await client.request(
                method=request.method,
                url=f"{service_url}{request.url.path}?{request.url.query}",
                headers=headers,
                content=transformed_request["body"] if transformed_request["body"] else None
            )
            return response
    
    try:
        service_response = await circuit_breaker.call(make_service_request)
        
        # Transform response
        gateway_response = await transform_response(service_response)
        
        # Cache response if GET request and successful
        if cache_key and service_response.status_code == 200:
            await cache_response(cache_key, gateway_response)
        
        # Log request
        duration = time.time() - start_time
        logger.info(f"Request {request.method} {request.url.path} -> {service_name} ({duration:.3f}s)")
        
        return gateway_response
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Gateway error: {e} ({duration:.3f}s)")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal gateway error", "correlation_id": getattr(request.state, 'correlation_id', '')}
        )

# --- Gateway Routes ---
@app.get("/api/v1/health")
async def health_check():
    """Comprehensive health check for all services."""
    health_status = {
        "gateway": "healthy",
        "services": service_health,
        "timestamp": datetime.utcnow().isoformat()
    }
    # Check if any service is unhealthy
    unhealthy_services = [name for name, status in service_health.items() if status["status"] != "healthy"]
    if unhealthy_services:
        health_status["gateway"] = "degraded"
        health_status["unhealthy_services"] = unhealthy_services
    return health_status

@app.get("/api/v1/metrics")
async def metrics():
    """Gateway and service metrics."""
    return {
        "gateway": {
            "uptime": time.time(),
            "requests_processed": 0,  # Add counter in production
            "average_response_time": 0,  # Add calculation in production
        },
        "services": service_health,
        "circuit_breakers": {
            name: {
                "state": cb.state,
                "failure_count": cb.failure_count
            } for name, cb in circuit_breakers.items()
        },
        "redis": {
            "connected": redis is not None
        }
    }

@app.api_route("/api/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def gateway_route(request: Request, path: str):
    return await proxy_request(request)

# --- Error Handlers ---
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "correlation_id": getattr(request.state, 'correlation_id', ''),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "correlation_id": getattr(request.state, 'correlation_id', ''),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# --- Startup Tasks ---
@app.on_event("startup")
async def startup_event():
    # Start health check loop
    asyncio.create_task(health_check_loop())

# --- Run the app ---
if __name__ == "__main__":
    uvicorn.run("api_gateway:app", host="0.0.0.0", port=8000, reload=True)
