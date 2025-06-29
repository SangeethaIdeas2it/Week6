import os
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Set, Any
import aioredis
import logging
from datetime import datetime
import uvicorn

# --- Configuration ---
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DOCUMENT_SERVICE_URL = os.getenv("DOCUMENT_SERVICE_URL", "http://localhost:8001")

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# --- FastAPI App Setup ---
app = FastAPI(title="Collaboration Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Redis Setup ---
redis = None

# --- In-memory Connection State ---
sessions: Dict[str, Set[WebSocket]] = {}  # document_id -> set of WebSocket
user_sessions: Dict[str, str] = {}  # websocket id -> document_id
user_cursors: Dict[str, Dict[str, Any]] = {}  # document_id -> {user_id: cursor_info}

# --- Operational Transformation (OT) ---
class Operation:
    def __init__(self, pos: int, text: str, op_type: str):
        self.pos = pos
        self.text = text
        self.op_type = op_type  # 'insert' or 'delete'

    def to_dict(self):
        return {"pos": self.pos, "text": self.text, "op_type": self.op_type}

    @staticmethod
    def from_dict(d):
        return Operation(d["pos"], d["text"], d["op_type"])

# Simple OT for demonstration (production: use robust library)
def apply_operation(content: str, op: Operation) -> str:
    if op.op_type == "insert":
        return content[:op.pos] + op.text + content[op.pos:]
    elif op.op_type == "delete":
        return content[:op.pos] + content[op.pos + len(op.text):]
    return content

def transform(op1: Operation, op2: Operation) -> Operation:
    # Simplified: if op2 is before op1, shift op1
    if op2.op_type == "insert" and op2.pos <= op1.pos:
        op1.pos += len(op2.text)
    elif op2.op_type == "delete" and op2.pos < op1.pos:
        op1.pos -= min(len(op2.text), op1.pos - op2.pos)
    return op1

# --- WebSocket Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, document_id: str, websocket: WebSocket):
        await websocket.accept()
        if document_id not in self.active_connections:
            self.active_connections[document_id] = set()
        self.active_connections[document_id].add(websocket)

    def disconnect(self, document_id: str, websocket: WebSocket):
        if document_id in self.active_connections:
            self.active_connections[document_id].discard(websocket)
            if not self.active_connections[document_id]:
                del self.active_connections[document_id]

    async def broadcast(self, document_id: str, message: dict):
        if document_id in self.active_connections:
            for connection in list(self.active_connections[document_id]):
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

manager = ConnectionManager()

# --- Redis Stream Utilities ---
async def publish_event(document_id: str, event: dict):
    await redis.xadd(f"doc_stream:{document_id}", {"event": json.dumps(event)})

async def listen_events(document_id: str, last_id: str = "$"):
    while True:
        events = await redis.xread({f"doc_stream:{document_id}": last_id}, block=1000, count=10)
        for stream, msgs in events:
            for msg_id, msg in msgs:
                event = json.loads(msg[b"event"].decode())
                yield event
                last_id = msg_id

# --- WebSocket Endpoint ---
@app.websocket("/ws/collaborate/{document_id}")
async def websocket_endpoint(websocket: WebSocket, document_id: str, user_id: str):
    await manager.connect(document_id, websocket)
    try:
        # Notify join
        join_event = {"type": "user_joined", "user_id": user_id, "timestamp": datetime.utcnow().isoformat()}
        await manager.broadcast(document_id, join_event)
        await publish_event(document_id, join_event)
        # Listen for messages
        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")
            if event_type == "document_change":
                op = Operation.from_dict(data["operation"])
                # Apply OT (simplified)
                # In production, fetch latest content and transform
                await publish_event(document_id, data)
                await manager.broadcast(document_id, data)
            elif event_type == "cursor_position":
                user_cursors.setdefault(document_id, {})[user_id] = data["cursor"]
                cursor_event = {"type": "cursor_position", "user_id": user_id, "cursor": data["cursor"], "timestamp": datetime.utcnow().isoformat()}
                await manager.broadcast(document_id, cursor_event)
            elif event_type == "document_saved":
                # Persist to Document Service (simulate)
                await publish_event(document_id, data)
                await manager.broadcast(document_id, data)
            elif event_type == "undo" or event_type == "redo":
                # Handle undo/redo (not implemented in this demo)
                pass
    except WebSocketDisconnect:
        manager.disconnect(document_id, websocket)
        leave_event = {"type": "user_left", "user_id": user_id, "timestamp": datetime.utcnow().isoformat()}
        await manager.broadcast(document_id, leave_event)
        await publish_event(document_id, leave_event)
    except Exception as exc:
        logger.error(f"WebSocket error: {exc}")
        await websocket.close()

# --- Health Check ---
@app.get("/health")
async def health():
    return {"status": "ok"}

# --- Startup/Shutdown Events ---
@app.on_event("startup")
async def startup():
    global redis
    redis = await aioredis.from_url(REDIS_URL, decode_responses=False)
    logger.info("Collaboration Service started.")

@app.on_event("shutdown")
async def shutdown():
    await redis.close()
    logger.info("Collaboration Service shutdown.")

# --- Run the app ---
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
