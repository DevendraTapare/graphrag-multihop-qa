"""Real HTTP and isolated Stage 5 outage/recovery; preserve both database volumes."""

import concurrent.futures
import json
import os
import socket
import subprocess
import time

import httpx
import psutil

from app.aligned.components import AlignedComponents
from app.core.config import Settings
from app.db.neo4j import GraphDatabaseClient
from app.evaluation.baseline import percentile
from app.graph.fixtures import ROOT
from scripts.stage4_support import check_graph_snapshot
from scripts.stage5_support import aligned_snapshot, check_history, read, save
from scripts.verify_aligned import snapshot_digest
from scripts.verify_graph import HERO
from scripts.verify_runtime import start_api, stop_api, wait_for_status


def compose(*args):
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "compose.stage5.yml",
            "-p",
            os.environ.get("STAGE5_COMPOSE_PROJECT", "graphrag-stage5"),
            "--progress",
            "plain",
            *args,
        ],
        check=True,
        timeout=180,
    )


def stop_owned_api(process):
    try:
        descendants = psutil.Process(process.pid).children(recursive=True)
    except psutil.NoSuchProcess:
        descendants = []
    stop_api(process)
    for child in descendants:
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(descendants, timeout=3)
    for child in alive:
        child.kill()


def main():
    if not (Settings().app_env == "development"):
        raise AssertionError()
    check_history()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    db = GraphDatabaseClient(Settings())
    try:
        historical = check_graph_snapshot(db)
    finally:
        db.close()
    results = {"historical_before": historical}
    log_path = ROOT / ".pytest_cache/stage5-runtime-api.log"
    log_path.parent.mkdir(exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        started = time.perf_counter()
        process = start_api(port, log)
        stopped = False
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=120) as client:
                results["health_connected"] = wait_for_status(client, "/health", 200)
                results["startup_to_health_ms"] = (time.perf_counter() - started) * 1000
                results["main_ready"] = wait_for_status(client, "/ready", 200)
                results["aligned_ready"] = wait_for_status(client, "/api/v1/rag/aligned/ready", 200)

                def query(
                    mode="hybrid",
                    question="Which database does Project Atlas use?",
                    answer="PostgreSQL",
                    status=200,
                ):
                    body = {"question": question}
                    if mode != "aligned/graph":
                        body["top_k"] = 5
                    r = client.post(f"/api/v1/rag/{mode}/query", json=body)
                    value = r.json()
                    if not (r.status_code == status):
                        raise AssertionError(value)
                    if not (r.headers["X-Request-ID"] == value["request_id"]):
                        raise AssertionError()
                    if status == 200:
                        if not (value["answer"] == answer and value["citations"]):
                            raise AssertionError()
                    else:
                        if not ("answer" not in value and "reasoning_paths" not in value):
                            raise AssertionError()
                    return value

                results["connected_modes"] = {
                    m: query(m) for m in ("aligned/vector", "aligned/graph", "hybrid")
                }
                results["connected_three_hop"] = query(question=HERO, answer="AWS")
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                    responses = list(pool.map(lambda _: query(), range(8)))
                results["concurrent_requests"] = len(responses)
                results["concurrent_configuration"] = {
                    "workers": 4,
                    "requests": 8,
                    "question": "Which database does Project Atlas use?",
                    "top_k": 5,
                    "max_hops": 3,
                }
                results["concurrent_latency_ms"] = {
                    phase: {
                        "p50": percentile([r["latency_ms"][phase] for r in responses], 0.5),
                        "p95": percentile([r["latency_ms"][phase] for r in responses], 0.95),
                    }
                    for phase in responses[0]["latency_ms"]
                }
                results["unique_request_ids"] = len({r["request_id"] for r in responses})
                if not (results["unique_request_ids"] == 8):
                    raise AssertionError()
                invalid = [
                    {"question": " "},
                    {"question": HERO, "top_k": 11},
                    {"question": HERO, "max_hops": 4},
                ]
                results["invalid_statuses"] = [
                    client.post("/api/v1/rag/hybrid/query", json=b).status_code for b in invalid
                ]
                if not (results["invalid_statuses"] == [422] * 3):
                    raise AssertionError()
                stopped = True
                compose("stop", "neo4j")
                results["health_outage"] = wait_for_status(client, "/health", 200)
                results["historical_ready_outage"] = wait_for_status(client, "/ready", 200)
                results["aligned_ready_outage"] = wait_for_status(
                    client, "/api/v1/rag/aligned/ready", 503
                )
                results["hybrid_outage"] = query(status=503)
                results["graph_outage"] = query("aligned/graph", status=503)
                stop_owned_api(process)
                process = start_api(port, log)
                results["restart_health_outage"] = wait_for_status(client, "/health", 200)
                results["restart_aligned_ready_outage"] = wait_for_status(
                    client, "/api/v1/rag/aligned/ready", 503
                )
                results["restart_hybrid_outage"] = query(status=503)
                compose("up", "-d", "--wait", "neo4j")
                stopped = False
                results["aligned_ready_recovered"] = wait_for_status(
                    client, "/api/v1/rag/aligned/ready", 200
                )
                results["recovered"] = query()
                results["recovered_three_hop"] = query(question=HERO, answer="AWS")
        finally:
            try:
                if stopped:
                    compose("up", "-d", "--wait", "neo4j")
            finally:
                stop_owned_api(process)
    db = GraphDatabaseClient(Settings())
    try:
        results["historical_after"] = check_graph_snapshot(db)
    finally:
        db.close()
    components = AlignedComponents(Settings())
    try:
        results["aligned_snapshot_sha256"] = snapshot_digest(aligned_snapshot(components.db))
        if not (
            results["aligned_snapshot_sha256"] == read("provenance_audit.json")["snapshot_sha256"]
        ):
            raise AssertionError()
    finally:
        components.close()
    save("runtime_verification.json", results)
    print(json.dumps({k: v for k, v in results.items() if not isinstance(v, dict)}, indent=2))


if __name__ == "__main__":
    main()
