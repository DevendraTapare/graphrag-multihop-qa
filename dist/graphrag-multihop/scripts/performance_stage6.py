"""Bounded service bursts and actual read PROFILEs; calibration-source probes only."""

import argparse
import concurrent.futures
import json
import threading
import time
from collections import Counter

import psutil

from app.db.neo4j import GraphDatabaseClient
from app.evaluation.baseline import percentile
from app.vector.embedding import MiniLM
from scripts.stage6_runtime import DATA, Components, challenge_settings
from scripts.stage6_support import check_freeze, save

MODES = ("graph_only", "vector_only", "hybrid_graph_vector")


def probes():
    docs = json.loads((DATA / "sources.json").read_text())
    person = next(
        d["text"].split(" is employed by ")[0]
        for d in docs
        if d["source_filename"] == "stage6/20/employment.txt"
    )
    project = next(
        d["text"].split(" is managed by ")[0][8:]
        for d in docs
        if d["source_filename"] == "stage6/20/management.txt"
    )
    return [
        f"Which project does {person} manage?",
        f"Which database does the project managed by {person} use?",
        f"Which cloud platform hosts the database used by the project managed by {person}?",
        "Which organization employs Oriel Neverlisted?",
    ], project


class MeteredDatabase(GraphDatabaseClient):
    def __init__(self):
        super().__init__(challenge_settings())
        self.local = threading.local()
        self.captured = []

    def execute(self, cypher, parameters=None, *, timeout=None):
        started = time.perf_counter()
        try:
            return super().execute(cypher, parameters, timeout=timeout)
        finally:
            elapsed = (time.perf_counter() - started) * 1000
            if hasattr(self.local, "calls"):
                self.local.calls.append(elapsed)
            if getattr(self.local, "capture", False):
                self.captured.append((cypher, parameters))


class MeteredModel:
    def __init__(self):
        self.model = MiniLM()
        self.version = self.model.version
        self.local = threading.local()

    def encode(self, texts):
        started = time.perf_counter()
        try:
            return self.model.encode(texts)
        finally:
            self.local.encode_ms = (time.perf_counter() - started) * 1000

    def close(self):
        self.model.close()


def quantiles(values):
    return {"p50": percentile(values, 0.5), "p95": percentile(values, 0.95)}


def load():
    check_freeze()
    db, model = MeteredDatabase(), MeteredModel()
    components = Components(db, model)
    questions, _ = probes()
    rows = []
    try:
        model.encode(["Load model warmup."])
        references = {m: [components.query(m, q) for q in questions] for m in MODES}
        for mode in MODES:
            for users in (1, 5, 10, 25, 50):
                started = time.perf_counter()
                requests, samples = [], []
                stop = threading.Event()

                def sample(stop=stop, samples=samples):
                    process = psutil.Process()
                    while not stop.wait(0.25):
                        samples.append(
                            {
                                "host_cpu_percent": psutil.cpu_percent(),
                                "runner_rss_bytes": process.memory_info().rss,
                                "host_used_memory_bytes": psutil.virtual_memory().used,
                            }
                        )

                sampler = threading.Thread(target=sample, daemon=True)
                sampler.start()
                try:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=users) as pool:
                        for round_number in range(2):
                            barrier = threading.Barrier(users)

                            def request(i, round_number=round_number, barrier=barrier, mode=mode):
                                choice = (i + round_number) % len(questions)
                                barrier.wait(timeout=15)
                                db.local.calls = []
                                model.local.encode_ms = 0
                                begin = time.perf_counter()
                                try:
                                    response = components.query(mode, questions[choice])
                                    reference = references[mode][choice]
                                    if choice == 3:
                                        outcome = (
                                            "correct_abstention"
                                            if response["abstained"]
                                            else "incorrect_answer"
                                        )
                                    elif response["abstained"]:
                                        outcome = "false_abstention"
                                    else:
                                        outcome = (
                                            "successful_answer"
                                            if (
                                                response["answer"] == reference["answer"]
                                                and {c["quote"] for c in response["citations"]}
                                                == {c["quote"] for c in reference["citations"]}
                                            )
                                            else "incorrect_answer"
                                        )
                                    reason = response["reason"]
                                    phases = response.get("latency_ms", {})
                                except Exception as exc:
                                    reason = getattr(exc, "category", type(exc).__name__)
                                    outcome = (
                                        "timeout"
                                        if "timeout" in reason or "busy" in reason
                                        else "error"
                                    )
                                    phases = {}
                                return {
                                    "probe": choice,
                                    "outcome": outcome,
                                    "reason": reason,
                                    "wall_ms": (time.perf_counter() - begin) * 1000,
                                    "database_call_ms": db.local.calls,
                                    "embedding_lock_inclusive_ms": model.local.encode_ms,
                                    "phases": phases,
                                }

                            requests.extend(list(pool.map(request, range(users))))
                finally:
                    stop.set()
                    sampler.join(timeout=2)
                elapsed = time.perf_counter() - started
                counts = Counter(r["outcome"] for r in requests)
                result = {
                    "mode": mode,
                    "users": users,
                    "rounds": 2,
                    "total_requests": len(requests),
                    "outcomes": dict(counts),
                    "duration_seconds": elapsed,
                    "throughput_requests_per_second": len(requests) / elapsed,
                    "latency_ms": quantiles([r["wall_ms"] for r in requests]),
                    "database_call_wall_ms": quantiles(
                        [t for r in requests for t in r["database_call_ms"]]
                    ),
                    "database_calls": sum(len(r["database_call_ms"]) for r in requests),
                    "embedding_lock_inclusive_ms": quantiles(
                        [r["embedding_lock_inclusive_ms"] for r in requests]
                    ),
                    "resources": samples,
                    "requests": requests,
                    "pool_configured_maximum": components.settings.neo4j_pool_size,
                    "pool_internal_utilization": None,
                    "pool_note": "No supported public occupancy metric; not inferred",
                    "database_timing_note": "Client wall time includes pool, network and server; "
                    "not server CPU",
                }
                rows.append(result)
                save(
                    "load_results.json",
                    {
                        "method": "closed-loop service bursts; not HTTP or sustained capacity",
                        "probes": questions,
                        "results": rows,
                    },
                )
                print(f"{mode}: {users} users, {dict(counts)}, {elapsed:.2f}s", flush=True)
    finally:
        components.close()


def profile():
    check_freeze()
    from neo4j import Query

    db = MeteredDatabase()
    components = Components(db)
    questions, _ = probes()
    results = []
    try:
        for depth, question in enumerate(questions[:3], 1):
            db.captured = []
            db.local.capture = True
            begin = time.perf_counter()
            response = components.query("graph_only", question)
            elapsed = (time.perf_counter() - begin) * 1000
            db.local.capture = False
            plans = []
            seen = set()
            for cypher, parameters in db.captured:
                key = (cypher, json.dumps(parameters, sort_keys=True))
                if key in seen:
                    continue
                seen.add(key)
                with db.driver.session(database=db.settings.neo4j_database) as session:
                    result = session.run(Query("PROFILE " + cypher, timeout=30), parameters or {})
                    list(result)
                    summary = result.consume()
                    plans.append(
                        {
                            "query": cypher,
                            "parameters": parameters,
                            "server_available_after_ms": summary.result_available_after,
                            "server_consumed_after_ms": summary.result_consumed_after,
                            "profile": summary.profile,
                        }
                    )
            results.append(
                {
                    "hops": depth,
                    "question": question,
                    "answer": response["answer"],
                    "wall_ms": elapsed,
                    "service_phases": response["latency_ms"],
                    "round_trips": len(db.captured),
                    "unique_queries": len(seen),
                    "plans": plans,
                }
            )
        save(
            "query_plans.json",
            {
                "results": results,
                "optimized": False,
                "reason": "Retain frozen runtime; quantify seal and revalidation first",
            },
        )
        print(
            json.dumps(
                {
                    "profiles": [
                        {"hops": r["hops"], "round_trips": r["round_trips"]} for r in results
                    ]
                }
            )
        )
    finally:
        components.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["load", "profile"])
    args = parser.parse_args()
    load() if args.command == "load" else profile()
