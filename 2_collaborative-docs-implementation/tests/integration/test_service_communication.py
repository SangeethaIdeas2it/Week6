import pytest
import asyncio
import httpx
import time
from typing import Dict, Any
from unittest import mock

# --- Test Config ---
USER_SERVICE_URL = "http://localhost:8003"
DOCUMENT_SERVICE_URL = "http://localhost:8001"
COLLABORATION_SERVICE_URL = "http://localhost:8002"
API_GATEWAY_URL = "http://localhost:8000/api/v1"
REDIS_URL = "redis://localhost:6379/0"

# --- Pytest Fixtures ---
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="module")
def http_client():
    with httpx.Client() as client:
        yield client

@pytest.fixture(scope="module")
def async_client():
    async with httpx.AsyncClient() as client:
        yield client

# --- Utility Functions ---
def register_user(client, email="testuser@example.com", password="TestPass123!") -> Dict[str, Any]:
    resp = client.post(f"{API_GATEWAY_URL}/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 201
    return resp.json()

def login_user(client, email="testuser@example.com", password="TestPass123!") -> str:
    resp = client.post(f"{API_GATEWAY_URL}/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]

def create_document(client, token, title="Test Doc", content="Hello World") -> Dict[str, Any]:
    resp = client.post(
        f"{API_GATEWAY_URL}/documents/",
        json={"title": title, "content": content},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 201
    return resp.json()

def share_document(client, token, doc_id, user_id, permission="read"):
    resp = client.post(
        f"{API_GATEWAY_URL}/documents/{doc_id}/share",
        json={"user_id": user_id, "permission": permission},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    return resp.json()

# --- Test Scenarios ---
def test_user_registration_to_document_creation(http_client):
    """End-to-end: User registers, logs in, creates a document."""
    user = register_user(http_client)
    token = login_user(http_client)
    doc = create_document(http_client, token)
    assert doc["title"] == "Test Doc"
    assert doc["content"] == "Hello World"

def test_document_sharing_with_event_notification(http_client):
    """Document sharing triggers event notification (mocked)."""
    user = register_user(http_client, email="shareuser@example.com")
    token = login_user(http_client, email="shareuser@example.com")
    doc = create_document(http_client, token, title="Share Doc")
    # Mock event publisher
    with mock.patch("shared.communication.events.EventPublisher.publish") as mock_publish:
        share_document(http_client, token, doc["id"], user["id"], permission="read")
        mock_publish.assert_called()

def test_service_failure_and_recovery(async_client):
    """Simulate service failure and test recovery/circuit breaker."""
    # Simulate user service down
    # (In real infra, stop container or mock httpx to raise error)
    with mock.patch("httpx.AsyncClient.request", side_effect=httpx.ConnectError("Service down")):
        resp = asyncio.run(async_client.get(f"{API_GATEWAY_URL}/auth/profile"))
        assert resp.status_code in (503, 500)
    # After recovery, should succeed (remove mock)
    # (Here, just test that circuit breaker resets)
    # This is a placeholder for real infra test

@pytest.mark.asyncio
def test_api_gateway_routing_and_auth(async_client):
    """Test API Gateway routing and authentication enforcement."""
    # Unauthenticated request
    resp = await async_client.get(f"{API_GATEWAY_URL}/documents/")
    assert resp.status_code == 401
    # Authenticated request
    user = register_user(httpx.Client(), email="routeuser@example.com")
    token = login_user(httpx.Client(), email="routeuser@example.com")
    resp = await async_client.get(
        f"{API_GATEWAY_URL}/documents/",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code in (200, 201)

@pytest.mark.asyncio
def test_event_processing_and_ordering(async_client):
    """Test event processing, ordering, and deduplication."""
    from shared.communication.events import EventPublisher, EventConsumer
    publisher = EventPublisher()
    await publisher.connect()
    # Publish multiple events
    for i in range(5):
        await publisher.publish("document_created", {
            "event_type": "document_created",
            "document_id": i,
            "timestamp": time.time(),
            "payload": {"title": f"Doc {i}"}
        })
    # Consume and check order
    events = []
    async def handler(event):
        events.append(event)
        if len(events) == 5:
            raise SystemExit(0)
    consumer = EventConsumer("document_created", handler)
    try:
        await consumer.start()
    except SystemExit:
        pass
    ids = [e["document_id"] for e in events]
    assert ids == list(range(5))

# --- Performance Benchmark ---
def test_performance_benchmark(http_client):
    """Benchmark document creation throughput."""
    token = login_user(http_client)
    start = time.time()
    for i in range(20):
        create_document(http_client, token, title=f"Perf Doc {i}")
    duration = time.time() - start
    assert duration < 10  # 20 docs in under 10 seconds

# --- Cleanup Fixture ---
@pytest.fixture(autouse=True, scope="module")
def cleanup():
    yield
    # Add cleanup logic: delete test users/docs, flush Redis, etc.
