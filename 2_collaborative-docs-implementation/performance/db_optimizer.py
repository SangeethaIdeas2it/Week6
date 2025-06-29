import asyncpg
import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, Callable
from collections import defaultdict

logger = logging.getLogger("DBOptimizer")
logging.basicConfig(level=logging.INFO)

# --- Query Performance Monitoring ---
class QueryMonitor:
    def __init__(self):
        self.query_times = []
        self.slow_queries = []
        self.threshold_ms = 100  # Sub-100ms target

    def record(self, query: str, duration_ms: float):
        self.query_times.append(duration_ms)
        if duration_ms > self.threshold_ms:
            self.slow_queries.append((query, duration_ms))
            logger.warning(f"Slow query ({duration_ms:.2f}ms): {query}")

    def get_stats(self):
        if not self.query_times:
            return {}
        return {
            "avg_ms": sum(self.query_times) / len(self.query_times),
            "p95_ms": sorted(self.query_times)[int(0.95 * len(self.query_times)) - 1],
            "slow_queries": self.slow_queries[-10:],
        }

# --- Index Recommendation ---
class IndexAdvisor:
    def __init__(self):
        self.query_patterns = defaultdict(int)

    def record_query(self, query: str):
        self.query_patterns[query] += 1

    def recommend_indexes(self) -> List[str]:
        # Naive: recommend index for columns in WHERE/ORDER BY of frequent queries
        recommendations = []
        for query, count in self.query_patterns.items():
            if count > 5 and "WHERE" in query:
                # Extract columns (very basic)
                where_idx = query.find("WHERE")
                cols = query[where_idx:].split()
                for col in cols:
                    if col.isidentifier() and col not in ("AND", "OR"):
                        recommendations.append(f"CREATE INDEX IF NOT EXISTS idx_{col} ON ... ({col});")
        return recommendations

# --- Connection Pool Management ---
class ConnectionPoolManager:
    def __init__(self, dsn: str, min_size=5, max_size=20):
        self.dsn = dsn
        self.min_size = min_size
        self.max_size = max_size
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(dsn=self.dsn, min_size=self.min_size, max_size=self.max_size)
        logger.info("Connection pool created.")

    async def close(self):
        if self.pool:
            await self.pool.close()
            logger.info("Connection pool closed.")

    async def execute(self, query: str, *args, monitor: QueryMonitor = None, **kwargs):
        start = time.time()
        async with self.pool.acquire() as conn:
            result = await conn.execute(query, *args, **kwargs)
        duration = (time.time() - start) * 1000
        if monitor:
            monitor.record(query, duration)
        return result

    async def fetch(self, query: str, *args, monitor: QueryMonitor = None, **kwargs):
        start = time.time()
        async with self.pool.acquire() as conn:
            result = await conn.fetch(query, *args, **kwargs)
        duration = (time.time() - start) * 1000
        if monitor:
            monitor.record(query, duration)
        return result

# --- Query Plan Analysis ---
async def analyze_query_plan(pool: ConnectionPoolManager, query: str) -> str:
    async with pool.pool.acquire() as conn:
        plan = await conn.fetchval(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {query}")
        logger.info(f"Query plan for {query}:\n{plan}")
        return plan

# --- Schema Optimization ---
def recommend_partitioning(table: str, column: str) -> str:
    return f"Consider partitioning {table} by {column} for large datasets."

def recommend_denormalization(table: str, columns: List[str]) -> str:
    return f"Consider denormalizing columns {columns} in {table} for read-heavy workloads."

def recommend_archiving(table: str, age_column: str, days: int) -> str:
    return f"Archive rows in {table} where {age_column} > {days} days for better performance."

# --- Concurrency Optimization ---
class ConcurrencyOptimizer:
    @staticmethod
    def optimistic_locking_clause(version_column="version") -> str:
        return f"WHERE {version_column} = $1"  # Use in UPDATE/DELETE

    @staticmethod
    def deadlock_detection():
        return "Monitor pg_locks and log deadlocks for analysis."

    @staticmethod
    def transaction_isolation(level="repeatable read") -> str:
        return f"SET TRANSACTION ISOLATION LEVEL {level.upper()};"

    @staticmethod
    def bulk_operation_hint():
        return "Use COPY for bulk inserts/updates."

# --- Health Monitoring & Alerting ---
class DBHealthMonitor:
    def __init__(self, pool: ConnectionPoolManager):
        self.pool = pool

    async def check_health(self) -> Dict[str, Any]:
        try:
            async with self.pool.pool.acquire() as conn:
                await conn.execute("SELECT 1")
            return {"status": "healthy"}
        except Exception as e:
            logger.error(f"DB health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

# --- Main Optimizer Toolkit ---
class DBOptimizer:
    def __init__(self, dsn: str):
        self.monitor = QueryMonitor()
        self.index_advisor = IndexAdvisor()
        self.pool_manager = ConnectionPoolManager(dsn)
        self.health_monitor = DBHealthMonitor(self.pool_manager)
        self.concurrency = ConcurrencyOptimizer()

    async def connect(self):
        await self.pool_manager.connect()

    async def close(self):
        await self.pool_manager.close()

    async def execute(self, query: str, *args, **kwargs):
        self.index_advisor.record_query(query)
        return await self.pool_manager.execute(query, *args, monitor=self.monitor, **kwargs)

    async def fetch(self, query: str, *args, **kwargs):
        self.index_advisor.record_query(query)
        return await self.pool_manager.fetch(query, *args, monitor=self.monitor, **kwargs)

    async def analyze_query(self, query: str):
        return await analyze_query_plan(self.pool_manager, query)

    def recommend_indexes(self):
        return self.index_advisor.recommend_indexes()

    def get_query_stats(self):
        return self.monitor.get_stats()

    def recommend_partitioning(self, table, column):
        return recommend_partitioning(table, column)

    def recommend_denormalization(self, table, columns):
        return recommend_denormalization(table, columns)

    def recommend_archiving(self, table, age_column, days):
        return recommend_archiving(table, age_column, days)

    async def check_health(self):
        return await self.health_monitor.check_health()

# --- Example Usage ---
# async def main():
#     optimizer = DBOptimizer(dsn="postgresql://user:pass@localhost:5432/collabdocs")
#     await optimizer.connect()
#     await optimizer.execute("CREATE TABLE IF NOT EXISTS ...")
#     stats = optimizer.get_query_stats()
#     print(stats)
#     await optimizer.close()
#
# if __name__ == "__main__":
#     asyncio.run(main())
