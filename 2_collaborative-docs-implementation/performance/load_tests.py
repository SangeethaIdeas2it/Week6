import time
import random
import threading
from locust import HttpUser, TaskSet, task, between, events
from locust.env import Environment
from locust.stats import stats_printer, stats_history
import gevent
import websocket
import json
import logging

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LoadTests")

# --- WebSocket User Simulation ---
class WebSocketUser:
    def __init__(self, ws_url):
        self.ws_url = ws_url
        self.ws = None

    def connect(self):
        self.ws = websocket.create_connection(self.ws_url)

    def send(self, message):
        self.ws.send(json.dumps(message))
        return self.ws.recv()

    def close(self):
        if self.ws:
            self.ws.close()

# --- Locust TaskSets for User Behavior ---
class CollaborativeBehavior(TaskSet):
    def on_start(self):
        self.token = None
        self.user_id = None
        self.login()

    def login(self):
        email = f"user{random.randint(1, 10000)}@test.com"
        password = "TestPass123!"
        resp = self.client.post("/api/v1/auth/register", json={"email": email, "password": password})
        if resp.status_code == 201:
            resp = self.client.post("/api/v1/auth/login", data={"username": email, "password": password})
            if resp.status_code == 200:
                self.token = resp.json()["access_token"]
                self.user_id = resp.json().get("user_id", 1)

    @task(2)
    def create_document(self):
        if not self.token:
            return
        title = f"Doc {random.randint(1, 10000)}"
        content = "Hello World!"
        headers = {"Authorization": f"Bearer {self.token}"}
        self.client.post("/api/v1/documents/", json={"title": title, "content": content}, headers=headers)

    @task(2)
    def list_documents(self):
        if not self.token:
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        self.client.get("/api/v1/documents/", headers=headers)

    @task(1)
    def share_document(self):
        if not self.token:
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        # List docs, pick one, share with another user
        resp = self.client.get("/api/v1/documents/", headers=headers)
        if resp.status_code == 200 and resp.json():
            doc_id = resp.json()[0]["id"]
            self.client.post(f"/api/v1/documents/{doc_id}/share", json={"user_id": self.user_id, "permission": "read"}, headers=headers)

    @task(1)
    def websocket_collaboration(self):
        ws_url = "ws://localhost:8002/ws/collaborate?doc_id=1&user_id=1"
        try:
            ws_user = WebSocketUser(ws_url)
            ws_user.connect()
            ws_user.send({"action": "edit", "content": "Edit from load test"})
            ws_user.close()
        except Exception as e:
            logger.warning(f"WebSocket error: {e}")

# --- Locust User Classes ---
class CollaborativeUser(HttpUser):
    tasks = [CollaborativeBehavior]
    wait_time = between(1, 3)
    host = "http://localhost:8000"

# --- Custom Load Test Scenarios ---
def run_locust_scenario(user_count=100, spawn_rate=10, run_time="1m"):
    env = Environment(user_classes=[CollaborativeUser])
    env.create_local_runner()
    gevent.spawn(stats_printer(env.stats))
    gevent.spawn(stats_history, env.runner)
    env.runner.start(user_count, spawn_rate=spawn_rate)
    gevent.spawn_later(time.strptime(run_time, "%Mm")[-2], lambda: env.runner.quit())
    env.runner.greenlet.join()

# --- Stress Test Scenario ---
def stress_test():
    logger.info("Starting stress test: ramping up to 1000 users...")
    run_locust_scenario(user_count=1000, spawn_rate=100, run_time="2m")

# --- Baseline Test Scenario ---
def baseline_test():
    logger.info("Starting baseline test: single user...")
    run_locust_scenario(user_count=1, spawn_rate=1, run_time="1m")

# --- Scalability Test Scenario ---
def scalability_test():
    logger.info("Starting scalability test: 1 to 500 users...")
    run_locust_scenario(user_count=500, spawn_rate=20, run_time="3m")

# --- Real-World Simulation Scenario ---
def real_world_simulation():
    logger.info("Starting real-world simulation: collaborative editing...")
    run_locust_scenario(user_count=200, spawn_rate=10, run_time="2m")

# --- Performance Report Generation ---
def generate_report(env):
    stats = env.stats
    report = {
        "requests": stats.total.num_requests,
        "failures": stats.total.num_failures,
        "avg_response_time": stats.total.avg_response_time,
        "max_response_time": stats.total.max_response_time,
        "min_response_time": stats.total.min_response_time,
        "rps": stats.total.total_rps,
    }
    logger.info(f"Performance Report: {report}")
    return report

# --- Main Entrypoint ---
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Collaborative Docs Load Testing Suite")
    parser.add_argument("--scenario", choices=["baseline", "scalability", "stress", "realworld"], default="baseline")
    args = parser.parse_args()
    if args.scenario == "baseline":
        baseline_test()
    elif args.scenario == "scalability":
        scalability_test()
    elif args.scenario == "stress":
        stress_test()
    elif args.scenario == "realworld":
        real_world_simulation()
