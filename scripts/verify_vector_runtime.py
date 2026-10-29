"""Real HTTP startup, sequential Compose outage/recovery, and safe vector errors."""

import concurrent.futures
import json
import socket
from pathlib import Path

import httpx

from app.core.config import Settings
from scripts.verify_runtime import compose, start_api, stop_api, wait_for_status


def main():
    if Settings().app_env != "development":
        raise SystemExit("Runtime outage verification requires development mode")
    directory = Path("reports/stage3")
    directory.mkdir(parents=True, exist_ok=True)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = None
    stopped = False
    body = {"question": "Which database does Project Atlas use?", "top_k": 5}
    results = {}
    # Logs are development-only ignored artifacts, never copied into reports.
    with Path("reports/stage3-runtime.log").open("w", encoding="utf-8") as log:
        try:
            process = start_api(port, log)
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=210) as client:
                results["health_connected"] = wait_for_status(client, "/health", 200)
                results["ready_connected"] = wait_for_status(client, "/ready", 200)
                result = client.post("/api/v1/rag/vector/query", json=body)
                assert result.status_code == 200, result.text
                assert result.json()["answer"] == "PostgreSQL"
                assert result.json()["citations"] and result.json()["retrieved_chunks"]
                results["vector_connected"] = result.json()
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
                    responses = list(
                        pool.map(
                            lambda _: client.post("/api/v1/rag/vector/query", json=body), range(6)
                        )
                    )
                assert all(r.status_code == 200 for r in responses)
                results["concurrent_requests_passed"] = len(responses)
                invalid = client.post("/api/v1/rag/vector/query", json={"question": "", "top_k": 0})
                assert invalid.status_code == 422
                results["invalid_input"] = invalid.status_code
                stopped = True
                compose("stop", "neo4j")
                results["health_outage"] = wait_for_status(client, "/health", 200)
                results["ready_outage"] = wait_for_status(client, "/ready", 503)
                failure = client.post("/api/v1/rag/vector/query", json=body)
                assert failure.status_code == 503 and "answer" not in failure.json()
                results["vector_outage"] = {"status": failure.status_code, "body": failure.json()}
                stop_api(process)
                process = start_api(port, log)
                results["fresh_start_health_outage"] = wait_for_status(client, "/health", 200)
                results["fresh_start_ready_outage"] = wait_for_status(client, "/ready", 503)
                compose("up", "-d", "--wait", "neo4j")
                stopped = False
                results["ready_recovered"] = wait_for_status(client, "/ready", 200)
                recovered = client.post("/api/v1/rag/vector/query", json=body)
                assert recovered.status_code == 200 and recovered.json()["answer"] == "PostgreSQL"
                results["vector_recovered"] = recovered.json()
                assert recovered.headers["X-Request-ID"]
                results["request_id_verified"] = True
        finally:
            try:
                if stopped:
                    compose("up", "-d", "--wait", "neo4j")
            finally:
                if process:
                    stop_api(process)
    (directory / "runtime_verification.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {k: v for k, v in results.items() if k not in {"vector_connected", "vector_recovered"}},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
