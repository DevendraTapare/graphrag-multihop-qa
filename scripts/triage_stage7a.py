"""Repeat the exact Stage 6 bounded workload with exception/lock instrumentation.

Pool size is the only configuration variable. Original files/results are read-only.
Monkeypatches are local orchestration/instrumentation, not runtime source changes.
"""

import argparse
import threading
import time

from app.db.neo4j import GraphDatabaseClient
from scripts import performance_stage6 as original
from scripts.diagnose_stage6_pool import chain
from scripts.stage6_runtime import Components as OriginalComponents
from scripts.stage6_runtime import challenge_settings
from scripts.stage7a_support import OUT, check_research, save


class TimedLock:
    def __init__(self):
        self.inner = threading.Lock()
        self.local = threading.local()

    def acquire(self, *args, **kwargs):
        start = time.perf_counter()
        acquired = self.inner.acquire(*args, **kwargs)
        self.local.wait_ms = (time.perf_counter() - start) * 1000
        self.local.hold_ms = None
        self.local.start = time.perf_counter() if acquired else None
        return acquired

    def release(self):
        self.local.hold_ms = (time.perf_counter() - self.local.start) * 1000
        self.inner.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args):
        self.release()


def run(pool_size):
    check_research()
    name = f"load_pool{pool_size}_repeat.json"
    assert not (OUT / name).exists(), "Never overwrite a measured trial"
    databases, models = [], []

    class Database(original.MeteredDatabase):
        def __init__(self):
            GraphDatabaseClient.__init__(
                self, challenge_settings().model_copy(update={"neo4j_pool_size": pool_size})
            )
            self.local = threading.local()
            self.captured, self.events = [], []
            databases.append(self)
            started = time.perf_counter()
            attempts = 0
            deadline = time.monotonic() + 120
            while not self.ready() and time.monotonic() < deadline:
                attempts += 1
                time.sleep(1)
            assert self.ready(), "Database did not become ready before load warmup"
            save(
                f"pool{pool_size}_readiness.json",
                {
                    "attempts": attempts + 1,
                    "wall_ms": (time.perf_counter() - started) * 1000,
                    "exception_events": self.events,
                    "note": "Bounded pre-measurement polling; no measured-request retries added",
                },
            )
            self.events.clear()

        def execute(self, *args, **kwargs):
            try:
                return super().execute(*args, **kwargs)
            except Exception as exc:
                self.events.append(
                    {"thread": threading.current_thread().name, "causes": chain(exc)}
                )
                raise

    class Model(original.MeteredModel):
        def __init__(self):
            super().__init__()
            self.model.lock = TimedLock()
            self.events = []
            models.append(self)

        def encode(self, texts):
            try:
                return super().encode(texts)
            finally:
                if threading.current_thread().name.startswith("ThreadPoolExecutor"):
                    local = self.model.lock.local
                    self.events.append(
                        {
                            "wait_ms": getattr(local, "wait_ms", None),
                            "hold_ms": getattr(local, "hold_ms", None),
                        }
                    )

    def components(db, model):
        result = OriginalComponents(db, model)
        result.settings = db.settings  # Report actual driver pool, all other values identical.
        return result

    def capture(_name, value):
        current = value["results"][-1]
        current["exception_events"] = list(databases[0].events)
        current["embedding_lock_events"] = list(models[0].events)
        current["embedding_wait_ms"] = original.quantiles(
            [e["wait_ms"] for e in models[0].events if e["wait_ms"] is not None]
        )
        current["embedding_hold_ms"] = original.quantiles(
            [e["hold_ms"] for e in models[0].events if e["hold_ms"] is not None]
        )
        databases[0].events.clear()
        models[0].events.clear()
        value["trial"] = {
            "pool_size": pool_size,
            "acquisition_timeout_seconds": 3,
            "read_managed_retry_seconds": 0,
            "graph_request_seconds": 20,
            "hybrid_request_seconds": 60,
            "query_max_seconds": 10,
            "changes": "Pool size only; same two-wave workload and calibration probes",
            "instrumentation": "Exception cause flags; embedding lock wait/hold",
        }
        save(name, value)

    original.MeteredDatabase = Database
    original.MeteredModel = Model
    original.Components = components
    original.save = capture
    original.load()
    check_research()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool-size", type=int, choices=[10, 50], required=True)
    run(parser.parse_args().pool_size)
