import time
import threading
import logging
import psutil
import asyncio
from typing import Dict, Any, Callable, List, Optional
from collections import defaultdict, deque
import numpy as np
from sklearn.ensemble import IsolationForest

logger = logging.getLogger("PerformanceMonitor")
logging.basicConfig(level=logging.INFO)

# --- Real-Time Metrics Collector ---
class MetricsCollector:
    def __init__(self):
        self.metrics = defaultdict(lambda: deque(maxlen=1000))
        self.lock = threading.Lock()

    def record(self, category: str, metric: str, value: float):
        with self.lock:
            self.metrics[(category, metric)].append((time.time(), value))

    def get_series(self, category: str, metric: str) -> List[float]:
        with self.lock:
            return [v for _, v in self.metrics[(category, metric)]]

    def get_latest(self, category: str, metric: str) -> Optional[float]:
        with self.lock:
            if self.metrics[(category, metric)]:
                return self.metrics[(category, metric)][-1][1]
            return None

# --- Anomaly Detection (ML-based) ---
class AnomalyDetector:
    def __init__(self):
        self.models = {}
        self.window = 100

    def fit(self, series: List[float], category: str, metric: str):
        if len(series) < self.window:
            return
        X = np.array(series[-self.window:]).reshape(-1, 1)
        model = IsolationForest(contamination=0.05)
        model.fit(X)
        self.models[(category, metric)] = model

    def detect(self, series: List[float], category: str, metric: str) -> List[int]:
        model = self.models.get((category, metric))
        if not model or len(series) < self.window:
            return []
        X = np.array(series[-self.window:]).reshape(-1, 1)
        preds = model.predict(X)
        return [i for i, p in enumerate(preds) if p == -1]

# --- Predictive Alerting ---
class PredictiveAlerter:
    def __init__(self):
        self.thresholds = {}

    def set_threshold(self, category: str, metric: str, threshold: float):
        self.thresholds[(category, metric)] = threshold

    def check(self, value: float, category: str, metric: str) -> bool:
        threshold = self.thresholds.get((category, metric))
        if threshold is not None and value > threshold:
            logger.warning(f"ALERT: {category}/{metric} exceeded threshold {threshold}: {value}")
            return True
        return False

# --- Trend Analysis & Optimization ---
class TrendAnalyzer:
    def analyze(self, series: List[float]) -> Dict[str, Any]:
        if not series:
            return {}
        arr = np.array(series)
        trend = np.polyfit(range(len(arr)), arr, 1)[0] if len(arr) > 1 else 0
        return {
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "trend": float(trend),
        }

    def recommend(self, category: str, metric: str, analysis: Dict[str, Any]) -> str:
        if analysis.get("trend", 0) > 0.1:
            return f"{category}/{metric} is increasing. Investigate scaling or optimization."
        if analysis.get("std", 0) > 2 * analysis.get("mean", 1):
            return f"{category}/{metric} is highly variable. Investigate root cause."
        return f"{category}/{metric} is stable."

# --- Business Impact Assessment ---
class BusinessImpactAssessor:
    def assess(self, perf_metric: float, user_metric: float) -> str:
        if perf_metric > 2 * user_metric:
            return "Performance issue is likely impacting user experience or revenue."
        return "No significant business impact detected."

# --- Main Performance Monitor ---
class PerformanceMonitor:
    def __init__(self):
        self.collector = MetricsCollector()
        self.anomaly = AnomalyDetector()
        self.alerter = PredictiveAlerter()
        self.trend = TrendAnalyzer()
        self.business = BusinessImpactAssessor()
        self.dashboard_data = {}

    def record_metric(self, category: str, metric: str, value: float):
        self.collector.record(category, metric, value)
        # Fit anomaly model if enough data
        series = self.collector.get_series(category, metric)
        self.anomaly.fit(series, category, metric)
        # Predictive alerting
        self.alerter.check(value, category, metric)

    def analyze_metric(self, category: str, metric: str) -> Dict[str, Any]:
        series = self.collector.get_series(category, metric)
        analysis = self.trend.analyze(series)
        recommendation = self.trend.recommend(category, metric, analysis)
        anomalies = self.anomaly.detect(series, category, metric)
        return {
            "analysis": analysis,
            "recommendation": recommendation,
            "anomalies": anomalies,
        }

    def assess_business_impact(self, perf_metric: float, user_metric: float) -> str:
        return self.business.assess(perf_metric, user_metric)

    def get_dashboard(self) -> Dict[str, Any]:
        # Aggregate latest metrics and recommendations
        dashboard = {}
        for (category, metric), series in self.collector.metrics.items():
            latest = self.collector.get_latest(category, metric)
            analysis = self.analyze_metric(category, metric)
            dashboard[(category, metric)] = {
                "latest": latest,
                **analysis
            }
        return dashboard

    def set_alert_threshold(self, category: str, metric: str, threshold: float):
        self.alerter.set_threshold(category, metric, threshold)

# --- System Resource Monitoring (Infrastructure) ---
async def monitor_system_resources(perf_monitor: PerformanceMonitor, interval=5):
    while True:
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        perf_monitor.record_metric("infrastructure", "cpu", cpu)
        perf_monitor.record_metric("infrastructure", "memory", mem)
        perf_monitor.record_metric("infrastructure", "disk", disk)
        await asyncio.sleep(interval)

# --- Example Usage ---
# perf_monitor = PerformanceMonitor()
# perf_monitor.record_metric("application", "api_response_time", 120)
# perf_monitor.set_alert_threshold("application", "api_response_time", 200)
# dashboard = perf_monitor.get_dashboard()
# print(dashboard)
# asyncio.run(monitor_system_resources(perf_monitor))
