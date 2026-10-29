"""Reproduce the 16-document corpus import, provenance audit, and idempotency check."""

import json

from app.core.config import Settings
from app.core.logging import configure_logging
from app.db.neo4j import GraphDatabaseClient
from app.extraction.documents import LocalDocumentLoader, fixture_documents
from app.extraction.models import ChunkOptions
from app.extraction.pipeline import ExtractionPipeline
from app.graph.fixtures import ROOT, read_evaluations, read_fixture
from app.repositories.ingestion import IngestionRepository
from app.services.ingestion import IngestionService
from app.services.ingestion_validation import validate_ingestion
from app.services.validation import validate_graph


def main():
    settings = Settings()
    if settings.app_env != "development":
        raise SystemExit("Corpus verification requires development mode")
    configure_logging(settings.neo4j_password.get_secret_value())
    db = GraphDatabaseClient(settings, write_retry_time=settings.neo4j_write_retry_time)
    pipeline = ExtractionPipeline(
        ChunkOptions(size=settings.ingestion_chunk_size, overlap=settings.ingestion_chunk_overlap)
    )
    repo = IngestionRepository(
        db, pipeline, settings.ingestion_batch_size, settings.ingestion_lease_seconds
    )
    service = IngestionService(repo)
    loader = LocalDocumentLoader(max_bytes=settings.ingestion_max_bytes)
    names = ["atlas.txt", "cedar.md", "conflicting-hosting.txt", "review-required.md"]
    documents = [*fixture_documents(), *[loader.load(name) for name in names]]
    try:

        def ingest(document):
            if document.original_document_id:

                def refresh():
                    return next(
                        d
                        for d in fixture_documents()
                        if d.original_document_id == document.original_document_id
                    )

                return service.ingest(document, refresh)
            return service.ingest_local(loader, document.source_filename)

        first = [ingest(d) for d in documents]
        before = {d.source_id: repo.visible_facts(d.source_id) for d in documents}
        second = [ingest(d) for d in documents]
        after = {d.source_id: repo.visible_facts(d.source_id) for d in documents}
        if first != second or before != after:
            raise RuntimeError("Repeated corpus ingestion changed assertions or summaries")
        audits = [validate_ingestion(repo, d.source_id) for d in documents]
        extraction = [pipeline.extract(d) for d in documents]
        result = {
            "processing_version": pipeline.version,
            "documents_processed": len(documents),
            "fixture_documents": 12,
            "local_documents": 4,
            "raw_entity_mentions": sum(len(batch.entities) for _, batch, _ in extraction),
            "resolved_entity_mentions": sum(len(value.entities) for _, _, value in extraction),
            "unique_canonical_entities": len(
                {e.canonical_id for _, _, value in extraction for e in value.entities}
            ),
            "relationship_candidates": sum(len(batch.relations) for _, batch, _ in extraction),
            "accepted_relationships": sum(r["facts"] for r in first),
            "rejected_candidates": sum(r["rejected_candidates"] for r in first),
            "idempotent_repeat": True,
            "provenance_audits_passed": len(audits),
            "stage1": validate_graph(db, read_fixture(), read_evaluations()),
            "documents": first,
        }
        (ROOT / "reports/stage2-corpus-verification.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps({k: v for k, v in result.items() if k != "documents"}, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
