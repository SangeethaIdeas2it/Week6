import pytest
from httpx import AsyncClient
from api_gateway import app
import json

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "gateway" in data
        assert "services" in data

@pytest.mark.asyncio
async def test_metrics():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "gateway" in data
        assert "circuit_breakers" in data

@pytest.mark.asyncio
async def test_authentication_required():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/documents")
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_correlation_id():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")
        assert "X-Correlation-ID" in response.headers

@pytest.mark.asyncio
async def test_rate_limiting():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Make multiple requests to trigger rate limiting
        for _ in range(101):
            response = await ac.get("/api/v1/health")
            if response.status_code == 429:
                break
        else:
            pytest.fail("Rate limiting not triggered") 