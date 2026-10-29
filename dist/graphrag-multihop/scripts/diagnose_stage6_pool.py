"""One supplementary bounded burst to identify high-concurrency database errors.

This adds summary/cause instrumentation, never changes limits, queries or retries.
Primary load results remain unchanged. No final challenge labels are read.
"""

import concurrent.futures
import threading
import time
from collections import Counter

from neo4j import Query
from neo4j.exceptions import DriverError, Neo4jError

from app.db.neo4j import DatabaseUnavailable, GraphDatabaseClient
from scripts.performance_stage6 import probes, quantiles
from scripts.stage6_runtime import Components, challenge_settings
from scripts.stage6_support import check_freeze, save


class SummaryDatabase(GraphDatabaseClient):
    def __init__(self):
        super().__init__(challenge_settings())
        self.local = threading.local()

    def execute(self, cypher, parameters=None, *, timeout=None):
        try:
            with self.driver.session(database=self.settings.neo4j_database) as session:
                result = session.run(
                    Query(cypher, timeout=timeout or self.settings.neo4j_query_timeout),
                    parameters=dict(parameters or {}),
                )
                rows = [record.data() for record in result]
                summary = result.consume()
                if hasattr(self.local, "summaries"):
                    self.local.summaries.append(
                        {
                            "available_after_ms": summary.result_available_after,
                            "consumed_after_ms": summary.result_consumed_after,
                        }
                    )
                return rows
        except (DriverError, Neo4jError, OSError) as exc:
            raise DatabaseUnavailable("Graph database operation failed") from exc


def chain(exc):
    values = []
    while exc is not None and len(values) < 6:
        message = str(exc).casefold()
        values.append(
            {
                "type": type(exc).__name__,
                "code": getattr(exc, "code", None),
                "pool_acquisition": "pool" in message or "acquisition" in message,
                "timeout": "timeout" in message or "timed out" in message,
                "defunct_connection": "defunct" in message,
            }
        )
        exc = exc.__cause__
    return values


def main():
    check_freeze()
    db = SummaryDatabase()
    components = Components(db)
    questions, _ = probes()
    try:
        for q in questions[:3]:
            components.query("graph_only", q)
        barrier = threading.Barrier(50)

        def request(i):
            barrier.wait(15)
            db.local.summaries = []
            start = time.perf_counter()
            try:
                response = components.query("graph_only", questions[i % 4])
                outcome, causes = response["reason"], []
            except Exception as exc:
                outcome, causes = getattr(exc, "category", type(exc).__name__), chain(exc)
            return {
                "probe": i % 4,
                "outcome": outcome,
                "causes": causes,
                "wall_ms": (time.perf_counter() - start) * 1000,
                "server_summaries": db.local.summaries,
            }

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as pool:
            rows = list(pool.map(request, range(50)))
        summaries = [s for r in rows for s in r["server_summaries"]]
        save(
            "pool_diagnostic.json",
            {
                "users": 50,
                "requests": 50,
                "rounds": 1,
                "mode": "graph_only",
                "rows": rows,
                "outcomes": dict(Counter(r["outcome"] for r in rows)),
                "pool_acquisition_failures": sum(
                    any(c["pool_acquisition"] for c in r["causes"]) for r in rows
                ),
                "server_available_after_ms": quantiles(
                    [s["available_after_ms"] for s in summaries]
                ),
                "server_consumed_after_ms": quantiles([s["consumed_after_ms"] for s in summaries]),
                "note": "Supplementary burst after recovery; "
                "server summary times exclude pool wait. "
                "Not primary load numbers.",
            },
        )
        print("Supplementary 50-request driver cause/summary diagnostic recorded")
    finally:
        components.close()


if __name__ == "__main__":
    main()
