"""Actual isolated Neo4j stop/restart and HTTP recovery; historical volumes untouched."""

import concurrent.futures
import json
import socket
import subprocess
import sys
import threading
import time

import httpx
import psutil

from app.db.neo4j import GraphDatabaseClient
from scripts.performance_stage6 import probes
from scripts.stage6_runtime import Components, challenge_settings
from scripts.stage6_support import OUT, check_freeze, save
from scripts.verify_runtime import stop_api, wait_for_status


def compose(*arguments):
    started = time.perf_counter()
    result = subprocess.run(
        ["docker", "compose", "-f", "compose.stage6.yml", "-p", "graphrag-stage6", *arguments],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return {"wall_ms": (time.perf_counter() - started) * 1000, "output": result.stdout.strip()}


def start_api(port, log):
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "scripts.stage6_runtime:api",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--no-access-log",
        ],
        stdout=log,
        stderr=log,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )


def cleanup_api(process):
    try:
        children = psutil.Process(process.pid).children(recursive=True)
    except psutil.NoSuchProcess:
        children = []
    stop_api(process)
    for child in children:
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(children, timeout=3)
    for child in alive:
        child.kill()


def timed(call):
    start = time.perf_counter()
    try:
        response = call()
        return {"wall_ms": (time.perf_counter() - start) * 1000, "response": response}
    except Exception as exc:
        return {
            "wall_ms": (time.perf_counter() - start) * 1000,
            "error": getattr(exc, "category", type(exc).__name__),
        }


class PausingDatabase(GraphDatabaseClient):
    """Test hook after an actual path read, before its remaining proof/revalidation."""

    def __init__(self):
        super().__init__(challenge_settings())
        self.pause = False
        self.entered, self.release = threading.Event(), threading.Event()

    def execute(self, cypher, parameters=None, *, timeout=None):
        result = super().execute(cypher, parameters, timeout=timeout)
        if self.pause and "MATCH p=" in cypher:
            self.pause = False
            self.entered.set()
            if not (self.release.wait(30)):
                raise AssertionError("Recovery coordinator stalled")
        return result


def main():
    check_freeze()
    questions, _ = probes()
    question = questions[2]
    db = PausingDatabase()
    components = Components(db)
    result = {
        "driver_read_retry_seconds": 0,
        "ingestion_retry_seconds": 3,
        "connection_acquisition_timeout_seconds": components.settings.neo4j_connection_timeout,
        "graph_request_budget_seconds": components.settings.graph_request_timeout,
        "hybrid_request_budget_seconds": 60,
        "inflight_method": "Stop isolated database after first real path read, "
        "while same request awaits further proof; not a simulated DB failure",
    }
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    log_path = OUT / "recovery-api.log"
    with log_path.open("w", encoding="utf-8") as log:
        process = start_api(port, log)
        stopped = False
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=120) as client:
                start = time.perf_counter()
                result["api_start_health"] = wait_for_status(client, "/health", 200)
                result["api_startup_ms"] = (time.perf_counter() - start) * 1000
                result["ready_before"] = wait_for_status(client, "/api/v1/rag/aligned/ready", 200)

                def http_query(mode="hybrid", q=question):
                    body = {"question": q}
                    if mode != "aligned/graph":
                        body["top_k"] = 5
                    response = client.post(f"/api/v1/rag/{mode}/query", json=body)
                    value = response.json()
                    if not (response.headers["X-Request-ID"] == value["request_id"]):
                        raise AssertionError()
                    return {"status": response.status_code, "body": value}

                result["http_cold_first"] = timed(http_query)
                result["http_modes_before"] = {
                    m: timed(lambda m=m: http_query(m))
                    for m in ("aligned/graph", "aligned/vector", "hybrid")
                }
                if not (result["http_cold_first"]["response"]["status"] == 200):
                    raise AssertionError()
                result["warm_model_before"] = timed(
                    lambda: components.query("hybrid_graph_vector", question)
                )
                db.pause = True
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(timed, lambda: components.query("graph_only", question))
                    if not (db.entered.wait(30)):
                        raise AssertionError()
                    stopped = True
                    result["stop"] = compose("stop", "-t", "5", "neo4j")
                    db.release.set()
                    result["interrupted_request"] = future.result(timeout=40)
                if "error" not in result["interrupted_request"]:
                    raise AssertionError()
                result["ready_outage"] = wait_for_status(client, "/api/v1/rag/aligned/ready", 503)
                result["health_outage"] = wait_for_status(client, "/health", 200)
                result["unavailable_before_query"] = {
                    m: timed(lambda m=m: http_query(m))
                    for m in ("aligned/graph", "aligned/vector", "hybrid")
                }
                for probe in result["unavailable_before_query"].values():
                    reply = probe["response"]
                    if not (reply["status"] == 503 and "answer" not in reply["body"]):
                        raise AssertionError()
                cleanup_api(process)
                process = start_api(port, log)
                result["restart_api_during_outage_health"] = wait_for_status(client, "/health", 200)
                result["restart_api_during_outage_ready"] = wait_for_status(
                    client, "/api/v1/rag/aligned/ready", 503
                )
                start = time.perf_counter()
                result["start_command"] = compose("start", "neo4j")
                deadline = time.monotonic() + 120
                attempts = 0
                while not db.ready() and time.monotonic() < deadline:
                    attempts += 1
                    time.sleep(0.5)
                if not (db.ready()):
                    raise AssertionError("Recovery failed")
                result["startup_to_bolt_ready_ms"] = (time.perf_counter() - start) * 1000
                result["readiness_attempts"] = attempts + 1
                stopped = False
                result["index_readiness"] = timed(components.vector.repo.require_index)
                result["warm_model_first_after_recovery"] = {
                    m: timed(lambda m=m: components.query(m, question))
                    for m in ("graph_only", "vector_only", "hybrid_graph_vector")
                }
                fresh = GraphDatabaseClient(challenge_settings())
                try:
                    result["fresh_connection_readiness"] = timed(fresh.ready)
                finally:
                    fresh.close()
                result["http_ready_recovered"] = wait_for_status(
                    client, "/api/v1/rag/aligned/ready", 200
                )
                result["http_fresh_model_first_after_recovery"] = timed(http_query)
                result["http_subsequent_warm"] = [timed(http_query) for _ in range(5)]
                if not (
                    all(r["response"]["status"] == 200 for r in result["http_subsequent_warm"])
                ):
                    raise AssertionError()
                save("recovery_results.json", result)
                print(
                    json.dumps(
                        {
                            "startup_to_bolt_ready_ms": result["startup_to_bolt_ready_ms"],
                            "fresh_model_http_ms": result["http_fresh_model_first_after_recovery"][
                                "wall_ms"
                            ],
                            "warm_model_hybrid_ms": result["warm_model_first_after_recovery"][
                                "hybrid_graph_vector"
                            ]["wall_ms"],
                        }
                    )
                )
        finally:
            db.release.set()
            if stopped:
                compose("start", "neo4j")
            cleanup_api(process)
            components.close()
            # Retain partial failures if an assertion or environment fault interrupts the exercise.
            save("recovery_attempt.json", result)


if __name__ == "__main__":
    main()
