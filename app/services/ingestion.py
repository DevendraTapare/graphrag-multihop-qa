from collections.abc import Callable

from pydantic import ValidationError

from app.extraction.documents import LocalDocumentLoader
from app.extraction.models import IngestionFailure, SourceDocument
from app.repositories.ingestion import IngestionRepository


class IngestionService:
    def __init__(self, repository: IngestionRepository):
        self.repository = repository
        self.pipeline = repository.pipeline

    def ingest_local(self, loader: LocalDocumentLoader, filename: str) -> dict:
        source_id = loader.source_id(filename)  # Reject invalid paths before any database mutation.
        try:
            document = loader.load(filename)
        except IngestionFailure as exc:
            self.repository.record_load_failure(source_id, filename, exc.category)
            raise
        return self.ingest(document, lambda: loader.load(filename))

    def ingest(self, document: SourceDocument, refresh: Callable[[], SourceDocument]) -> dict:
        document = SourceDocument.model_validate(document.model_dump())
        claim = self.repository.start(document)
        if claim is None:
            current = refresh()
            if (current.id, current.content_hash) != (document.id, document.content_hash):
                # Claim the changed snapshot immediately; never return stale ready evidence.
                return self.ingest(current, refresh)
            return self.repository.summary(document.source_id)
        try:
            chunks, batch, result = self.pipeline.extract(document)
            self.repository.record_plan(claim, chunks, result)
            self.repository.put_chunks(claim, document, chunks)
            self.repository.put_entities(claim, document, chunks, result)
            self.repository.put_facts(claim, document, chunks, batch, result)
            current = refresh()
            if (current.id, current.content_hash, current.ingestion_version) != (
                document.id,
                document.content_hash,
                document.ingestion_version,
            ):
                raise IngestionFailure("source_changed_during_processing")
            return self.repository.publish(claim, document, chunks, result)
        except Exception as exc:
            category = (
                exc.category
                if isinstance(exc, IngestionFailure)
                else (
                    "invalid_extractor_output"
                    if isinstance(exc, ValidationError)
                    else "processing_failed"
                )
            )
            try:
                self.repository.fail(claim, category)
            except IngestionFailure:
                pass  # Outage leaves a processing lease, never a ready document.
            raise IngestionFailure(category) from exc
