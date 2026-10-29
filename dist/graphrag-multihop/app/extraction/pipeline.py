from app.extraction.chunking import CHUNKER_VERSION, split_document
from app.extraction.models import (
    CandidateBatch,
    ChunkOptions,
    SourceDocument,
    TextChunk,
    ValidatedExtraction,
    stable_id,
)
from app.extraction.provenance import ProvenanceValidator
from app.extraction.registry import EntityRegistry
from app.extraction.rules import DeterministicExtractor, Extractor


class ExtractionPipeline:
    def __init__(
        self,
        options: ChunkOptions | None = None,
        registry: EntityRegistry | None = None,
        extractor: Extractor | None = None,
    ):
        self.options = options or ChunkOptions()
        self.registry = registry or EntityRegistry()
        self.extractor = extractor or DeterministicExtractor(self.registry)
        self.validator = ProvenanceValidator(self.registry)
        self.version = stable_id(
            "processing",
            self.options.model_dump(),
            self.registry.version,
            self.extractor.version,
            self.validator.version,
            CHUNKER_VERSION,
            SourceDocument.model_fields["ingestion_version"].default,
        )

    def extract(
        self, document: SourceDocument
    ) -> tuple[list[TextChunk], CandidateBatch, ValidatedExtraction]:
        chunks = split_document(document, self.options, self.version)
        entities = self.extractor.extract_entities(document, chunks)
        raw = self.extractor.extract_relations(document, chunks, entities)
        # Revalidate extension output rather than trusting preconstructed model instances.
        batch = CandidateBatch.model_validate(raw.model_dump())
        return chunks, batch, self.validator.validate(document, chunks, batch, self.version)
