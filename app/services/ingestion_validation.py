import json

from app.extraction.models import IngestionFailure, SourceDocument, TextChunk
from app.repositories.ingestion import Claim, IngestionRepository


def stored_document(repository: IngestionRepository, document_id: str) -> SourceDocument:
    rows = repository.read(
        "MATCH (d:Document {id: $id}) RETURN properties(d) AS doc", {"id": document_id}
    )
    if len(rows) != 1:
        raise IngestionFailure("missing_source_document")
    fields = SourceDocument.model_fields
    return SourceDocument.model_validate({k: v for k, v in rows[0]["doc"].items() if k in fields})


def validate_ingestion(repository: IngestionRepository, source_id: str) -> dict:
    summary = repository.summary(source_id)
    if summary["status"] != "ready":
        raise IngestionFailure("ingestion_not_ready")
    document = stored_document(repository, summary["document_id"])
    chunks, batch, result = repository.pipeline.extract(document)
    if summary["processing_version"] != repository.pipeline.version:
        raise IngestionFailure("stale_processing_version")
    actual_chunks = repository.read(
        "MATCH (c:Chunk {ingestion_id: $run}) RETURN properties(c) AS chunk",
        {"run": summary["run_id"]},
    )
    recovered = [
        TextChunk.model_validate(
            {k: v for k, v in row["chunk"].items() if k in TextChunk.model_fields}
        )
        for row in actual_chunks
    ]
    if {c.id: c for c in recovered} != {c.id: c for c in chunks} or len(recovered) != len(chunks):
        raise IngestionFailure("stored_chunk_provenance_mismatch")
    for chunk in chunks:
        links = repository.read(
            "MATCH (:Chunk {id: $chunk})-[r:PART_OF|DERIVED_FROM]->(d:Document) "
            "WHERE r.ingestion_id = $run RETURN type(r) AS type, d.id AS document",
            {"chunk": chunk.id, "run": summary["run_id"]},
        )
        if sorted((r["type"], r["document"]) for r in links) != [
            ("DERIVED_FROM", document.id),
            ("PART_OF", document.id),
        ]:
            raise IngestionFailure("orphan_source_chunk")
    claim = Claim(
        source_id,
        summary["run_id"],
        document.id,
        document.content_hash,
        repository.pipeline.version,
        "audit",
    )
    expected = {f.id: repository.fact_row(claim, f) for f in result.facts}
    actual = repository.visible_facts(source_id)
    if len(actual) != len(expected):
        raise IngestionFailure("missing_or_ineligible_facts")
    for row in actual:
        props = row["properties"]
        expected_row = expected.get(props.get("id"))
        if not expected_row:
            raise IngestionFailure("unexpected_accepted_fact")
        for field in expected_row["props"]:
            if field != "created_at" and props.get(field) != expected_row["props"][field]:
                raise IngestionFailure("stored_fact_provenance_mismatch")
        fact = next(f for f in result.facts if f.id == props["id"])
        if (row["subject"], row["predicate"], row["object"]) != (
            fact.subject_id,
            fact.candidate.predicate.value,
            fact.object_id,
        ):
            raise IngestionFailure("invalid_relationship_direction")
        repository.pipeline.validator.verify_fact(
            fact, document, chunks, batch.entities, claim.version
        )
    return {
        "source_id": source_id,
        "status": "valid",
        "facts": len(actual),
        "chunks": len(chunks),
        "content_hash": document.content_hash,
    }


def potential_conflicts(repository: IngestionRepository, source_id: str) -> list[dict]:
    return repository.read(
        """
        MATCH (source:IngestionSource {id: $source})
        MATCH (i:Ingestion {id: source.current_run_id, status: 'ready'})
        MATCH (a)-[r:HOSTED_ON|BELONGS_TO]->(b), (a)-[other:HOSTED_ON|BELONGS_TO]->(c)
        WHERE source.status = 'ready' AND r.ingestion_id = i.id
          AND r.provenance_status = 'verified_rule' AND b.id <> c.id AND type(r) = type(other)
          AND (other.extraction_method = 'manual_fixture' OR EXISTS {
            MATCH (s:IngestionSource), (j:Ingestion {id: s.current_run_id, status: 'ready'})
            WHERE s.status = 'ready' AND other.ingestion_id = j.id
              AND other.provenance_status = 'verified_rule'
          })
        RETURN r.id AS fact, other.id AS other_fact, a.id AS subject, type(r) AS predicate,
               b.id AS object, c.id AS other_object, other.source_document_id AS other_source
        ORDER BY fact, other_fact
    """,
        {"source": source_id},
    )


def rejected_candidates(repository: IngestionRepository, source_id: str) -> list[dict]:
    rows = repository.read(
        "MATCH (s:IngestionSource {id: $source}), (i:Ingestion {id: s.desired_run_id}) "
        "RETURN i.rejections_json AS rejected",
        {"source": source_id},
    )
    if not rows:
        raise IngestionFailure("ingestion_not_found")
    return json.loads(rows[0]["rejected"] or "[]")
