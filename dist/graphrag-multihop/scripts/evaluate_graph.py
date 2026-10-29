"""Frozen Stage 3 dataset, actual graph-only runtime, unchanged evidence/answer grader."""

import csv
import json
import platform
from collections import Counter

import psutil

from app.core.config import Settings
from app.db.neo4j import GraphDatabaseClient
from app.evaluation.graph import aggregate, score
from app.graph.fixtures import ROOT
from app.graph_rag.service import build_graph_service
from scripts.stage4_support import (
    OUT,
    check_frozen_files,
    check_graph_snapshot,
    check_runtime_freeze,
    read_json,
)


def main():
    protected = check_frozen_files()
    code = check_runtime_freeze()
    settings = Settings()
    db = GraphDatabaseClient(settings)
    try:
        before = check_graph_snapshot(db)
        gold = json.loads((ROOT / "data/evaluation/baseline_v1.json").read_text(encoding="utf-8"))
        corpus = json.loads(
            (ROOT / "data/runtime/graph_corpus_v1.json").read_text(encoding="utf-8")
        )
        service = build_graph_service(db, settings)
        rows = []
        for q in gold["questions"]:
            response = service.query(q["question"], 3).model_dump(mode="json")
            rows.append(
                {
                    "id": q["id"],
                    "question": q["question"],
                    "split": q["split"],
                    "hops": q["hops"],
                    "tags": q["tags"],
                    "expected_answer": q["expected_answer"],
                    "answer": response["answer"],
                    "reason": response["reason"],
                    "plan": response["plan"],
                    "resolution": response["resolution"],
                    "candidate_path_count": response["candidate_path_count"],
                    "paths_discarded": response["paths_discarded"],
                    "latency_ms": response["latency_ms"],
                    **score(q, gold["facts"], response, corpus, service.pipeline.registry),
                }
            )
        summaries = {}
        for split in ("all", "calibration", "held_out"):
            selected = [r for r in rows if split == "all" or r["split"] == split]
            summaries[split] = {
                "overall": aggregate(selected),
                **{
                    str(h): aggregate([r for r in selected if r["hops"] == h]) for h in (0, 1, 2, 3)
                },
                "answerable": aggregate([r for r in selected if r["hops"] > 0]),
            }
        baseline = read_json("baseline_freeze.json")
        result = {
            "dataset_version": gold["version"],
            "question_count": len(rows),
            "configuration": {
                "max_hops": 3,
                "max_candidates": settings.graph_max_candidates,
                "max_answers": settings.graph_max_answers,
                "query_timeout": settings.graph_query_timeout,
                "request_timeout": settings.graph_request_timeout,
                "concurrency": 1,
                "os": platform.platform(),
                "processor": platform.processor(),
                "physical_cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(),
                "ram_bytes": psutil.virtual_memory().total,
                "python": platform.python_version(),
                "neo4j": db.execute(
                    "CALL dbms.components() YIELD versions,edition RETURN versions,edition"
                ),
                "processing_version": service.pipeline.version,
                "registry_version": service.pipeline.registry.version,
                "runtime_sha256": code["files"],
                "source_corpus": corpus["version"],
                "baseline_build_id": corpus["baseline_build_id"],
            },
            "protected_baseline": protected,
            "graph_snapshot_before": before,
            "graph_snapshot_after": check_graph_snapshot(db),
            "metrics": summaries,
            "by_question_type": {
                tag: aggregate([r for r in rows if tag in r["tags"]])
                for tag in sorted({t for r in rows for t in r["tags"]})
            },
            "by_plan": {
                rule: aggregate(
                    [r for r in rows if (r["plan"] or {}).get("rule_id", "unsupported") == rule]
                )
                for rule in sorted({(r["plan"] or {}).get("rule_id", "unsupported") for r in rows})
            },
            "frozen_vector_k5": baseline["baseline_k5"],
            "queries": rows,
        }
        (OUT / "graph_metrics.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        fields = [
            "id",
            "split",
            "hops",
            "question",
            "expected_answer",
            "answer",
            "reason",
            "error_cause",
            "error_origin",
            "resolution_status",
            "incorrect_entity_link",
            "document_recall",
            "required_evidence_coverage",
            "complete_chain",
            "validated_graph_chain",
            "exact_match",
            "abstained",
            "candidate_path_count",
            "paths_discarded",
            "citation_count",
            "correct_citations",
            "unsupported_answer",
            "end_to_end_ms",
        ]
        with (OUT / "graph_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        **{k: row[k] for k in fields if k in row},
                        "end_to_end_ms": row["latency_ms"]["end_to_end"],
                    }
                )
        lines = [
            "# Graph-only error analysis",
            "",
            "The registry, extraction, graph snapshot, Stage 3 data and grading rules are frozen. "
            "These results include upstream coverage failures; no gold-derived edges were added.",
            "",
            "Citation/validation percentages are N/A when zero evidence was returned.",
            "",
            "Causes across all abstentions: "
            + str(dict(Counter(r["error_cause"] for r in rows if r["abstained"]))),
            "",
            "| ID | Split | Hops | Expected | Actual | Cause | Origin | Reason |",
            "| --- | --- | ---: | --- | --- | --- | --- | --- |",
        ]
        lines += [
            f"| {r['id']} | {r['split']} | {r['hops']} | {r['expected_answer']} | {r['answer']} | "
            f"{r['error_cause']} | {r['error_origin']} | {r['reason']} |"
            for r in rows
            if r["abstained"] or not r["exact_match"]
        ]
        (OUT / "error_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(json.dumps({"questions": len(rows), "metrics": summaries["all"]}, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
