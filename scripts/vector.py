"""Explicit model preparation, canonical corpus indexing, and local vector query CLI."""

import argparse
import json

from app.core.config import Settings
from app.db.neo4j import DatabaseUnavailable, GraphDatabaseClient
from app.extraction.documents import LocalDocumentLoader, fixture_documents
from app.extraction.models import ChunkOptions, IngestionFailure
from app.extraction.pipeline import ExtractionPipeline
from app.graph.fixtures import ROOT
from app.vector.embedding import MODEL, REVISION, MiniLM
from app.vector.indexing import VectorIndexer
from app.vector.models import VectorFailure
from app.vector.repository import VectorRepository
from app.vector.retrieval import VectorOnlyService


def corpus_documents():
    loader = LocalDocumentLoader()
    original = [
        *fixture_documents(),
        *[
            loader.load(n)
            for n in ("atlas.txt", "cedar.md", "conflicting-hosting.txt", "review-required.md")
        ],
    ]
    # Text corpus only. Gold questions/answers/facts are never read by runtime modules.
    from app.extraction.documents import snapshot

    path = ROOT / "data/fictional/stage3_corpus.json"
    if path.exists():
        original.extend(
            snapshot(f"stage3:{d['id']}", f"stage3/{d['id']}.txt", d["text"])
            for d in json.loads(path.read_text(encoding="utf-8"))["documents"]
        )
    return original


def components(settings):
    db = GraphDatabaseClient(settings, write_retry_time=settings.neo4j_write_retry_time)
    model = MiniLM(settings.embedding_startup_timeout, settings.embedding_inference_timeout)
    repo = VectorRepository(db, settings.vector_corpus)
    return db, model, repo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare-model", "index", "query", "status"])
    parser.add_argument("--question")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    if args.command == "prepare-model":
        from huggingface_hub import snapshot_download

        # Public, free model files. No custom model code or provider inference.
        snapshot_download(
            MODEL,
            revision=REVISION,
            allow_patterns=["*.json", "*.txt", "*.safetensors", "1_Pooling/*", "2_Normalize/*"],
            etag_timeout=20,
        )
        print(json.dumps({"model": MODEL, "revision": REVISION, "cached": True}))
        return
    settings = Settings()
    db, model, repo = components(settings)
    try:
        if args.command == "index":
            if settings.app_env != "development":
                parser.error("Indexing requires development mode")
            repo.require_index()
            # Ingestion is explicit and retains the Stage 2 source publication contract.
            from app.repositories.ingestion import IngestionRepository
            from app.services.ingestion import IngestionService

            pipeline = ExtractionPipeline(
                ChunkOptions(
                    size=settings.ingestion_chunk_size, overlap=settings.ingestion_chunk_overlap
                )
            )
            service = IngestionService(IngestionRepository(db, pipeline))
            documents = corpus_documents()
            for document in documents:

                def refresh(source=document.source_id):
                    return next(d for d in corpus_documents() if d.source_id == source)

                service.ingest(document, refresh)
            result = VectorIndexer(repo, model).index(
                [d.source_id for d in documents], pipeline.version
            )
            result.update(model=MODEL, revision=REVISION, embedding_version=model.version)
        elif args.command == "status":
            index = repo.require_index()
            result = {
                "index": index["name"],
                "state": index["state"],
                "build": repo.current(model.version),
            }
        else:
            if args.question is None:
                parser.error("--question is required")
            result = (
                VectorOnlyService(repo, model)
                .retrieve_vector_only(args.question, args.top_k)
                .model_dump()
            )
        print(json.dumps(result, indent=2))
    except (VectorFailure, IngestionFailure, DatabaseUnavailable) as exc:
        category = (
            exc.category
            if isinstance(exc, (VectorFailure, IngestionFailure))
            else "database_unavailable"
        )
        print(json.dumps({"error": category}))
        raise SystemExit(1) from None
    finally:
        model.close()
        db.close()


if __name__ == "__main__":
    main()
