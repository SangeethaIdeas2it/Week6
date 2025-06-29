import asyncio
import websockets
import json
import random

WS_URL = "ws://localhost:8002/ws/collaborate/1?user_id={user_id}"

async def simulate_user(user_id):
    uri = WS_URL.format(user_id=user_id)
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"type": "user_joined", "user_id": user_id}))
        for _ in range(10):
            await ws.send(json.dumps({
                "type": "document_change",
                "operation": {"pos": random.randint(0, 100), "text": "A", "op_type": "insert"},
                "user_id": user_id
            }))
            await asyncio.sleep(random.uniform(0.01, 0.1))
        await ws.send(json.dumps({"type": "user_left", "user_id": user_id}))

async def main():
    users = 1000
    await asyncio.gather(*(simulate_user(i) for i in range(users)))

if __name__ == "__main__":
    asyncio.run(main()) 