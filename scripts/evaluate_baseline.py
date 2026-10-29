"""Measured real MiniLM + Neo4j evaluation. Never supplies gold to runtime services."""

import csv
import importlib.metadata
import json
import platform
import time

import psutil

from app.core.config import Settings
from app.evaluation.baseline import aggregate, measure
from app.graph.fixtures import ROOT
from app.vector.embedding import MODEL, REVISION
from app.vector.retrieval import VectorOnlyService
from scripts.vector import components


def main():
    gold = json.loads((ROOT / "data/evaluation/baseline_v1.json").read_text(encoding="utf-8"))
    db, model, repo = components(Settings())
    directory = ROOT / "reports/stage3"
    directory.mkdir(parents=True, exist_ok=True)
    try:
        repo.require_index()
        build = repo.current(model.version)
        # Cold startup explicitly measured and excluded from steady-state quantiles.
        cold = time.perf_counter()
        model.encode(["Warm the local sentence embedding model."])
        cold_ms = (time.perf_counter() - cold) * 1000
        service = VectorOnlyService(repo, model)
        rows = []
        for k in (1, 3, 5, 10):
            for q in gold["questions"]:
                response = service.retrieve_vector_only(q["question"], k).model_dump()
                rows.append(
                    {
                        "id": q["id"],
                        "split": q["split"],
                        "hops": q["hops"],
                        "top_k": k,
                        "question": q["question"],
                        "answer": response["answer"],
                        "reason": response["reason"],
                        **measure(q, gold["facts"], response),
                        "latency_ms": response["latency_ms"],
                        "scores": [c["score"] for c in response["retrieved_chunks"]],
                        "retrieved_chunk_ids": [
                            c["chunk_id"] for c in response["retrieved_chunks"]
                        ],
                    }
                )
        summaries = {}
        for split in ("all", "calibration", "held_out"):
            summaries[split] = {}
            for k in (1, 3, 5, 10):
                selected = [
                    r for r in rows if r["top_k"] == k and (split == "all" or r["split"] == split)
                ]
                summaries[split][str(k)] = {
                    "overall": aggregate(selected),
                    **{
                        str(h): aggregate([r for r in selected if r["hops"] == h])
                        for h in (0, 1, 2, 3)
                    },
                    "answerable": aggregate([r for r in selected if r["hops"] > 0]),
                }
        version = db.execute(
            "CALL dbms.components() YIELD versions, edition RETURN versions, edition"
        )
        memory = psutil.Process().memory_info().rss
        worker_memory = psutil.Process(model.process.pid).memory_info().rss
        result = {
            "dataset_version": gold["version"],
            "disclosure": gold["disclosure"],
            "question_count": len(gold["questions"]),
            "configuration": {
                "model": MODEL,
                "revision": REVISION,
                "embedding_version": model.version,
                "dimension": 384,
                "normalization": "L2",
                "index": "chunk_minilm_cosine",
                "similarity": "cosine",
                "corpus": json.loads(build["summary_json"]),
                "os": platform.platform(),
                "processor": platform.processor(),
                "physical_cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(),
                "ram_bytes": psutil.virtual_memory().total,
                "python": platform.python_version(),
                "neo4j": version,
                "concurrency": 1,
                "torch_threads": 2,
                "packages": {
                    p: importlib.metadata.version(p)
                    for p in ("sentence-transformers", "transformers", "torch", "neo4j")
                },
            },
            "performance": {
                "cold_model_plus_first_inference_ms": cold_ms,
                "cold_worker_startup_ms": model.cold_start_ms,
                "parent_rss_bytes": memory,
                "model_worker_rss_bytes": worker_memory,
                "steady_state_rows": len(rows),
            },
            "metrics": summaries,
            "queries": rows,
        }
        (directory / "baseline_metrics.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        fields = [
            "id",
            "split",
            "hops",
            "top_k",
            "document_recall",
            "precision",
            "required_evidence_coverage",
            "complete_chain",
            "exact_match",
            "abstained",
            "citation_count",
            "correct_citations",
            "unsupported_answer",
            "query_embedding_ms",
            "vector_retrieval_ms",
            "end_to_end_ms",
        ]
        with (directory / "baseline_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for r in rows:
                writer.writerow(
                    {
                        **{f: r[f] for f in fields if f in r},
                        **{
                            f"{key}_ms": r["latency_ms"][key]
                            for key in ("query_embedding", "vector_retrieval", "end_to_end")
                        },
                    }
                )
        failures = [r for r in rows if r["top_k"] == 5 and r["hops"] > 0 and not r["exact_match"]]
        lines = [
            "# Baseline error analysis",
            "",
            gold["disclosure"],
            "",
            "At k=5, failures below distinguish incomplete retrieved evidence from generation "
            "failures. No GraphRAG result exists yet.",
            "",
            "| Question | Hops | Complete evidence | Generator reason | Missing facts |",
            "| --- | ---: | --- | --- | --- |",
        ]
        lines.extend(
            f"| {r['id']} | {r['hops']} | {r['complete_chain']} | {r['reason']} | "
            f"{', '.join(r['missing_fact_ids'])} |"
            for r in failures
        )
        (directory / "error_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "questions": len(gold["questions"]),
                    "k5": summaries["all"]["5"],
                    "performance": result["performance"],
                },
                indent=2,
            )
        )
    finally:
        model.close()
        db.close()


if __name__ == "__main__":
    main()
