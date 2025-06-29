import pytest
from httpx import AsyncClient
from main import app
import asyncio

@pytest.mark.asyncio
async def test_rate_limiting():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        for _ in range(101):
            resp = await ac.post("/auth/login", data={
                "username": "testuser@example.com",
                "password": "Test@1234"
            })
        assert resp.status_code == 429

@pytest.mark.asyncio
async def test_concurrent_logins():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        async def login():
            return await ac.post("/auth/login", data={
                "username": "testuser@example.com",
                "password": "Test@1234"
            })
        results = await asyncio.gather(*[login() for _ in range(20)])
        assert all(r.status_code in (200, 401, 403, 429) for r in results) 