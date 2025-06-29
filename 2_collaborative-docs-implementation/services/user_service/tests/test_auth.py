import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_register_and_login():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Register
        resp = await ac.post("/auth/register", json={
            "email": "testuser@example.com",
            "password": "Test@1234",
            "full_name": "Test User"
        })
        assert resp.status_code == 200
        # Login
        resp = await ac.post("/auth/login", data={
            "username": "testuser@example.com",
            "password": "Test@1234"
        })
        assert resp.status_code == 200
        tokens = resp.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens

@pytest.mark.asyncio
async def test_password_complexity():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.post("/auth/register", json={
            "email": "weakpass@example.com",
            "password": "password",
            "full_name": "Weak Pass"
        })
        assert resp.status_code == 422 or resp.status_code == 400

@pytest.mark.asyncio
async def test_account_lockout(monkeypatch):
    # Simulate lockout after failed attempts
    async with AsyncClient(app=app, base_url="http://test") as ac:
        email = "lockout@example.com"
        # Register
        await ac.post("/auth/register", json={
            "email": email,
            "password": "Test@1234",
            "full_name": "Lockout User"
        })
        # Fail login 5 times
        for _ in range(5):
            await ac.post("/auth/login", data={
                "username": email,
                "password": "WrongPass1!"
            })
        # 6th attempt should be locked
        resp = await ac.post("/auth/login", data={
            "username": email,
            "password": "Test@1234"
        })
        assert resp.status_code == 403 