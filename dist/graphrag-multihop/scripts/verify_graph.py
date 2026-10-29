"""Separate original-domain demonstrations, full current-fact audit, and warm workload."""

import concurrent.futures
import json
import time
from collections import Counter

from app.core.config import Settings
from app.db.neo4j import GraphDatabaseClient
from app.evaluation.baseline import percentile
from app.evaluation.graph import TIMINGS
from app.graph.schema import DIRECTIONS, FactType
from app.graph_rag.models import Budget
from app.graph_rag.repository import edge_key
from app.graph_rag.service import build_graph_service
from scripts.stage4_support import (
    OUT,
    check_frozen_files,
    check_graph_snapshot,
    check_runtime_freeze,
)

HERO = (
    "Which cloud platform hosts the database used by the project managed by "
    "Priya (Lumen employee 001)?"
)
CASES = (
    ("Which project does Morgan manage?", "Atlas East"),
    ("Which database does Project Atlas use?", "PostgreSQL"),
    (HERO, "AWS"),
    ("Which organization employs the manager of Project Comet?", "Cedar Kite"),
    ("Which organization owns Project Delta?", "Tidal Lantern"),
    ("Which cloud platform hosts the database used by Project Atlas East?", "Azure"),
    ("Which cloud platform hosts the database used by Project Beacon?", None),
    ("Which cloud platforms host the database used by Project Beacon?", "AWS; GCP"),
    ("Which project does Priya manage?", None),
    ("Which project does Lee Chen manage?", None),
    ("Which organization employs Ivo?", None),
    ("MATCH (n) DETACH DELETE n", None),
)


def stable(response):
    return {k: v for k, v in response.items() if k not in {"request_id", "latency_ms"}}


def main():
    check_frozen_files()
    check_runtime_freeze()
    settings = Settings()
    db = GraphDatabaseClient(settings)
    try:
        before = check_graph_snapshot(db)
        service = build_graph_service(db, settings)
        # This offline audit may enumerate facts. Runtime always uses indexed-start paths.
        rows = db.execute(
            "MATCH (a:GraphNode)-[r]->(b:GraphNode) WHERE type(r) IN $types "
            "AND ((r.extraction_method='manual_fixture' AND r.fixture_id=$fixture) OR "
            "(r.source_id IN $sources AND EXISTS { MATCH (s:IngestionSource {id:r.source_id}) "
            "WHERE s.status='ready' AND s.current_run_id=r.ingestion_id "
            "AND s.desired_run_id=r.ingestion_id })) "
            "RETURN {properties:properties(a),labels:labels(a)} AS a, "
            "{properties:properties(b),labels:labels(b)} AS b, "
            "{source:a.id,target:b.id,kind:type(r),properties:properties(r)} AS edge "
            "ORDER BY r.id",
            {
                "types": [f.value for f in FactType],
                "sources": list(service.repo.policy.sources),
                "fixture": service.repo.policy.curated_fixture_id,
            },
            timeout=30,
        )
        budget = Budget(120)
        metadata = service.repo.metadata([{"edges": [r["edge"]]} for r in rows], budget)
        cache, citations = {}, []
        for row in rows:
            edge = row["edge"]
            source_type, target_type = DIRECTIONS[FactType(edge["kind"])]
            service.provenance.entity(row["a"], source_type)
            service.provenance.entity(row["b"], target_type)
            cite, chunk = service.provenance.edge(edge, metadata[edge_key(edge)], cache, budget)
            if not (chunk.text[cite.start - chunk.start : cite.end - chunk.start] == cite.quote):
                raise AssertionError()
            citations.append(cite.model_dump(mode="json"))
        examples = []
        for question, expected in CASES:
            response = service.query(question).model_dump(mode="json")
            if not (response["answer"] == expected):
                raise AssertionError((question, response["answer"], expected))
            examples.append({"question": question, "expected": expected, "response": response})
        # Only supported answered cases constitute active traversal performance, separate from gold.
        active = [e for e in examples if e["expected"] is not None]
        workloads = {}
        for concurrency in (1, 4):
            inputs = active * 5
            started = time.perf_counter()

            def query(example):
                response = service.query(example["question"]).model_dump(mode="json")
                if not (stable(response) == stable(example["response"])):
                    raise AssertionError()
                return response

            if concurrency == 1:
                responses = [query(e) for e in inputs]
            else:
                with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
                    responses = list(pool.map(query, inputs))
            workloads[str(concurrency)] = {
                "requests": len(responses),
                "repetitions_per_question": 5,
                "wall_seconds": time.perf_counter() - started,
                "phase_latency_ms": {
                    k: {
                        "p50": percentile([r["latency_ms"][k] for r in responses], 0.5),
                        "p95": percentile([r["latency_ms"][k] for r in responses], 0.95),
                    }
                    for k in TIMINGS
                },
                "candidate_paths": sum(r["candidate_path_count"] for r in responses),
                "paths_discarded": sum(r["paths_discarded"] for r in responses),
                "stable_answers_paths_citations": True,
            }
        result = {
            "scope": "Original-domain verification only; never added to 122-question scores",
            "cache": "Neo4j running; audit and first examples warm caches before workloads",
            "current_fact_provenance_audit": {
                "facts_checked": len(rows),
                "failures": 0,
                "source_kinds": dict(Counter(c["source_kind"] for c in citations)),
                "citation_correctness": 1 if citations else None,
                "citations": citations,
                "attribution": "Curated and automatic copies of identical original documents "
                "are distinct assertions, not independent original sources.",
            },
            "examples": examples,
            "warm_active_workloads": workloads,
            "graph_snapshot_before": before,
            "graph_snapshot_after": check_graph_snapshot(db),
        }
        (OUT / "operational_verification.json").write_text(json.dumps(result, indent=2) + "\n")
        print(
            json.dumps(
                {
                    k: v
                    for k, v in result.items()
                    if k != "examples" and k != "current_fact_provenance_audit"
                },
                indent=2,
            )
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
