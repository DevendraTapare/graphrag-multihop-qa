import pytest

from app.extraction.documents import snapshot
from app.extraction.models import IngestionFailure
from app.extraction.pipeline import ExtractionPipeline


@pytest.fixture
def proof():
    pipeline = ExtractionPipeline()
    document = snapshot("unit:proof", "proof.txt", "Priya manages Project Atlas.")
    chunks, batch, result = pipeline.extract(document)
    return pipeline, document, chunks, batch, result


@pytest.mark.parametrize(
    "mutation,category",
    [
        ("document", "missing_source_document"),
        ("chunk", "missing_source_chunk"),
        ("offset", "invalid_evidence_offsets"),
        ("quote", "evidence_text_mismatch"),
        ("direction", "invalid_relationship_direction"),
        ("version", "stale_extraction_version"),
        ("rule", "unapproved_relation_pattern"),
        ("mention", "ungrounded_entity_mention"),
    ],
)
def test_candidate_validation_is_independent_of_score(proof, mutation, category):
    pipeline, document, chunks, batch, _ = proof
    candidate = batch.relations[0]
    match mutation:
        case "document":
            candidate = candidate.model_copy(update={"source_document_id": "doc:absent"})
        case "chunk":
            candidate = candidate.model_copy(update={"source_chunk_id": "chunk:absent"})
        case "offset":
            candidate = candidate.model_copy(update={"end": 999})
        case "quote":
            candidate = candidate.model_copy(update={"evidence": "Priya manages Echo."})
        case "direction":
            candidate = candidate.model_copy(
                update={"subject": candidate.object, "object": candidate.subject}
            )
        case "version":
            candidate = candidate.model_copy(update={"extraction_version": "rules:stale"})
        case "rule":
            candidate = candidate.model_copy(update={"rule_id": "invented-rule"})
        case "mention":
            candidate = candidate.model_copy(
                update={"subject": candidate.subject.model_copy(update={"mention": "Morgan"})}
            )
    with pytest.raises(IngestionFailure, match=category):
        pipeline.validator.accept_relation(
            document, chunks, candidate, batch.entities, pipeline.version
        )


@pytest.mark.parametrize(
    "mutation", ["text", "document_hash", "chunk_hash", "chunk_version", "chunk_offset"]
)
def test_invalid_or_stale_sources_fail_closed(proof, mutation):
    pipeline, document, chunks, batch, _ = proof
    match mutation:
        case "text":
            document = document.model_copy(update={"text": "Changed source."})
        case "document_hash":
            document = document.model_copy(update={"content_hash": "a" * 64})
        case "chunk_hash":
            chunks = [chunks[0].model_copy(update={"content_hash": "b" * 64})]
        case "chunk_version":
            chunks = [chunks[0].model_copy(update={"processing_version": "stale"})]
        case "chunk_offset":
            chunks = [chunks[0].model_copy(update={"start": 1})]
    with pytest.raises(IngestionFailure):
        pipeline.validator.validate(document, chunks, batch, pipeline.version)


def test_forged_canonical_id_is_rejected(proof):
    pipeline, document, chunks, batch, result = proof
    forged = result.facts[0].model_copy(update={"subject_id": "person:priya-cedar"})
    with pytest.raises(IngestionFailure, match="fact_proof_mismatch"):
        pipeline.validator.verify_fact(forged, document, chunks, batch.entities, pipeline.version)


def test_quote_containment_does_not_prove_an_assertion(proof):
    pipeline, _, _, batch, _ = proof
    document = snapshot(
        "unit:misleading", "misleading.txt", "It is false that Priya manages Project Atlas."
    )
    chunks, _, _ = pipeline.extract(document)
    original = batch.relations[0]
    candidate = original.model_copy(
        update={
            "source_document_id": document.id,
            "source_chunk_id": chunks[0].id,
            "start": len("It is false that "),
            "end": len(document.text),
        }
    )
    assert candidate.evidence in document.text
    with pytest.raises(IngestionFailure, match="unapproved_relation_pattern"):
        pipeline.validator.accept_relation(
            document, chunks, candidate, batch.entities, pipeline.version
        )


def test_extractor_cannot_inject_fake_disambiguation_context():
    from app.extraction.models import EntityCandidate

    pipeline = ExtractionPipeline()
    document = snapshot("unit:fake-context", "fake.txt", "PostgreSQL is hosted on AWS.")
    chunks, batch, _ = pipeline.extract(document)
    fake = EntityCandidate(
        id="mention:fake",
        mention="Project Atlas",
        label="Project",
        source_document_id=document.id,
        source_chunk_id=chunks[0].id,
        start=0,
        end=13,
        extraction_version=pipeline.extractor.version,
    )
    with pytest.raises(IngestionFailure, match="ambiguous_identity"):
        pipeline.validator.accept_relation(
            document, chunks, batch.relations[0], [*batch.entities, fake], pipeline.version
        )


def test_code_example_cannot_supply_context_for_an_ambiguous_fact():
    pipeline = ExtractionPipeline()
    document = snapshot(
        "unit:code-context",
        "code.txt",
        "```text\nProject Atlas uses PostgreSQL.\n```\nPostgreSQL is hosted on AWS.",
    )
    assert pipeline.extract(document)[2].facts == []
