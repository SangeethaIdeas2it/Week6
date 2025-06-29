import asyncio
import aioredis
import json
import time
import logging
from typing import Any, Callable, Dict, List, Optional, Type
from pydantic import BaseModel, ValidationError
from datetime import datetime

# --- Event Schemas ---
class UserEvent(BaseModel):
    event_type: str
    user_id: int
    timestamp: datetime
    payload: Dict[str, Any]

class DocumentEvent(BaseModel):
    event_type: str
    document_id: int
    timestamp: datetime
    payload: Dict[str, Any]

class CollaborationEvent(BaseModel):
    event_type: str
    document_id: int
    user_id: int
    timestamp: datetime
    payload: Dict[str, Any]

EVENT_SCHEMAS = {
    'user_registered': UserEvent,
    'user_updated': UserEvent,
    'user_deleted': UserEvent,
    'document_created': DocumentEvent,
    'document_updated': DocumentEvent,
    'document_shared': DocumentEvent,
    'document_deleted': DocumentEvent,
    'user_joined_session': CollaborationEvent,
    'user_left_session': CollaborationEvent,
    'document_changed': CollaborationEvent,
}

# --- Redis Stream Names ---
STREAMS = {
    'user': 'user_events',
    'document': 'document_events',
    'collaboration': 'collaboration_events',
    'dead_letter': 'dead_letter_events',
    'audit': 'event_audit_store',
}

# --- Logging ---
logger = logging.getLogger("EventSystem")
logging.basicConfig(level=logging.INFO)

# --- EventPublisher ---
class EventPublisher:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis = None

    async def connect(self):
        self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)

    async def publish(self, event_type: str, data: dict):
        if event_type not in EVENT_SCHEMAS:
            raise ValueError(f"Unknown event type: {event_type}")
        schema = EVENT_SCHEMAS[event_type]
        try:
            event = schema(**data)
        except ValidationError as e:
            logger.error(f"Event validation failed: {e}")
            raise
        stream = self._get_stream(event_type)
        event_data = event.dict()
        await self.redis.xadd(stream, {"event": json.dumps(event_data)})
        # Store in audit
        await self.redis.xadd(STREAMS['audit'], {"event": json.dumps(event_data)})
        logger.info(f"Published event {event_type} to {stream}")

    def _get_stream(self, event_type: str) -> str:
        if event_type.startswith('user_'):
            return STREAMS['user']
        elif event_type.startswith('document_'):
            return STREAMS['document']
        elif event_type.startswith('user_joined') or event_type.startswith('user_left') or event_type.startswith('document_changed'):
            return STREAMS['collaboration']
        else:
            return STREAMS['dead_letter']

    @classmethod
    async def test_events(cls):
        redis_url = "redis://localhost:6379/0"
        publisher = cls(redis_url)
        await publisher.connect()
        # Publish a test event
        await publisher.publish('user_registered', {
            'event_type': 'user_registered',
            'user_id': 1,
            'timestamp': datetime.utcnow(),
            'payload': {'email': 'test@example.com'}
        })
        # Consume the event
        async def handler(event):
            print(f"Handled event: {event}")
            # Stop after first event
            raise SystemExit(0)
        consumer = EventConsumer(redis_url, STREAMS['user'], 'test_group', 'test_consumer', handler)
        await consumer.connect()
        try:
            await consumer.consume()
        except SystemExit:
            pass

# --- EventStore ---
class EventStore:
    def __init__(self, redis):
        self.redis = redis

    async def replay(self, stream: str, handler: Callable[[dict], Any], from_id: str = '0-0'):
        last_id = from_id
        while True:
            events = await self.redis.xread({stream: last_id}, count=100, block=1000)
            if not events:
                break
            for _, msgs in events:
                for msg_id, msg in msgs:
                    event = json.loads(msg['event'])
                    await handler(event)
                    last_id = msg_id

    async def get_events(self, stream: str, count: int = 100):
        return await self.redis.xrevrange(stream, count=count)

# --- EventConsumer ---
class EventConsumer:
    def __init__(self, redis_url: str, stream: str, group: str, consumer: str, handler: Callable[[dict], Any], max_retries: int = 5):
        self.redis_url = redis_url
        self.stream = stream
        self.group = group
        self.consumer = consumer
        self.handler = handler
        self.max_retries = max_retries
        self.redis = None

    async def connect(self):
        self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)
        try:
            await self.redis.xgroup_create(self.stream, self.group, id='0-0', mkstream=True)
        except Exception:
            pass  # Group may already exist

    async def consume(self):
        while True:
            try:
                events = await self.redis.xreadgroup(self.group, self.consumer, streams={self.stream: '>'}, count=10, block=5000)
                for stream, msgs in events:
                    for msg_id, msg in msgs:
                        event = json.loads(msg['event'])
                        await self._process_event(msg_id, event)
            except Exception as e:
                logger.error(f"Consumer error: {e}")
                await asyncio.sleep(2)

    async def _process_event(self, msg_id, event):
        retries = 0
        while retries < self.max_retries:
            try:
                await self.handler(event)
                await self.redis.xack(self.stream, self.group, msg_id)
                return
            except Exception as e:
                retries += 1
                logger.warning(f"Retry {retries} for event {msg_id}: {e}")
                await asyncio.sleep(2 ** retries)
        # Move to dead letter
        await self.redis.xadd(STREAMS['dead_letter'], {"event": json.dumps(event), "original_id": msg_id})
        await self.redis.xack(self.stream, self.group, msg_id)
        logger.error(f"Event {msg_id} moved to dead letter queue")

# --- EventRouter ---
class EventRouter:
    def __init__(self):
        self.routes: Dict[str, Callable[[dict], Any]] = {}

    def register(self, event_type: str, handler: Callable[[dict], Any]):
        self.routes[event_type] = handler

    async def route(self, event: dict):
        event_type = event.get('event_type')
        handler = self.routes.get(event_type)
        if handler:
            await handler(event)
        else:
            logger.warning(f"No handler registered for event type: {event_type}")

# --- EventMonitor ---
class EventMonitor:
    def __init__(self, redis):
        self.redis = redis

    async def get_metrics(self):
        metrics = {}
        for name, stream in STREAMS.items():
            try:
                metrics[stream] = await self.redis.xlen(stream)
            except Exception:
                metrics[stream] = None
        return metrics

    async def alert_on_dead_letter(self, threshold: int = 1):
        count = await self.redis.xlen(STREAMS['dead_letter'])
        if count >= threshold:
            logger.error(f"Dead letter queue has {count} events! Immediate attention required.")

# --- Testing Utilities ---
async def test_event_system():
    redis_url = "redis://localhost:6379/0"
    publisher = EventPublisher(redis_url)
    await publisher.connect()
    # Publish a test event
    await publisher.publish('user_registered', {
        'event_type': 'user_registered',
        'user_id': 1,
        'timestamp': datetime.utcnow(),
        'payload': {'email': 'test@example.com'}
    })
    # Consume the event
    async def handler(event):
        print(f"Handled event: {event}")
    consumer = EventConsumer(redis_url, STREAMS['user'], 'test_group', 'test_consumer', handler)
    await consumer.connect()
    await asyncio.wait_for(consumer.consume(), timeout=5)

# --- Exports ---
__all__ = [
    'EventPublisher', 'EventConsumer', 'EventRouter', 'EventStore', 'EventMonitor',
    'UserEvent', 'DocumentEvent', 'CollaborationEvent', 'STREAMS', 'EVENT_SCHEMAS'
]
