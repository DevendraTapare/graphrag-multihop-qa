"""Real process + Compose outage/recovery exercise; leaves Neo4j running."""

import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

from app.core.config import Settings
from app.db.neo4j import GraphDatabaseClient
from app.extraction.documents import LocalDocumentLoader
from app.extraction.models import ChunkOptions, IngestionFailure
from app.extraction.pipeline import ExtractionPipeline
from app.repositories.ingestion import IngestionRepository
from app.services.ingestion import IngestionService
from app.services.ingestion_validation import validate_ingestion


def wait_for_status(client, path, expected, timeout=60):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            response = client.get(path)
            last = response.status_code
            if last == expected:
                assert response.headers.get("X-Request-ID")
                return last
        except httpx.TransportError:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"{path}: expected {expected}, last status {last}")


def compose(*arguments):
    subprocess.run(
        ["docker", "compose", "--progress", "plain", *arguments], check=True, timeout=180
    )


def start_api(port, log):
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:create_app",
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


def stop_api(process):
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def ingestion_probe():
    settings = Settings()
    database = GraphDatabaseClient(settings)
    try:
        pipeline = ExtractionPipeline(
            ChunkOptions(
                size=settings.ingestion_chunk_size, overlap=settings.ingestion_chunk_overlap
            )
        )
        repository = IngestionRepository(database, pipeline)
        result = IngestionService(repository).ingest_local(LocalDocumentLoader(), "atlas.txt")
        validate_ingestion(repository, result["source_id"])
        return {"status": result["status"], "facts": result["facts"]}
    finally:
        database.close()


def main():
    if Settings().app_env != "development":
        raise SystemExit("Runtime outage verification requires development environment")
    # A separate ephemeral API port avoids interfering with an existing developer API.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    results = {}
    Path("reports").mkdir(exist_ok=True)
    with Path("reports/runtime-api.log").open("w") as log:
        process = start_api(port, log)
        stopped = False
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=15) as client:
                results["health_connected"] = wait_for_status(client, "/health", 200)
                results["ready_connected"] = wait_for_status(client, "/ready", 200)
                results["versioned_ready"] = wait_for_status(client, "/api/v1/ready", 200)
                stopped = True
                compose("stop", "neo4j")
                results["health_outage"] = wait_for_status(client, "/health", 200)
                results["ready_outage"] = wait_for_status(client, "/ready", 503)
                try:
                    ingestion_probe()
                except IngestionFailure as exc:
                    if exc.category != "database_unavailable":
                        raise
                    results["ingestion_outage"] = exc.category
                else:
                    raise RuntimeError("Ingestion unexpectedly succeeded during database outage")
                stop_api(process)
                process = start_api(port, log)
                results["health_start_during_outage"] = wait_for_status(client, "/health", 200)
                results["ready_start_during_outage"] = wait_for_status(client, "/ready", 503)
                compose("up", "-d", "--wait", "neo4j")
                stopped = False
                results["ready_recovered"] = wait_for_status(client, "/ready", 200)
                results["health_recovered"] = wait_for_status(client, "/health", 200)
                results["ingestion_recovered"] = ingestion_probe()
                results["request_id_present"] = bool(client.get("/health").headers["X-Request-ID"])
        finally:
            try:
                if stopped:
                    compose("up", "-d", "--wait", "neo4j")
            finally:
                stop_api(process)
    Path("reports/runtime-verification.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
