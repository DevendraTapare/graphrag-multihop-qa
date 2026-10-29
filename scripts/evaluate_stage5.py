"""Offline three-way and ablation evaluation with unchanged Stage 3 grading."""

import csv
import hashlib
import json
import platform
import time
from collections import Counter

import psutil

from app.aligned.components import AlignedComponents
from app.aligned.graph import build_aligned_service
from app.aligned.hybrid import HybridService
from app.core.config import Settings
from app.evaluation.baseline import aggregate as baseline_aggregate
from app.evaluation.baseline import measure, percentile
from app.graph.fixtures import ROOT
from app.vector.embedding import MODEL, REVISION
from scripts.stage5_support import OUT, aligned_snapshot, check_history, read, save
from scripts.verify_aligned import snapshot_digest

MODES = (
    "vector_only",
    "graph_only",
    "hybrid_no_expansion",
    "hybrid_no_reranking",
    "hybrid_graph_vector",
)
FILENAMES = {
    "vector_only": "vector_aligned_metrics.json",
    "graph_only": "graph_aligned_metrics.json",
    "hybrid_graph_vector": "hybrid_metrics.json",
}


def runtime_hashes():
    paths = [
        *(ROOT / "app/aligned").glob("*.py"),
        ROOT / "app/api/hybrid.py",
        ROOT / "app/main.py",
        ROOT / "app/core/config.py",
        ROOT / "data/runtime/stage5_registry.json",
        ROOT / "data/runtime/stage5_corpus.json",
    ]
    return {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(paths)
    }


def normalize(response, mode):
    if mode == "vector_only":
        return response
    chunks = {(c["document_id"], c["chunk_id"]): c for c in response["evidence_chunks"]}
    for c in response.get("vector_evidence", []):
        chunks.setdefault((c["document_id"], c["chunk_id"]), c)
    if "fused_evidence" in response:
        ordered = [chunks[(r["document_id"], r["chunk_id"])] for r in response["fused_evidence"]]
    else:
        ordered = list(chunks.values())
    return {**response, "retrieved_chunks": ordered}


def graph_chain(question, facts, response):
    supported = set()
    for path in response.get("reasoning_paths", []):
        if path["hop_count"] != question["hops"]:
            continue
        for step in path["steps"]:
            for cite in step["supports"]:
                supported.update(
                    f["id"]
                    for f in facts
                    if f["id"] in question["supporting_fact_ids"]
                    and (f["predicate"], f["document_id"], f["start"], f["end"], f["quote"])
                    == (
                        step["relation"],
                        cite["document_id"],
                        cite["start"],
                        cite["end"],
                        cite["quote"],
                    )
                )
    return supported == set(question["supporting_fact_ids"]) if question["answerable"] else None


def aggregate(rows):
    transformed = [
        {
            **r,
            "latency_ms": {
                "query_embedding": 0,
                "vector_retrieval": 0,
                "end_to_end": r["latency_ms"]["end_to_end"],
            },
        }
        for r in rows
    ]
    result = baseline_aggregate(transformed)
    phases = sorted({k for r in rows for k in r["latency_ms"]})
    result["latency_ms"] = {
        k: {
            "p50": percentile([r["latency_ms"].get(k, 0) for r in rows], 0.5),
            "p95": percentile([r["latency_ms"].get(k, 0) for r in rows], 0.95),
        }
        for k in phases
    }
    values = [r["validated_graph_chain"] for r in rows if r["validated_graph_chain"] is not None]
    result["validated_graph_chain_coverage"] = sum(values) / len(values) if values else None
    result["candidate_paths"] = sum(r["response"].get("candidate_path_count", 0) for r in rows)
    result["paths_discarded"] = sum(r["response"].get("paths_discarded", 0) for r in rows)
    result["resolution_statuses"] = dict(
        Counter(
            (r["response"].get("resolution") or {}).get("status", "not_applicable") for r in rows
        )
    )
    result["failure_causes"] = dict(Counter(r["failure_cause"] for r in rows))
    return result


def summarize(rows):
    return {
        split: {
            "overall": aggregate([r for r in rows if split == "all" or r["split"] == split]),
            "answerable": aggregate(
                [r for r in rows if r["hops"] and (split == "all" or r["split"] == split)]
            ),
            **{
                str(h): aggregate(
                    [r for r in rows if r["hops"] == h and (split == "all" or r["split"] == split)]
                )
                for h in range(4)
            },
        }
        for split in ("all", "calibration", "held_out")
    }


def main():
    check_history()
    assert runtime_hashes() == read("runtime_freeze.json")["files"], "Runtime changed after freeze"
    gold = json.loads((ROOT / "data/evaluation/baseline_v1.json").read_text(encoding="utf-8"))
    settings = Settings()
    components = AlignedComponents(settings)
    try:
        before = snapshot_digest(aligned_snapshot(components.db))
        assert before == read("provenance_audit.json")["snapshot_sha256"]
        started = time.perf_counter()
        components.model.encode(["Warm the local sentence embedding model."])
        cold_ms = (time.perf_counter() - started) * 1000
        services = {
            "vector_only": components.vector,
            "graph_only": components.graph,
            "hybrid_graph_vector": components.hybrid,
            "hybrid_no_expansion": HybridService(
                components.vector,
                build_aligned_service(components.db, settings, expand=False),
                expand=False,
            ),
            "hybrid_no_reranking": HybridService(components.vector, components.graph, rerank=False),
        }
        warmup_question = "Which project does Morgan manage?"
        cold_requests = {}
        for mode in ("vector_only", "graph_only", "hybrid_graph_vector"):
            started = time.perf_counter()
            service = services[mode]
            if mode == "vector_only":
                response = service.retrieve_vector_only(warmup_question, 5)
            else:
                response = service.query(warmup_question)
            cold_requests[mode] = {
                "answer": response.answer,
                "wall_ms": (time.perf_counter() - started) * 1000,
                "latency_ms": response.latency_ms,
            }
        results = {}
        for mode in MODES:
            rows = []
            for question in gold["questions"]:
                service = services[mode]
                if mode == "vector_only":
                    response = service.retrieve_vector_only(question["question"], 5)
                elif mode == "graph_only":
                    response = service.query(question["question"], 3)
                else:
                    response = service.query(question["question"], 5, 3)
                raw = response.model_dump(mode="json")
                measured = measure(question, gold["facts"], normalize(raw, mode))
                cause = "none"
                if raw["abstained"]:
                    if not question["answerable"]:
                        cause = "expected_abstention"
                    elif raw["reason"] in {"entity_not_found", "entity_ambiguous"}:
                        cause = "entity_resolution_gap"
                    elif "unsupported" in raw["reason"]:
                        cause = "unsupported_grammar"
                    elif not measured["complete_chain"]:
                        cause = (
                            "vector_retrieval_gap"
                            if mode == "vector_only"
                            else "traversal_planning_failure"
                        )
                    else:
                        cause = "answer_generation_failure"
                elif not measured["exact_match"]:
                    cause = "answer_generation_failure"
                rows.append(
                    {
                        "id": question["id"],
                        "question": question["question"],
                        "split": question["split"],
                        "hops": question["hops"],
                        "tags": question["tags"],
                        "expected_answer": question["expected_answer"],
                        "answer": raw["answer"],
                        **measured,
                        "validated_graph_chain": graph_chain(question, gold["facts"], raw)
                        if mode != "vector_only"
                        else None,
                        "failure_cause": cause,
                        "response": raw,
                        "latency_ms": raw["latency_ms"],
                    }
                )
            results[mode] = {
                "label": "Stage 5 aligned-corpus " + mode,
                "dataset_version": gold["version"],
                "disclosure": gold["disclosure"],
                "configuration": {
                    "top_k": 5,
                    "max_hops": 3,
                    "concurrency": 1,
                    "source_documents": 92,
                    "chunks": 92,
                    "index": components.vector.repo.require_index(),
                    "vector_build_id": components.vector.repo.current(components.model.version)[
                        "id"
                    ],
                    "embedding_model": MODEL,
                    "model_revision": REVISION,
                    "embedding_version": components.model.version,
                    "processing_version": components.graph.pipeline.version,
                    "neo4j": components.db.execute(
                        "CALL dbms.components() YIELD versions,edition RETURN versions,edition"
                    ),
                    "platform": platform.platform(),
                    "cpu": platform.processor(),
                    "physical_cores": psutil.cpu_count(logical=False),
                    "logical_cores": psutil.cpu_count(),
                    "ram_bytes": psutil.virtual_memory().total,
                    "python": platform.python_version(),
                    "runtime_files": runtime_hashes(),
                    "snapshot_sha256": before,
                },
                "metrics": summarize(rows),
                "by_question_type": {
                    tag: aggregate([r for r in rows if tag in r["tags"]])
                    for tag in sorted({t for r in rows for t in r["tags"]})
                },
                "queries": rows,
            }
            save(FILENAMES.get(mode, mode + "_metrics.json"), results[mode])
            print(
                json.dumps(
                    {"mode": mode, "answerable": results[mode]["metrics"]["all"]["answerable"]}
                ),
                flush=True,
            )
        after = snapshot_digest(aligned_snapshot(components.db))
        assert before == after, "Aligned graph changed during evaluation"
        save(
            "performance.json",
            {
                "cache": "Fresh local model process with cached weights; DB already running. "
                "Warm-up requests precede benchmark; no forced OS/page-cache eviction.",
                "model_start_plus_first_inference_ms": cold_ms,
                "first_requests": cold_requests,
                "snapshot_unchanged": before == after,
            },
        )
        frozen = json.loads((ROOT / "reports/stage3/baseline_metrics.json").read_text())
        save(
            "comparison.json",
            {
                "frozen_stage3_vector_k5": frozen["metrics"]["all"]["5"],
                "modes": {m: r["metrics"] for m, r in results.items()},
                "by_question_type": {m: r["by_question_type"] for m, r in results.items()},
            },
        )
        fields = [
            "mode",
            "hops",
            "questions",
            "answer_exact_match",
            "complete_chain_coverage",
            "required_evidence_coverage",
            "validated_graph_chain_coverage",
            "citation_correctness",
            "abstention_rate",
            "unsupported_answer_count",
            "p50_ms",
            "p95_ms",
            "accuracy_delta_pp",
        ]
        with (OUT / "ablation_results.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for mode, result in results.items():
                for hops in ("answerable", "0", "1", "2", "3"):
                    metric = result["metrics"]["all"][hops]
                    base = results["vector_only"]["metrics"]["all"][hops]
                    writer.writerow(
                        {
                            "mode": mode,
                            "hops": hops,
                            **{k: metric[k] for k in fields if k in metric},
                            "p50_ms": metric["latency_ms"]["end_to_end"]["p50"],
                            "p95_ms": metric["latency_ms"]["end_to_end"]["p95"],
                            "accuracy_delta_pp": 100
                            * (metric["answer_exact_match"] - base["answer_exact_match"]),
                        }
                    )
        lines = [
            "# Stage 5 errors and abstentions",
            "",
            "All modes use the same 92 source versions. "
            "Split names are descriptive, not blind generalization estimates.",
            "",
            "| Mode | Question ID | Expected | Actual | Cause | Reason |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for mode, result in results.items():
            lines.extend(
                f"| {mode} | {r['id']} | {r['expected_answer']} | {r['answer']} | "
                f"{r['failure_cause']} | {r['response']['reason']} |"
                for r in result["queries"]
                if r["abstained"] or not r["exact_match"]
            )
        (OUT / "error_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    finally:
        components.close()


if __name__ == "__main__":
    main()
