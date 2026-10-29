from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

import pytest
from neo4j.exceptions import ServiceUnavailable

from app.db.neo4j import GraphDatabaseClient
from app.extraction.documents import snapshot
from app.extraction.models import ChunkOptions, IngestionFailure, utcnow
from app.extraction.pipeline import ExtractionPipeline
from app.graph.fixtures import read_evaluations, read_fixture
from app.repositories.ingestion import IngestionRepository
from app.services.ingestion import IngestionService
from app.services.ingestion_validation import (
    potential_conflicts,
    rejected_candidates,
    validate_ingestion,
)
from app.services.validation import validate_graph

pytestmark = pytest.mark.integration


@pytest.fixture
def ingestion(loaded_database):
    db = GraphDatabaseClient(loaded_database.settings, write_retry_time=3)
    repository = IngestionRepository(db, ExtractionPipeline(), batch_size=2)
    sources = []

    def document(text="Priya manages Project Atlas.", key=None):
        source = snapshot(key or f"integration:{uuid4().hex}", "fictional-test.txt", text)
        sources.append(source.source_id)
        return source

    try:
        yield repository, IngestionService(repository), document
    finally:
        # Remove only ingestion snapshots/edges created under this test's explicit source IDs.
        rows = repository.read(
            "MATCH (i:Ingestion) WHERE i.source_id IN $sources "
            "RETURN i.id AS id, i.document_id AS document",
            {"sources": sources},
        )
        runs = [r["id"] for r in rows]
        docs = list({r["document"] for r in rows})
        repository.read("MATCH ()-[r]->() WHERE r.ingestion_id IN $runs DELETE r", {"runs": runs})
        repository.read("MATCH (c:Chunk) WHERE c.ingestion_id IN $runs DELETE c", {"runs": runs})
        repository.read(
            "MATCH (d:Document) WHERE d.id IN $docs AND d.origin = 'automatic_ingestion' DELETE d",
            {"docs": docs},
        )
        repository.read("MATCH (i:Ingestion) WHERE i.id IN $runs DELETE i", {"runs": runs})
        repository.read(
            "MATCH (s:IngestionSource) WHERE s.id IN $sources DELETE s", {"sources": sources}
        )
        db.close()


def test_automatic_ingestion_provenance_and_stage1_preservation(ingestion):
    repo, service, make = ingestion
    doc = make(
        "Priya manages Project Atlas. Atlas uses PostgreSQL. "
        "The PostgreSQL instance for Project Atlas is hosted on AWS."
    )
    result = service.ingest(doc, lambda: doc)
    assert result["facts"] == 3 and result["status"] == "ready"
    assert validate_ingestion(repo, doc.source_id)["facts"] == 3
    assert validate_graph(repo.db, read_fixture(), read_evaluations())["facts"] == 30
    assert all(
        r["properties"]["extraction_method"] == "deterministic_rules"
        for r in repo.visible_facts(doc.source_id)
    )


def test_repeated_ingestion_is_idempotent(ingestion):
    repo, service, make = ingestion
    doc = make()
    first = service.ingest(doc, lambda: doc)
    assert service.ingest(doc, lambda: doc) == first
    assert service.ingest(doc, lambda: doc) == first
    assert len(repo.visible_facts(doc.source_id)) == 1
    assert len(repo.results(doc.source_id)) == 1
    run = repo.results(doc.source_id)[0]["ingestion"]
    assert run["state_history"] == ["pending", "processing", "ready"]


def test_distinct_sources_keep_independent_support(ingestion):
    repo, service, make = ingestion
    first, second = make(), make()
    service.ingest(first, lambda: first)
    service.ingest(second, lambda: second)
    one, two = repo.visible_facts(first.source_id)[0], repo.visible_facts(second.source_id)[0]
    assert (one["subject"], one["predicate"], one["object"]) == (
        two["subject"],
        two["predicate"],
        two["object"],
    )
    assert one["properties"]["id"] != two["properties"]["id"]
    assert one["properties"]["source_document_id"] != two["properties"]["source_document_id"]


def test_similar_people_and_deployments_stay_separate(ingestion):
    repo, service, make = ingestion
    doc = make(
        "Priya (Lumen employee 001) manages Project Atlas. "
        "Priya (Cedar employee 003) manages Project Atlas East. "
        "Atlas uses PostgreSQL. Atlas East uses PostgreSQL."
    )
    service.ingest(doc, lambda: doc)
    rows = repo.visible_facts(doc.source_id)
    assert {r["subject"] for r in rows if r["predicate"] == "MANAGES"} == {
        "person:priya",
        "person:priya-cedar",
    }
    assert {r["object"] for r in rows if r["predicate"] == "USES"} == {
        "tech:postgres-atlas",
        "tech:postgres-east",
    }


def test_ambiguous_and_negative_candidates_are_reviewed(ingestion):
    repo, service, make = ingestion
    doc = make("Priya works for Tidal Lantern. Project Atlas does not use Redis.")
    result = service.ingest(doc, lambda: doc)
    assert result["facts"] == 0 and result["rejected_candidates"] >= 2
    assert {r["reason"] for r in rejected_candidates(repo, doc.source_id)} >= {
        "ambiguous_identity",
        "non_asserted_statement",
    }
    assert repo.visible_facts(doc.source_id) == []


def test_incomplete_batches_never_publish_ready(ingestion):
    repo, _, make = ingestion
    doc = make()
    claim = repo.start(doc)
    chunks, _, result = repo.pipeline.extract(doc)
    repo.put_chunks(claim, doc, chunks)
    repo.put_entities(claim, doc, chunks, result)
    with pytest.raises(IngestionFailure, match="incomplete_fact_batch"):
        repo.publish(claim, doc, chunks, result)
    assert repo.summary(doc.source_id)["status"] == "processing"
    assert repo.visible_facts(doc.source_id) == []


def test_missing_persisted_source_chunk_blocks_fact_write(ingestion):
    repo, _, make = ingestion
    doc = make()
    claim = repo.start(doc)
    chunks, batch, result = repo.pipeline.extract(doc)
    with pytest.raises(IngestionFailure, match="missing_persisted_source_evidence"):
        repo.put_facts(claim, doc, chunks, batch, result)
    assert repo.read(
        "MATCH ()-[r {ingestion_id: $run}]->() RETURN count(r) AS count", {"run": claim.run_id}
    ) == [{"count": 0}]


def test_failed_ingestion_is_hidden_and_can_be_reprocessed(ingestion, monkeypatch):
    repo, service, make = ingestion
    doc = make()
    publish = repo.publish
    monkeypatch.setattr(
        repo, "publish", lambda *args: (_ for _ in ()).throw(IngestionFailure("interrupted"))
    )
    with pytest.raises(IngestionFailure, match="interrupted"):
        service.ingest(doc, lambda: doc)
    assert repo.summary(doc.source_id)["status"] == "failed"
    assert repo.visible_facts(doc.source_id) == []
    assert repo.read(
        "MATCH ()-[r]->() WHERE r.source_document_id = $id RETURN count(r) AS count", {"id": doc.id}
    ) == [{"count": 1}]
    monkeypatch.setattr(repo, "publish", publish)
    assert service.ingest(doc, lambda: doc)["facts"] == 1
    assert len(repo.visible_facts(doc.source_id)) == 1


def test_source_changes_hide_old_assertions_and_preserve_other_sources(ingestion):
    repo, service, make = ingestion
    key = f"integration:change:{uuid4().hex}"
    first = make("Redis is hosted on GCP.", key)
    independent = make("Redis is hosted on GCP.")
    changed = make("Redis is hosted on AWS.", key)
    service.ingest(first, lambda: first)
    service.ingest(independent, lambda: independent)
    claim = repo.start(changed)
    assert repo.visible_facts(first.source_id) == []
    assert len(repo.visible_facts(independent.source_id)) == 1
    repo.fail(claim, "interrupted_before_write")
    assert service.ingest(changed, lambda: changed)["facts"] == 1
    assert repo.visible_facts(first.source_id)[0]["object"] == "platform:aws"
    assert repo.visible_facts(independent.source_id)[0]["object"] == "platform:gcp"
    assert len(repo.results(first.source_id)) == 2
    assert repo.read(
        "MATCH ()-[r]->() WHERE r.source_document_id = $id RETURN count(r) AS n", {"id": first.id}
    ) == [{"n": 1}]


def test_source_changed_during_processing_fails_closed(ingestion):
    repo, service, make = ingestion
    key = f"integration:race:{uuid4().hex}"
    original, changed = make("Redis is hosted on GCP.", key), make("Redis is hosted on AWS.", key)
    with pytest.raises(IngestionFailure, match="source_changed_during_processing"):
        service.ingest(original, lambda: changed)
    assert repo.summary(original.source_id)["status"] == "failed"
    assert repo.visible_facts(original.source_id) == []


def test_stale_extraction_version_cannot_be_written(ingestion):
    repo, _, make = ingestion
    doc = make()
    claim = repo.start(doc)
    stale = ExtractionPipeline(ChunkOptions(size=512, overlap=16))
    chunks, batch, result = stale.extract(doc)
    with pytest.raises(IngestionFailure, match="stale_processing_version"):
        repo.put_facts(claim, doc, chunks, batch, result)
    assert repo.visible_facts(doc.source_id) == []


def test_current_reader_excludes_old_processing_configuration(ingestion):
    repo, service, make = ingestion
    doc = make()
    service.ingest(doc, lambda: doc)
    other = IngestionRepository(repo.db, ExtractionPipeline(ChunkOptions(size=512, overlap=16)))
    assert other.visible_facts(doc.source_id) == []


def test_expired_interrupted_claim_can_be_recovered(ingestion):
    repo, service, make = ingestion
    doc = make()
    old = repo.start(doc)
    repo.read("MATCH (s:IngestionSource {id: $id}) SET s.lease_until = 0", {"id": doc.source_id})
    assert service.ingest(doc, lambda: doc)["status"] == "ready"
    with pytest.raises(IngestionFailure, match="stale_ingestion_claim"):
        repo.put_chunks(old, doc, repo.pipeline.extract(doc)[0])
    run = repo.results(doc.source_id)[0]["ingestion"]
    assert "failed" in run["state_history"]


def test_concurrent_same_document_has_one_writer(ingestion, monkeypatch):
    repo, service, make = ingestion
    doc = make()
    started, release = Event(), Event()
    extract = repo.pipeline.extract

    def held(document):
        started.set()
        assert release.wait(20)
        return extract(document)

    monkeypatch.setattr(repo.pipeline, "extract", held)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(service.ingest, doc, lambda: doc)
        try:
            assert started.wait(20)
            with pytest.raises(IngestionFailure, match="ingestion_busy"):
                service.ingest(doc, lambda: doc)
        finally:
            release.set()
        assert first.result(timeout=40)["status"] == "ready"
    assert len(repo.visible_facts(doc.source_id)) == 1


def test_real_managed_transaction_retry_and_commit_replay_are_idempotent(ingestion):
    repo, _, make = ingestion
    doc = make()
    claim = repo.start(doc)
    chunks, batch, result = repo.pipeline.extract(doc)
    repo.put_chunks(claim, doc, chunks)
    repo.put_entities(claim, doc, chunks, result)
    row = repo.fact_row(claim, result.facts[0])
    epoch, calls = utcnow().timestamp(), []

    def retryable(tx):
        repo._put_facts(tx, claim, "MANAGES", [row], epoch)
        calls.append(
            "called"
        )  # Test instrumentation only; production callbacks have no external effects.
        if len(calls) == 1:
            raise ServiceUnavailable("Injected pre-commit retry")

    repo.write(retryable)
    assert len(calls) >= 2
    repo.write(repo._put_facts, claim, "MANAGES", [row], epoch)
    first = repo.publish(claim, doc, chunks, result)
    assert repo.publish(claim, doc, chunks, result) == first
    assert len(repo.visible_facts(doc.source_id)) == 1


def test_potential_conflicts_preserve_both_sources(ingestion):
    repo, service, make = ingestion
    doc = make("The Redis instance for Project Beacon is hosted on AWS.")
    service.ingest(doc, lambda: doc)
    conflicts = potential_conflicts(repo, doc.source_id)
    assert any(
        r["other_object"] == "platform:gcp" and r["object"] == "platform:aws" for r in conflicts
    )
    assert validate_graph(repo.db, read_fixture(), read_evaluations())["facts"] == 30


def test_provenance_audit_detects_database_tampering(ingestion):
    repo, service, make = ingestion
    doc = make()
    service.ingest(doc, lambda: doc)
    row = repo.visible_facts(doc.source_id)[0]
    id, original = row["properties"]["id"], row["properties"]["quote"]
    try:
        repo.read("MATCH ()-[r {id: $id}]->() SET r.quote = 'Unsupported assertion'", {"id": id})
        with pytest.raises(IngestionFailure, match="stored_fact_provenance_mismatch"):
            validate_ingestion(repo, doc.source_id)
    finally:
        repo.read("MATCH ()-[r {id: $id}]->() SET r.quote = $quote", {"id": id, "quote": original})


def test_database_outage_is_safe_then_recovery_succeeds(ingestion):
    import socket

    repo, service, make = ingestion
    doc = make()
    with socket.socket() as socket_guard:
        socket_guard.bind(("127.0.0.1", 0))
        port = socket_guard.getsockname()[1]
        settings = repo.db.settings.model_copy(update={"neo4j_uri": f"bolt://127.0.0.1:{port}"})
        disconnected = GraphDatabaseClient(settings)
        try:
            offline = IngestionService(IngestionRepository(disconnected, repo.pipeline))
            with pytest.raises(IngestionFailure, match="database_unavailable"):
                offline.ingest(doc, lambda: doc)
        finally:
            disconnected.close()
    assert service.ingest(doc, lambda: doc)["status"] == "ready"


def test_empty_document_can_complete_with_zero_facts(ingestion):
    repo, service, make = ingestion
    doc = make("")
    result = service.ingest(doc, lambda: doc)
    assert result["chunks"] == result["facts"] == 0
    assert validate_ingestion(repo, doc.source_id)["status"] == "valid"


@pytest.mark.parametrize("failure", ["deleted", "corrupt_encoding"])
def test_unreadable_updated_local_source_invalidates_only_its_own_evidence(
    ingestion, tmp_path, failure
):
    from app.extraction.documents import LocalDocumentLoader

    repo, service, make = ingestion
    filename = f"test-{uuid4().hex}.txt"
    path = tmp_path / filename
    text = "Priya manages Project Atlas."
    path.write_bytes(text.encode())
    loader = LocalDocumentLoader(tmp_path)
    doc = loader.load(filename)
    make(
        text, f"fictional-local:{filename}"
    )  # Register the logical source for precise test cleanup.
    independent = make(text)
    service.ingest(independent, lambda: independent)
    service.ingest_local(loader, filename)
    if failure == "deleted":
        path.unlink()
    else:
        path.write_bytes(b"\xff")
    with pytest.raises(IngestionFailure):
        service.ingest_local(loader, filename)
    assert repo.summary(doc.source_id)["status"] == "failed"
    assert repo.visible_facts(doc.source_id) == []
    assert len(repo.visible_facts(independent.source_id)) == 1
    path.write_bytes(text.encode())
    assert service.ingest_local(loader, filename)["facts"] == 1
    assert len(repo.visible_facts(doc.source_id)) == 1
