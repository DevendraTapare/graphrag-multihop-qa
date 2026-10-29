"""Read-only k=5 vector replay; preserve every Stage 3 artifact."""

import json
import time

from app.core.config import Settings
from app.evaluation.baseline import aggregate, measure
from app.graph.fixtures import ROOT
from app.vector.retrieval import VectorOnlyService
from scripts.stage4_support import OUT, check_frozen_files, check_graph_snapshot, read_json
from scripts.vector import components


def main():
    check_frozen_files()
    gold = json.loads((ROOT / "data/evaluation/baseline_v1.json").read_text(encoding="utf-8"))
    frozen = json.loads((ROOT / "reports/stage3/baseline_metrics.json").read_text(encoding="utf-8"))
    db, model, repo = components(Settings())
    try:
        before = check_graph_snapshot(db)
        repo.require_index()
        build = repo.current(model.version)
        started = time.perf_counter()
        model.encode(["Warm the local sentence embedding model."])
        cold_ms = (time.perf_counter() - started) * 1000
        service = VectorOnlyService(repo, model)
        rows = []
        for q in gold["questions"]:
            response = service.retrieve_vector_only(q["question"], 5).model_dump()
            rows.append(
                {
                    "id": q["id"],
                    "hops": q["hops"],
                    "split": q["split"],
                    "answer": response["answer"],
                    "reason": response["reason"],
                    **measure(q, gold["facts"], response),
                    "latency_ms": response["latency_ms"],
                    "scores": [c["score"] for c in response["retrieved_chunks"]],
                    "retrieved_chunk_ids": [c["chunk_id"] for c in response["retrieved_chunks"]],
                }
            )
        old = {r["id"]: r for r in frozen["queries"] if r["top_k"] == 5}
        comparable = (
            "answer",
            "reason",
            "exact_match",
            "complete_chain",
            "required_evidence_coverage",
            "citation_count",
            "correct_citations",
            "unsupported_answer",
            "retrieved_chunk_ids",
        )
        differences = [
            {"id": r["id"], "fields": [k for k in comparable if r[k] != old[r["id"]][k]]}
            for r in rows
            if any(r[k] != old[r["id"]][k] for k in comparable)
        ]
        result = {
            "dataset_version": gold["version"],
            "configuration": {"top_k": 5, "concurrency": 1, "build_id": build["id"]},
            "cache": "New model process; cached local weights; warm timings exclude startup",
            "cold_model_plus_first_inference_ms": cold_ms,
            "metrics": {
                "overall": aggregate(rows),
                "answerable": aggregate([r for r in rows if r["hops"]]),
                **{str(h): aggregate([r for r in rows if r["hops"] == h]) for h in (0, 1, 2, 3)},
            },
            "frozen_quality_and_retrieval_equal": not differences,
            "differences": differences,
            "graph_snapshot_before": before,
            "graph_snapshot_after": check_graph_snapshot(db),
            "queries": rows,
        }
        (OUT / "vector_recheck.json").write_text(json.dumps(result, indent=2) + "\n")
        graph = read_json("graph_metrics.json")
        comparison = {
            "dataset_version": gold["version"],
            "frozen_vector_k5": frozen["metrics"]["all"]["5"],
            "vector_recheck_k5": result["metrics"],
            "graph_only": graph["metrics"]["all"],
            "frozen_vector_reproduced": not differences,
            "caveat": "Graph benchmark resolves no starts: its latency measures early abstention. "
            "Use operational_verification.json for actual traversal latency. "
            "Workloads ran sequentially.",
        }
        (OUT / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
        if not (not differences):
            raise AssertionError(differences)
        print(json.dumps({k: v for k, v in result.items() if k != "queries"}, indent=2))
    finally:
        db.close()
        model.close()


if __name__ == "__main__":
    main()
