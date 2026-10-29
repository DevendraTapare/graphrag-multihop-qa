"""Source-only registry preparation and idempotent isolated Stage 5 ingestion/indexing."""

import argparse
import json

from app.aligned.discovery import VERSION, discover
from app.core.config import Settings
from app.db.migrations import migrate
from app.db.neo4j import GraphDatabaseClient
from app.extraction.pipeline import ExtractionPipeline
from app.extraction.registry import EntityRegistry
from app.graph.fixtures import ROOT
from app.repositories.ingestion import IngestionRepository
from app.services.ingestion import IngestionService
from app.vector.embedding import MiniLM
from app.vector.indexing import VectorIndexer
from app.vector.repository import VectorRepository
from scripts.stage5_support import check_history, save
from scripts.vector import corpus_documents

REGISTRY = ROOT / "data/runtime/stage5_registry.json"


def prepare():
    documents = corpus_documents()  # Only source documents; no questions/answers/gold IDs.
    discovered = discover(documents)
    REGISTRY.write_text(discovered.registry.model_dump_json(indent=2) + "\n", encoding="utf-8")
    pipeline = ExtractionPipeline(registry=EntityRegistry(REGISTRY))
    summaries, rejections, assertions = [], [], []
    for doc in documents:
        chunks, batch, result = pipeline.extract(doc)
        summaries.append(
            {
                "document_id": doc.id,
                "source_id": doc.source_id,
                "content_hash": doc.content_hash,
                "filename": doc.source_filename,
                "chunks": len(chunks),
                "relation_candidates": len(batch.relations),
                "facts": len(result.facts),
                "entity_mentions": len(result.entities),
                "rejected_candidates": len(result.rejections),
                "rejected_relationships": sum(r.kind == "relationship" for r in result.rejections),
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
    manifest = {
        "version": "aligned-corpus-v1",
        "discovery_version": VERSION,
        "processing_version": pipeline.version,
        "registry_version": pipeline.registry.version,
        "source_ids": sorted(d.source_id for d in documents),
        "documents": summaries,
        "new_entity_ids": discovered.new_ids,
        "reused_entity_ids": discovered.reused_ids,
        "discovered_mentions": discovered.mentions,
        "discovery_rejections": discovered.rejections,
        "extraction_rejections": rejections,
        "facts": sum(s["facts"] for s in summaries),
        "rejected_candidates": len(rejections),
        "rejected_relationships": sum(s["rejected_relationships"] for s in summaries),
    }
    save("build_manifest.json", manifest)
    (ROOT / "data/runtime/stage5_corpus.json").write_text(
        json.dumps(
            {
                "version": manifest["version"],
                "processing_version": pipeline.version,
                "registry_version": pipeline.registry.version,
                "source_ids": manifest["source_ids"],
                "documents": [
                    {k: s[k] for k in ("document_id", "source_id", "content_hash")}
                    for s in summaries
                ],
                "assertions": sorted(assertions, key=lambda a: a["id"]),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                k: v
                for k, v in manifest.items()
                if k
                not in {
                    "documents",
                    "discovered_mentions",
                    "extraction_rejections",
                    "source_ids",
                    "new_entity_ids",
                    "reused_entity_ids",
                }
            },
            indent=2,
        )
    )
    print(
        json.dumps(
            {
                "documents": len(documents),
                "registry_entities": len(pipeline.registry.entries),
                "new_entities": len(discovered.new_ids),
            }
        )
    )
    return pipeline, documents, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "backfill", "index"])
    args = parser.parse_args()
    check_history()
    pipeline, documents, manifest = prepare()
    if args.command == "prepare":
        return
    settings = Settings()
    if not (settings.stage5_neo4j_uri != settings.neo4j_uri):
        raise AssertionError()
    db = GraphDatabaseClient(
        settings.model_copy(update={"neo4j_uri": settings.stage5_neo4j_uri}),
        write_retry_time=settings.neo4j_write_retry_time,
    )
    try:
        migrate(db)
        if args.command == "backfill":
            service = IngestionService(IngestionRepository(db, pipeline))
            passes = []
            for _ in range(2):
                results = [service.ingest(doc, lambda doc=doc: doc) for doc in documents]
                facts = db.execute(
                    "MATCH ()-[r]->() WHERE r.provenance_status='verified_rule' "
                    "RETURN r.id AS id,properties(r) AS p ORDER BY r.id",
                    timeout=30,
                )
                passes.append({"results": results, "assertions": facts})
            if not (passes[0] == passes[1]):
                raise AssertionError("Backfill must be idempotent")
            save(
                "backfill_verification.json",
                {
                    "idempotent": True,
                    "passes": 2,
                    "source_count": len(documents),
                    "fact_count": len(passes[0]["assertions"]),
                    "processing_version": pipeline.version,
                    "ingestions": passes[1]["results"],
                },
            )
            print(json.dumps({"idempotent": True, "facts": len(passes[1]["assertions"])}))
        else:
            model = MiniLM()
            try:
                repo = VectorRepository(db, "stage5-aligned")
                result = VectorIndexer(repo, model).index(manifest["source_ids"], pipeline.version)
                repeated = VectorIndexer(repo, model).index(
                    manifest["source_ids"], pipeline.version
                )
                if not (repeated["cached"] and result["build_id"] == repeated["build_id"]):
                    raise AssertionError()
                save(
                    "index_verification.json",
                    {"first": result, "repeat": repeated, "index": repo.require_index()},
                )
                print(json.dumps(result))
            finally:
                model.close()
    finally:
        db.close()


if __name__ == "__main__":
    main()
