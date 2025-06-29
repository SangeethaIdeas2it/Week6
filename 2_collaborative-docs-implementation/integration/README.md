# API Gateway

## Overview
Intelligent API Gateway for the collaborative document system with routing, authentication, rate limiting, caching, and monitoring.

## Features
- **Intelligent Routing**: Route requests to User, Document, and Collaboration services
- **Centralized Authentication**: JWT validation and user context injection
- **Rate Limiting**: Per-user and per-endpoint rate limiting with Redis
- **Request/Response Transformation**: Add correlation IDs and gateway metadata
- **Load Balancing**: Health checks and circuit breakers for service resilience
- **Caching**: Redis-based response caching for GET requests
- **Monitoring**: Real-time metrics and health status
- **CORS**: Cross-origin resource sharing configuration
- **Compression**: GZip compression for responses

## Configuration
Environment variables:
- `REDIS_URL`: Redis connection string
- `USER_SERVICE_URL`: User service endpoint
- `DOCUMENT_SERVICE_URL`: Document service endpoint
- `COLLABORATION_SERVICE_URL`: Collaboration service endpoint
- `SECRET_KEY`: JWT secret key

## Routes
- `/api/v1/auth/*` → User Service
- `/api/v1/documents/*` → Document Service
- `/api/v1/collaboration/*` → Collaboration Service
- `/api/v1/health` → Health check for all services
- `/api/v1/metrics` → Gateway and service metrics

## Testing
```bash
pytest tests/
```

## Deployment
```bash
docker build -t api-gateway .
docker run -p 8000:8000 api-gateway
```

## Monitoring
- Health endpoint: `/api/v1/health`
- Metrics endpoint: `/api/v1/metrics`
- Circuit breaker status in metrics
- Request correlation IDs for tracing

## Security
- JWT token validation
- Rate limiting per user
- CORS configuration
- Request sanitization
- Error handling without information leakage 