"""Real loopback HTTP, Neo4j outage, API restart, recovery; always restore Compose."""

import concurrent.futures
import json
import socket
import time

import httpx

from app.core.config import Settings
from app.db.neo4j import GraphDatabaseClient
from scripts.stage4_support import OUT, check_graph_snapshot, check_runtime_freeze
from scripts.verify_graph import HERO
from scripts.verify_runtime import compose, start_api, stop_api, wait_for_status


def main():
    if not (Settings().app_env == "development"):
        raise AssertionError()
    check_runtime_freeze()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    results = {}
    db = GraphDatabaseClient(Settings())
    try:
        results["graph_snapshot_before"] = check_graph_snapshot(db)
    finally:
        db.close()
    with (OUT / "runtime-api.log").open("w") as log:
        started = time.perf_counter()
        process = start_api(port, log)
        stopped = False
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=60) as client:
                results["health_connected"] = wait_for_status(client, "/health", 200)
                results["startup_to_health_ms"] = (time.perf_counter() - started) * 1000
                results["ready_connected"] = wait_for_status(client, "/api/v1/ready", 200)

                def query(expected=200):
                    response = client.post(
                        "/api/v1/rag/graph/query", json={"question": HERO, "max_hops": 3}
                    )
                    body = response.json()
                    if not (response.status_code == expected):
                        raise AssertionError(body)
                    if not (response.headers["X-Request-ID"] == body["request_id"]):
                        raise AssertionError()
                    if expected == 200:
                        if not (body["answer"] == "AWS" and body["hop_count"] == 3):
                            raise AssertionError()
                        if not (body["reasoning_paths"] and body["citations"]):
                            raise AssertionError()
                    else:
                        if not ("answer" not in body and "reasoning_paths" not in body):
                            raise AssertionError()
                        if not (body["error"] == "Graph database unavailable"):
                            raise AssertionError()
                    return body

                results["connected_query"] = query()
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                    responses = list(pool.map(lambda _: query(), range(8)))
                results["concurrent_http_requests"] = len(responses)
                results["concurrent_unique_request_ids"] = len({r["request_id"] for r in responses})
                results["bad_depth"] = client.post(
                    "/api/v1/rag/graph/query", json={"question": HERO, "max_hops": 4}
                ).status_code
                if not (results["bad_depth"] == 422):
                    raise AssertionError()
                stopped = True
                compose("stop", "neo4j")
                results["health_outage"] = wait_for_status(client, "/health", 200)
                results["ready_outage"] = wait_for_status(client, "/api/v1/ready", 503)
                results["outage_query"] = query(503)
                stop_api(process)
                process = start_api(port, log)
                results["health_start_during_outage"] = wait_for_status(client, "/health", 200)
                results["ready_start_during_outage"] = wait_for_status(client, "/api/v1/ready", 503)
                results["outage_query_after_api_restart"] = query(503)
                compose("up", "-d", "--wait", "neo4j")
                stopped = False
                results["ready_recovered"] = wait_for_status(client, "/api/v1/ready", 200)
                results["recovered_query"] = query()
        finally:
            try:
                if stopped:
                    compose("up", "-d", "--wait", "neo4j")
            finally:
                stop_api(process)
    db = GraphDatabaseClient(Settings())
    try:
        results["graph_snapshot_after"] = check_graph_snapshot(db)
    finally:
        db.close()
    (OUT / "runtime_verification.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({k: v for k, v in results.items() if "query" not in k}, indent=2))


if __name__ == "__main__":
    main()
