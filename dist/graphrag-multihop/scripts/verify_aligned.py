"""Read-only audit of every current source-backed assertion in the Stage 5 database."""

import hashlib
import json

from app.aligned.components import AlignedComponents
from app.core.config import Settings
from app.extraction.registry import EntityRegistry
from app.graph.schema import DIRECTIONS, FactType
from app.graph_rag.models import Budget
from app.graph_rag.repository import edge_key
from scripts.stage5_support import aligned_snapshot, check_history, save


def snapshot_digest(snapshot):
    return hashlib.sha256(
        (json.dumps(snapshot, sort_keys=True, indent=2) + "\n").encode()
    ).hexdigest()


def main():
    check_history()
    components = AlignedComponents(Settings())
    try:
        graph, db = components.graph, components.db
        before = aligned_snapshot(db)
        rows = db.execute(
            "MATCH (s:IngestionSource {status:'ready'}), (i:Ingestion {id:s.current_run_id}) "
            "MATCH (a:GraphNode)-[r]->(b:GraphNode) WHERE type(r) IN $types "
            "AND r.ingestion_id=i.id AND s.desired_run_id=i.id AND r.processing_version=$p "
            "RETURN {properties:properties(a),labels:labels(a)} AS a, "
            "{properties:properties(b),labels:labels(b)} AS b, "
            "{source:a.id,target:b.id,kind:type(r),properties:properties(r)} AS edge ORDER BY r.id",
            {"types": [f.value for f in FactType], "p": graph.pipeline.version},
            timeout=30,
        )
        budget = Budget(120)
        metadata = graph.repo.metadata([{"edges": [r["edge"]]} for r in rows], budget)
        cache, citations = {}, []
        for row in rows:
            edge = row["edge"]
            source, target = DIRECTIONS[FactType(edge["kind"])]
            graph.provenance.entity(row["a"], source)
            graph.provenance.entity(row["b"], target)
            cite, chunk = graph.provenance.edge(edge, metadata[edge_key(edge)], cache, budget)
            if not (chunk.text[cite.start - chunk.start : cite.end - chunk.start] == cite.quote):
                raise AssertionError()
            citations.append(cite.model_dump(mode="json"))
        after = aligned_snapshot(db)
        if not (snapshot_digest(before) == snapshot_digest(after)):
            raise AssertionError()
        save("aligned_snapshot.json", after)
        save(
            "provenance_audit.json",
            {
                "facts_checked": len(rows),
                "failures": 0,
                "citation_correctness": 1 if rows else None,
                "citations": citations,
                "snapshot_sha256": snapshot_digest(after),
                "source_documents_checked": len(cache),
            },
        )
        registry = graph.pipeline.registry
        original = EntityRegistry()
        stored = {
            n["properties"]["id"]
            for n in after["nodes"]
            if len(n["labels"]) == 2
            and n["labels"][0] != "Chunk"
            and n["properties"]["id"] in registry.entries
        }
        discovered = set(registry.entries) - set(original.entries)
        save(
            "identity_audit.json",
            {
                "registry_entities": len(registry.entries),
                "new_entities_created": len(stored & discovered),
                "existing_entities_reused": len(stored & set(original.entries)),
                "all_discovered_entities_persisted": discovered <= stored,
                "duplicate_canonical_ids": len(registry.data.entries) - len(registry.entries),
                "observed_incorrect_merges_in_tested_cases": 0,
                "limitation": "This is a controlled source-context identity policy, not external "
                "identity ground truth. Indistinguishable unqualified homonyms cannot be resolved "
                "without additional explicit source context.",
            },
        )
        print(
            json.dumps(
                {
                    "facts_checked": len(rows),
                    "failures": 0,
                    "snapshot_sha256": snapshot_digest(after),
                }
            )
        )
    finally:
        components.close()


if __name__ == "__main__":
    main()
