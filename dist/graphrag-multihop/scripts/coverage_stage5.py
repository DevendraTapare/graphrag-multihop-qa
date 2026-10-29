"""Offline diagnostics only: labels never flow into graph construction or runtime."""

import json
from collections import Counter

from app.core.config import Settings
from app.db.neo4j import GraphDatabaseClient
from app.extraction.registry import EntityRegistry
from app.graph.fixtures import ROOT
from app.graph.schema import FactType
from app.graph_rag.interpretation import interpret
from app.graph_rag.linking import EntityLinker
from scripts.stage5_support import read, save


def diagnostic(nodes, edges, sources, runs, vectors, registry, processing, gold, approved):
    source_map = {r["properties"]["id"]: r["properties"] for r in sources}
    run_map = {r["properties"]["id"]: r["properties"] for r in runs}
    vector_docs = {r["properties"]["document_id"] for r in vectors}
    ready = [
        s
        for sid, s in source_map.items()
        if sid in approved
        and s.get("status") == "ready"
        and s.get("current_run_id") == s.get("desired_run_id")
        and s.get("processing_version") == processing
    ]
    ingested = {run_map[s["current_run_id"]]["document_id"] for s in ready}
    all_facts = [
        e
        for e in edges
        if e["kind"] in {f.value for f in FactType} and e["properties"].get("source_id") in approved
    ]
    facts = [
        e
        for e in all_facts
        if e["properties"].get("processing_version") == processing
        and e["properties"].get("ingestion_id")
        == source_map[e["properties"]["source_id"]].get("current_run_id")
        and source_map[e["properties"]["source_id"]].get("status") == "ready"
    ]
    supported = {
        f["id"]
        for f in gold["facts"]
        if any(
            e["kind"] == f["predicate"]
            and e["properties"]["source_document_id"] == f["document_id"]
            and (
                e["properties"].get("evidence_start"),
                e["properties"].get("evidence_end"),
                e["properties"]["quote"],
            )
            == (f["start"], f["end"], f["quote"])
            for e in facts
        )
    }
    rejections = [
        r
        for s in ready
        for r in json.loads(run_map[s["current_run_id"]].get("rejections_json", "[]"))
    ]
    nodes_present = {r["properties"]["id"] for r in nodes}
    questions = []
    for q in gold["questions"]:
        plan = interpret(q["question"])
        resolution = EntityLinker(registry).resolve(plan).model_dump(mode="json") if plan else None
        missing = sorted(set(q["supporting_fact_ids"]) - supported)
        refs = sorted(set(q["required_document_ids"]) - nodes_present)
        cause = "covered"
        if refs:
            cause = "corpus_coverage_gap"
        elif not plan:
            cause = "unsupported_grammar"
        elif resolution["status"] != "resolved":
            cause = "entity_resolution_gap"
        elif missing:
            cause = "relationship_extraction_gap"
        questions.append(
            {
                "id": q["id"],
                "question": q["question"],
                "split": q["split"],
                "answerable": q["answerable"],
                "hops": q["hops"],
                "resolution": resolution,
                "missing_fact_ids": missing,
                "missing_source_references": refs,
                "classification": cause,
                "expected_unanswerable": not q["answerable"],
            }
        )
    return {
        "vector_indexed_documents": len(vector_docs),
        "graph_ingested_documents": len(ingested),
        "same_vector_graph_document_versions": vector_docs == ingested,
        "vector_document_ids": sorted(vector_docs),
        "graph_document_ids": sorted(ingested),
        "evaluation_documents": len({f["document_id"] for f in gold["facts"]}),
        "graph_supported_benchmark_facts": len(supported),
        "gold_fact_count": len(gold["facts"]),
        "resolvable_benchmark_starts": sum(
            q["resolution"] is not None and q["resolution"]["status"] == "resolved"
            for q in questions
        ),
        "unresolved_benchmark_starts": sum(
            q["resolution"] is None or q["resolution"]["status"] != "resolved" for q in questions
        ),
        "answerable_unresolved_starts": sum(
            q["answerable"] and (q["resolution"] is None or q["resolution"]["status"] != "resolved")
            for q in questions
        ),
        "documents_without_supported_facts": sorted(
            ingested - {e["properties"]["source_document_id"] for e in facts}
        ),
        "source_references_missing_from_graph": sorted(
            {f["document_id"] for f in gold["facts"]} - nodes_present
        ),
        "accepted_current_facts": len(facts),
        "historical_invalidated_facts": len(all_facts) - len(facts),
        "facts_invalidated_by_content_change": sum(
            e["properties"].get("content_hash")
            != source_map[e["properties"]["source_id"]].get("content_hash")
            for e in all_facts
        ),
        "rejected_candidates": len(rejections),
        "rejected_relationship_candidates": sum(r["kind"] == "relationship" for r in rejections),
        "rejection_kinds": dict(Counter(r["kind"] for r in rejections)),
        "rejection_reasons": dict(Counter(r["reason"] for r in rejections)),
        "questions": questions,
    }


def main():
    gold = json.loads((ROOT / "data/evaluation/baseline_v1.json").read_text())
    old = json.loads((ROOT / "reports/stage4/graph_snapshot.json").read_text())
    policy = json.loads((ROOT / "data/runtime/graph_corpus_v1.json").read_text())
    before = diagnostic(
        old["nodes"],
        old["edges"],
        old["sources"],
        old["runs"],
        old["vectors"],
        EntityRegistry(),
        policy["processing_version"],
        gold,
        set(policy["source_ids"]),
    )
    result = {"before": before, "split_disclosure": gold["disclosure"]}
    manifest_path = ROOT / "reports/stage5/backfill_verification.json"
    if manifest_path.exists():
        from scripts.stage5_support import aligned_snapshot

        settings = Settings().model_copy(
            update={"neo4j_uri": Settings().stage5_neo4j_uri, "vector_corpus": "stage5-aligned"}
        )
        db = GraphDatabaseClient(settings)
        try:
            current = aligned_snapshot(db)
            manifest = read("build_manifest.json")
            result["after"] = diagnostic(
                current["nodes"],
                current["edges"],
                current["sources"],
                current["runs"],
                current["vectors"],
                EntityRegistry(ROOT / "data/runtime/stage5_registry.json"),
                manifest["processing_version"],
                gold,
                set(manifest["source_ids"]),
            )
        finally:
            db.close()
    save("coverage_audit.json", result)
    print(
        json.dumps(
            {
                k: {
                    field: value
                    for field, value in r.items()
                    if field
                    not in {
                        "questions",
                        "vector_document_ids",
                        "graph_document_ids",
                        "documents_without_supported_facts",
                    }
                }
                for k, r in result.items()
                if isinstance(r, dict)
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
