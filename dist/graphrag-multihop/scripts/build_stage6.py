"""Build the isolated challenge using source documents alone; never read gold."""

import json
import time

from app.aligned.discovery import discover
from app.db.migrations import migrate
from app.extraction.models import SourceDocument
from app.extraction.pipeline import ExtractionPipeline
from app.extraction.registry import EntityRegistry
from app.graph.schema import DIRECTIONS, FactType
from app.graph_rag.models import Budget
from app.graph_rag.repository import edge_key
from app.repositories.ingestion import IngestionRepository
from app.services.ingestion import IngestionService
from app.vector.indexing import VectorIndexer
from scripts.stage5_support import aligned_snapshot
from scripts.stage6_runtime import DATA, Components
from scripts.stage6_support import check_history, digest, save


def main():
    check_history()
    documents = [
        SourceDocument.model_validate(d) for d in json.loads((DATA / "sources.json").read_text())
    ]
    discovered = discover(documents)
    (DATA / "registry.json").write_text(discovered.registry.model_dump_json(indent=2) + "\n")
    pipeline = ExtractionPipeline(registry=EntityRegistry(DATA / "registry.json"))
    assertions, summaries, rejections = [], [], []
    for doc in documents:
        chunks, batch, result = pipeline.extract(doc)
        summaries.append(
            {
                "source_id": doc.source_id,
                "document_id": doc.id,
                "content_hash": doc.content_hash,
                "chunks": len(chunks),
                "candidates": len(batch.relations),
                "accepted": len(result.facts),
            }
        )
        rejections.extend(r.model_dump(mode="json") for r in result.rejections)
        assertions.extend(
            {
                "id": f.id,
                "kind": f.candidate.predicate.value,
                "source": f.subject_id,
                "target": f.object_id,
                "source_id": doc.source_id,
                "document_id": doc.id,
                "content_hash": doc.content_hash,
            }
            for f in result.facts
        )
    corpus = {
        "version": "stage6-source-only-v1",
        "processing_version": pipeline.version,
        "registry_version": pipeline.registry.version,
        "source_ids": sorted(d.source_id for d in documents),
        "documents": [
            {k: s[k] for k in ("source_id", "document_id", "content_hash")} for s in summaries
        ],
        "assertions": sorted(assertions, key=lambda a: a["id"]),
    }
    (DATA / "corpus.json").write_text(json.dumps(corpus, indent=2) + "\n")
    components = Components()
    try:
        db = components.db
        deadline = time.monotonic() + 120
        while not db.ready() and time.monotonic() < deadline:
            time.sleep(1)
        if not (db.ready()):
            raise AssertionError("Challenge Neo4j did not become ready")
        migrate(db)
        # Managed write retries only for ingestion. Read query driver remains retry=0.
        from app.db.neo4j import GraphDatabaseClient

        writer = GraphDatabaseClient(components.settings, write_retry_time=3)
        started = time.perf_counter()
        try:
            ingest = IngestionService(IngestionRepository(writer, pipeline))
            first = [ingest.ingest(d, lambda d=d: d) for d in documents]
            second = [ingest.ingest(d, lambda d=d: d) for d in documents]
            if not (first == second):
                raise AssertionError()
        finally:
            writer.close()
        ingestion_ms = (time.perf_counter() - started) * 1000
        indexer = VectorIndexer(components.vector.repo, components.model)
        index = indexer.index(corpus["source_ids"], pipeline.version)
        repeated = indexer.index(corpus["source_ids"], pipeline.version)
        if not (repeated["cached"] and index["build_id"] == repeated["build_id"]):
            raise AssertionError()
        rows = db.execute(
            "MATCH (a:GraphNode)-[r]->(b:GraphNode) WHERE type(r) IN $types "
            "RETURN {properties:properties(a),labels:labels(a)} AS a, "
            "{properties:properties(b),labels:labels(b)} AS b, "
            "{source:a.id,target:b.id,kind:type(r),properties:properties(r)} AS edge ORDER BY r.id",
            {"types": [f.value for f in FactType]},
            timeout=30,
        )
        graph = components.graph
        budget = Budget(120)
        metadata = graph.repo.metadata([{"edges": [r["edge"]]} for r in rows], budget)
        cache = {}
        for row in rows:
            source, target = DIRECTIONS[FactType(row["edge"]["kind"])]
            graph.provenance.entity(row["a"], source)
            graph.provenance.entity(row["b"], target)
            graph.provenance.edge(row["edge"], metadata[edge_key(row["edge"])], cache, budget)
        snapshot = aligned_snapshot(db)
        save("challenge_snapshot.json", snapshot)
        stored = db.execute(
            "MATCH (n:GraphNode) WHERE n.id IN $ids RETURN n.id AS id", {"ids": discovered.new_ids}
        )
        save(
            "build_manifest.json",
            {
                "documents": summaries,
                "documents_ingested": len(documents),
                "registry_entries": len(pipeline.registry.entries),
                "new_registry_identities": len(discovered.new_ids),
                "entities_created": len(stored),
                "reused_historical_entities_stored": 0,
                "duplicate_ids": len(discovered.registry.entries) - len(pipeline.registry.entries),
                "source_grounded_mentions": discovered.mentions,
                "discovery_rejections": discovered.rejections,
                "candidate_relationships": sum(s["candidates"] for s in summaries),
                "accepted_facts": len(rows),
                "rejections": rejections,
                "provenance_failures": 0,
                "provenance_checked": len(rows),
                "idempotent": True,
                "processing_version": pipeline.version,
                "registry_version": pipeline.registry.version,
                "snapshot_sha256": digest(
                    (json.dumps(snapshot, sort_keys=True, indent=2) + "\n").encode()
                ),
                "index": index,
                "repeat_index": repeated,
                "ingestion_ms": ingestion_ms,
                "identity_policy": "Existing source-context policy; no gold IDs; "
                "identical full-name/org "
                "mentions coalesce, explicit distinct employee qualifiers stay separate. "
                "No claim of resolving indistinguishable homonyms.",
                "merge_events": [
                    {"canonical_id": e.entity.id, "aliases": e.aliases, "scope": e.entity.scope}
                    for e in discovered.registry.entries
                    if e.entity.id in discovered.new_ids
                ],
            },
        )
        save("index_verification.json", {"index": components.vector.repo.require_index()})
        print(
            json.dumps(
                {
                    "documents": len(documents),
                    "facts": len(rows),
                    "new_entities_stored": len(stored),
                    "provenance_failures": 0,
                }
            )
        )
    finally:
        components.close()


if __name__ == "__main__":
    main()
