from datetime import datetime

from app.extraction.chunking import sentences
from app.extraction.models import (
    AcceptedFact,
    CandidateBatch,
    EntityCandidate,
    IngestionFailure,
    Rejection,
    RelationCandidate,
    ResolvedEntity,
    SourceDocument,
    TextChunk,
    ValidatedExtraction,
    stable_id,
    text_hash,
)
from app.extraction.registry import EntityRegistry
from app.extraction.rules import DeterministicExtractor
from app.graph.schema import DIRECTIONS


class ProvenanceValidator:
    version = "provenance-v2"

    def __init__(self, registry: EntityRegistry):
        self.registry = registry
        self.approved = DeterministicExtractor(registry)

    def validate_sources(self, document: SourceDocument, chunks: list[TextChunk], version: str):
        if document.content_hash != text_hash(document.text):
            raise IngestionFailure("document_hash_mismatch")
        if document.id != stable_id("autodoc", document.source_id, document.content_hash):
            raise IngestionFailure("document_identity_mismatch")
        if len({c.id for c in chunks}) != len(chunks):
            raise IngestionFailure("duplicate_chunk")
        for chunk in chunks:
            if chunk.document_id != document.id or chunk.content_hash != document.content_hash:
                raise IngestionFailure("missing_or_stale_source_document")
            if chunk.processing_version != version:
                raise IngestionFailure("stale_processing_version")
            if not (0 <= chunk.start < chunk.end <= len(document.text)):
                raise IngestionFailure("invalid_chunk_offsets")
            if document.text[chunk.start : chunk.end] != chunk.text:
                raise IngestionFailure("chunk_text_mismatch")

    def validate_entity(
        self, document: SourceDocument, chunks: list[TextChunk], entity: EntityCandidate
    ):
        chunk = next((c for c in chunks if c.id == entity.source_chunk_id), None)
        if entity.source_document_id != document.id:
            raise IngestionFailure("missing_source_document")
        if not chunk:
            raise IngestionFailure("missing_source_chunk")
        if not chunk.start <= entity.start < entity.end <= chunk.end:
            raise IngestionFailure("invalid_mention_offsets")
        if document.text[entity.start : entity.end] != entity.mention:
            raise IngestionFailure("ungrounded_entity_mention")
        if entity.extraction_version != self.approved.version:
            raise IngestionFailure("stale_extraction_version")
        if entity.id != stable_id(
            "mention",
            document.id,
            entity.start,
            entity.end,
            entity.label,
            entity.extraction_version,
        ):
            raise IngestionFailure("invalid_mention_identity")
        if not any(e.id == entity.id for e in self.approved.extract_entities(document, chunks)):
            raise IngestionFailure("unapproved_entity_span")

    def accept_relation(
        self,
        document: SourceDocument,
        chunks: list[TextChunk],
        candidate: RelationCandidate,
        mentions: list[EntityCandidate],
        version: str,
        created_at: datetime | None = None,
    ) -> AcceptedFact:
        self.validate_sources(document, chunks, version)
        if candidate.source_document_id != document.id:
            raise IngestionFailure("missing_source_document")
        chunk = next((c for c in chunks if c.id == candidate.source_chunk_id), None)
        if not chunk:
            raise IngestionFailure("missing_source_chunk")
        if not chunk.start <= candidate.start < candidate.end <= chunk.end:
            raise IngestionFailure("invalid_evidence_offsets")
        if document.text[candidate.start : candidate.end] != candidate.evidence:
            raise IngestionFailure("evidence_text_mismatch")
        sentence = next(
            (
                s
                for s in sentences(document.text)
                if (s.start, s.end) == (candidate.start, candidate.end)
            ),
            None,
        )
        approved = self.approved.approved_match(sentence) if sentence else None
        if not approved or (approved[0], approved[1]) != (candidate.rule_id, candidate.predicate):
            raise IngestionFailure("unapproved_relation_pattern")
        if candidate.extraction_version != self.approved.version:
            raise IngestionFailure("stale_extraction_version")
        if candidate.id != stable_id(
            "candidate",
            document.id,
            candidate.start,
            candidate.end,
            candidate.predicate,
            self.approved.version,
        ):
            raise IngestionFailure("invalid_candidate_identity")
        if (candidate.subject.label, candidate.object.label) != DIRECTIONS[candidate.predicate]:
            raise IngestionFailure("invalid_relationship_direction")
        for entity, group in ((candidate.subject, "s"), (candidate.object, "o")):
            self.validate_entity(document, chunks, entity)
            expected = (
                candidate.start + approved[2].start(group),
                candidate.start + approved[2].end(group),
            )
            if (entity.start, entity.end) != expected or entity.source_chunk_id != chunk.id:
                raise IngestionFailure("entity_not_grounded_in_relation")
        # Context is source evidence too. Never trust extractor-supplied contextual mentions.
        grounded = self.approved.extract_entities(document, chunks)
        asserted = [s for s in sentences(document.text) if self.approved.approved_match(s)]
        context = [
            e for e in grounded if any(s.start <= e.start < e.end <= s.end for s in asserted)
        ]
        subject = self.registry.resolve(candidate.subject, document, context)
        target = self.registry.resolve(candidate.object, document, context)
        if (
            self.registry.entries[subject].entity.label,
            self.registry.entries[target].entity.label,
        ) != DIRECTIONS[candidate.predicate]:
            raise IngestionFailure("canonical_type_mismatch")
        fields = dict(
            id=stable_id(
                "auto-fact",
                document.source_id,
                document.content_hash,
                version,
                subject,
                candidate.predicate,
                target,
                candidate.start,
                candidate.end,
            ),
            source_id=document.source_id,
            content_hash=document.content_hash,
            processing_version=version,
            ingestion_version=document.ingestion_version,
            subject_id=subject,
            object_id=target,
            candidate=candidate,
        )
        if created_at:
            fields["created_at"] = created_at
        return AcceptedFact(**fields)

    def verify_fact(
        self,
        fact: AcceptedFact,
        document: SourceDocument,
        chunks: list[TextChunk],
        mentions: list[EntityCandidate],
        version: str,
    ) -> None:
        expected = self.accept_relation(
            document, chunks, fact.candidate, mentions, version, fact.created_at
        )
        if fact != expected:
            raise IngestionFailure("fact_proof_mismatch")

    def validate(
        self, document: SourceDocument, chunks: list[TextChunk], batch: CandidateBatch, version: str
    ) -> ValidatedExtraction:
        self.validate_sources(document, chunks, version)
        grounded_context = self.approved.extract_entities(document, chunks)
        resolved, facts, rejected = [], [], list(batch.rejections)
        for entity in batch.entities:
            try:
                self.validate_entity(document, chunks, entity)
                resolved.append(
                    ResolvedEntity(
                        candidate=entity,
                        canonical_id=self.registry.resolve(entity, document, grounded_context),
                    )
                )
            except IngestionFailure as exc:
                rejected.append(
                    Rejection(
                        candidate_id=entity.id,
                        kind="entity",
                        reason=exc.category,
                        source_document_id=document.id,
                        source_chunk_id=entity.source_chunk_id,
                        start=entity.start,
                        end=entity.end,
                        text=entity.mention,
                    )
                )
        seen = set()
        for candidate in batch.relations:
            try:
                fact = self.accept_relation(document, chunks, candidate, batch.entities, version)
                if fact.id not in seen:
                    facts.append(fact)
                    seen.add(fact.id)
            except IngestionFailure as exc:
                rejected.append(
                    Rejection(
                        candidate_id=candidate.id,
                        kind="relationship",
                        reason=exc.category,
                        source_document_id=document.id,
                        source_chunk_id=candidate.source_chunk_id,
                        start=candidate.start,
                        end=candidate.end,
                        text=candidate.evidence,
                    )
                )
        return ValidatedExtraction(entities=resolved, facts=facts, rejections=rejected)
