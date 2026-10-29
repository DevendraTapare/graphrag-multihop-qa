import argparse
import json
import re

from app.core.config import Settings
from app.core.logging import configure_logging
from app.db.neo4j import GraphDatabaseClient
from app.extraction.documents import LocalDocumentLoader, fixture_documents
from app.extraction.models import ChunkOptions, IngestionFailure
from app.extraction.pipeline import ExtractionPipeline
from app.repositories.ingestion import IngestionRepository
from app.services.ingestion import IngestionService
from app.services.ingestion_validation import (
    potential_conflicts,
    rejected_candidates,
    validate_ingestion,
)


def main():
    parser = argparse.ArgumentParser(
        description="Local fictional document ingestion; no HTTP mutations"
    )
    parser.add_argument(
        "command",
        choices=["ingest", "fixtures", "list", "summary", "rejections", "validate", "conflicts"],
    )
    parser.add_argument("target", nargs="?", help="Relative fictional filename or source ID")
    parser.add_argument("--chunk-size", type=int)
    parser.add_argument("--overlap", type=int)
    args = parser.parse_args()
    settings = Settings()
    if settings.app_env != "development":
        parser.error("Stage 2 CLI requires APP_ENV=development")
    configure_logging(settings.neo4j_password.get_secret_value())
    try:
        options = ChunkOptions(
            size=args.chunk_size if args.chunk_size is not None else settings.ingestion_chunk_size,
            overlap=args.overlap if args.overlap is not None else settings.ingestion_chunk_overlap,
        )
    except ValueError:
        parser.error("Chunk size must be 32..16000; overlap must be smaller and nonnegative")
    pipeline = ExtractionPipeline(options)
    db = GraphDatabaseClient(settings, write_retry_time=settings.neo4j_write_retry_time)
    repository = IngestionRepository(
        db, pipeline, settings.ingestion_batch_size, settings.ingestion_lease_seconds
    )
    service = IngestionService(repository)
    loader = LocalDocumentLoader(max_bytes=settings.ingestion_max_bytes)
    try:
        if args.command == "ingest":
            if not args.target:
                parser.error("ingest requires a relative filename below data/fictional")
            result = service.ingest_local(loader, args.target)
        elif args.command == "fixtures":
            result = []
            for document in fixture_documents():

                def refresh(original=document.original_document_id):
                    return next(
                        d for d in fixture_documents() if d.original_document_id == original
                    )

                result.append(service.ingest(document, refresh))
        elif args.command == "list":
            result = repository.results()
            for row in result:
                row["ingestion"].pop("claim_token", None)
        else:
            if not args.target or not re.fullmatch(r"source:[a-f0-9]{40}", args.target):
                parser.error("Provide the source ID returned by ingestion")
            function = {
                "summary": repository.summary,
                "rejections": lambda source: rejected_candidates(repository, source),
                "validate": lambda source: validate_ingestion(repository, source),
                "conflicts": lambda source: potential_conflicts(repository, source),
            }[args.command]
            result = function(args.target)
        print(json.dumps(result, indent=2))
    except IngestionFailure as exc:
        print(json.dumps({"status": "failed", "error_category": exc.category}))
        raise SystemExit(1) from None
    finally:
        db.close()


if __name__ == "__main__":
    main()
