"""Real cached MiniLM and a separate disposable Neo4j Community container, no mocks."""

import asyncio
import concurrent.futures
import os
import secrets
import socket
import subprocess
import time
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.db.migrations import migrate
from app.db.neo4j import DatabaseUnavailable, GraphDatabaseClient
from app.extraction.documents import snapshot
from app.extraction.pipeline import ExtractionPipeline
from app.main import create_app
from app.repositories.ingestion import IngestionRepository
from app.services.ingestion import IngestionService
from app.vector.embedding import MiniLM
from app.vector.indexing import VectorIndexer
from app.vector.models import VectorFailure
from app.vector.repository import VectorRepository
from app.vector.retrieval import VectorOnlyService
from tests.client import api_client

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def isolated_vector_database():
    name = "graphrag-stage3-test-" + uuid4().hex[:12]
    password = secrets.token_hex(24)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    env = {**os.environ, "NEO4J_AUTH": f"neo4j/{password}"}
    subprocess.run(
        [
            "docker",
            "run",
            "--detach",
            "--name",
            name,
            "--publish",
            f"127.0.0.1:{port}:7687",
            "--env",
            "NEO4J_AUTH",
            "--env",
            "NEO4J_server_memory_heap_initial__size=128m",
            "--env",
            "NEO4J_server_memory_heap_max__size=256m",
            "--env",
            "NEO4J_server_memory_pagecache_size=128m",
            "neo4j:5.26.32-community",
        ],
        env=env,
        check=True,
        capture_output=True,
        timeout=60,
    )
    settings = Settings(
        _env_file=None,
        neo4j_uri=f"bolt://127.0.0.1:{port}",
        neo4j_password=password,
        neo4j_connection_timeout=1,
    )
    db = GraphDatabaseClient(settings, write_retry_time=3)
    try:
        deadline = time.monotonic() + 120
        while not db.ready() and time.monotonic() < deadline:
            time.sleep(1)
        assert db.ready(), "Isolated Neo4j must start; no silent skip"
        migrate(db)
        yield db
    finally:
        db.close()
        subprocess.run(
            ["docker", "rm", "--force", name], check=True, capture_output=True, timeout=60
        )


@pytest.fixture(scope="module")
def real_minilm():
    model = MiniLM()
    try:
        vectors = model.encode(["A real local embedding smoke test."])
        assert len(vectors[0]) == 384
        yield model
    finally:
        model.close()


@pytest.fixture
def vector_setup(isolated_vector_database, real_minilm):
    db = isolated_vector_database
    pipeline = ExtractionPipeline()
    ingest = IngestionService(IngestionRepository(db, pipeline))
    identity = uuid4().hex
    docs = [
        snapshot(f"vector-test:{identity}:{i}", f"{i}.txt", text)
        for i, text in enumerate(
            [
                "Asha Rao manages Project Boreal.",
                "Project Boreal uses its CobaltDB instance.",
                "The CobaltDB instance for Project Boreal is hosted on AWS.",
                "Project Boreal East uses its SQLite instance.",
            ]
        )
    ]
    for d in docs:
        ingest.ingest(d, lambda d=d: d)
    repo = VectorRepository(db, "test-" + identity)
    indexer = VectorIndexer(repo, real_minilm)
    result = indexer.index([d.source_id for d in docs], pipeline.version)
    yield db, real_minilm, repo, indexer, ingest, pipeline, docs, result
    # This entire database is disposable and never shares the development volume.


def test_actual_inference_and_token_limit(real_minilm):
    vectors = real_minilm.encode(["database on AWS", "database on AWS"])
    assert vectors[0] == vectors[1]
    assert abs(sum(v * v for v in vectors[0]) - 1) < 1e-4
    with pytest.raises(VectorFailure, match="embedding_token_limit"):
        real_minilm.encode(["database " * 257])


def test_repeated_indexing_and_online_index(vector_setup):
    db, model, repo, indexer, _, pipeline, docs, result = vector_setup
    before = db.execute("MATCH (e:ChunkEmbedding) RETURN count(e) AS n")
    second = indexer.index([d.source_id for d in docs], pipeline.version)
    assert second["cached"] and second["build_id"] == result["build_id"]
    assert before == db.execute("MATCH (e:ChunkEmbedding) RETURN count(e) AS n")
    assert repo.require_index()["state"] == "ONLINE"


def test_factual_edges_do_not_affect_vector_results(vector_setup):
    db, model, repo, *_ = vector_setup
    service = VectorOnlyService(repo, model)
    question = "Which cloud platform hosts the database used by the project managed by Asha Rao?"
    before = service.retrieve_vector_only(question, 5)
    assert before.answer == "AWS" and len(before.citations) == 3
    # Add deliberately false factual edges, then alter and remove every factual edge
    # in THIS isolated container. Canonical chunks/publication metadata stay identical.
    db.execute(
        "CREATE (a:Person {id:'edge-person'}), (b:Project {id:'edge-project'}), "
        "(a)-[:MANAGES {id:'edge-false'}]->(b)"
    )
    db.execute("MATCH ()-[r:MANAGES|USES|HOSTED_ON|WORKS_FOR|BELONGS_TO]->() SET r.quote='false'")
    altered = service.retrieve_vector_only(question, 5)
    db.execute("MATCH ()-[r:MANAGES|USES|HOSTED_ON|WORKS_FOR|BELONGS_TO]->() DELETE r")
    removed = service.retrieve_vector_only(question, 5)
    assert before.retrieved_chunks == altered.retrieved_chunks == removed.retrieved_chunks
    assert before.answer == altered.answer == removed.answer


def test_no_factual_query_executed(vector_setup):
    db, model, repo, *_ = vector_setup
    observed = []

    class RecordingDatabase:
        settings = db.settings

        def execute(self, query, parameters=None, **kwargs):
            observed.append(query)
            return db.execute(query, parameters, **kwargs)

    service = VectorOnlyService(VectorRepository(RecordingDatabase(), repo.corpus), model)
    assert service.retrieve_vector_only("Which project does Asha Rao manage?", 5).answer == "Boreal"
    assert any("db.index.vector.queryNodes" in q for q in observed)
    assert all(
        not any(
            t in q for t in ("MANAGES", "HOSTED_ON", "WORKS_FOR", "BELONGS_TO", "MENTIONS", "-[:")
        )
        for q in observed
    )


def test_stale_document_hidden_and_missing_link_abstains(vector_setup):
    db, model, repo, indexer, ingest, pipeline, docs, _ = vector_setup
    service = VectorOnlyService(repo, model)
    changed = snapshot(docs[1].source_id, "1.txt", "Project Boreal uses its NewStore instance.")
    # snapshot takes a logical source key. Preserve the original source identity here.
    from app.extraction.models import stable_id, text_hash

    changed = changed.model_copy(
        update={
            "source_id": docs[1].source_id,
            "id": stable_id("autodoc", docs[1].source_id, text_hash(changed.text)),
        }
    )
    ingest.ingest(changed, lambda: changed)
    response = service.retrieve_vector_only(
        "Which cloud platform hosts the database used by the project managed by Asha Rao?", 5
    )
    assert response.abstained
    assert docs[1].id not in {c.document_id for c in response.retrieved_chunks}
    indexer.index([d.source_id for d in docs], pipeline.version)
    assert service.retrieve_vector_only(
        "Which cloud platform hosts the database used by Project Boreal?", 5
    ).abstained


def test_missing_source_chunk_excluded(vector_setup):
    db, model, repo, _, _, _, docs, _ = vector_setup
    # Only delete the owning evidence chunk in the disposable test database.
    db.execute("MATCH (c:Chunk {document_id:$d}) DETACH DELETE c", {"d": docs[1].id})
    response = VectorOnlyService(repo, model).retrieve_vector_only(
        "Which cloud platform hosts the database used by Project Boreal?", 5
    )
    assert response.abstained
    assert docs[1].id not in {c.document_id for c in response.retrieved_chunks}


def test_corrupt_source_is_infrastructure_error(vector_setup):
    db, model, repo, _, _, _, docs, _ = vector_setup
    db.execute("MATCH (d:Document {id:$d}) SET d.text='corrupted'", {"d": docs[0].id})
    with pytest.raises(VectorFailure, match="source_provenance_invalid"):
        VectorOnlyService(repo, model).retrieve_vector_only(
            "Which project does Asha Rao manage?", 5
        )


def test_failed_transaction_never_publishes(vector_setup):
    db, model, repo, _, _, pipeline, docs, _ = vector_setup
    other = VectorRepository(db, repo.corpus + "-fail")
    original = other._put

    def fail_after_write(tx, *args):
        original(tx, *args)
        raise VectorFailure("injected_transaction_failure")

    other._put = fail_after_write
    with pytest.raises(VectorFailure, match="injected_transaction_failure"):
        VectorIndexer(other, model).index([d.source_id for d in docs], pipeline.version)
    with pytest.raises(VectorFailure, match="vector_corpus_unavailable"):
        other.current(model.version)
    state = db.execute(
        "MATCH (c:VectorCorpus {id:$id}), (b:VectorBuild {id:c.desired_build}) "
        "RETURN c.status AS status,b.id AS build,b.error_category AS error",
        {"id": other.corpus},
    )[0]
    assert state["status"] == "failed"
    assert db.execute(
        "MATCH (e:ChunkEmbedding {build_id:$b}) RETURN count(e) AS n", {"b": state["build"]}
    ) == [{"n": 0}]
    other._put = original
    assert (
        VectorIndexer(other, model).index([d.source_id for d in docs], pipeline.version)["status"]
        == "ready"
    )


def test_index_offline_is_explicit_error(vector_setup):
    db, model, repo, *_ = vector_setup
    db.execute("DROP INDEX chunk_minilm_cosine")
    try:
        with pytest.raises(VectorFailure, match="vector_index_unavailable"):
            VectorOnlyService(repo, model).retrieve_vector_only(
                "Which project does Asha Rao manage?", 5
            )
    finally:
        # Recreate the exact trusted migration schema; do not alter checksum history.
        from app.db.migrations import MIGRATIONS

        for statement in (MIGRATIONS / "004_chunk_vectors.cypher").read_text().split(";"):
            if statement.strip():
                db.execute(statement)
        db.execute("CALL db.awaitIndexes(30)")


def test_concurrent_real_requests(vector_setup):
    _, model, repo, *_ = vector_setup
    service = VectorOnlyService(repo, model)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(
            pool.map(
                lambda _: service.retrieve_vector_only("Which project does Asha Rao manage?", 5),
                range(8),
            )
        )
    assert all(r.answer == "Boreal" for r in results)
    assert all(r.retrieved_chunks == results[0].retrieved_chunks for r in results)


@pytest.mark.anyio
async def test_real_vector_api(vector_setup):
    db, model, repo, *_ = vector_setup
    service = VectorOnlyService(repo, model)
    # App owns a separate real driver so closing its lifespan leaves the fixture driver open.
    async with api_client(create_app(db.settings, vector_service=service)) as client:
        responses = await asyncio.gather(
            *[
                client.post(
                    "/api/v1/rag/vector/query",
                    json={"question": "Which project does Asha Rao manage?", "top_k": 5},
                )
                for _ in range(3)
            ]
        )
        assert all(r.status_code == 200 and r.json()["answer"] == "Boreal" for r in responses)
        assert all(r.json()["retrieval_mode"] == "vector_only" for r in responses)


def test_unused_bolt_endpoint_and_recovery(vector_setup):
    db, model, repo, *_ = vector_setup
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        settings = db.settings.model_copy(
            update={"neo4j_uri": f"bolt://127.0.0.1:{sock.getsockname()[1]}"}
        )
        unavailable = GraphDatabaseClient(settings)
        try:
            with pytest.raises(DatabaseUnavailable):
                VectorOnlyService(
                    VectorRepository(unavailable, repo.corpus), model
                ).retrieve_vector_only("Which project does Asha Rao manage?", 5)
        finally:
            unavailable.close()
    assert (
        VectorOnlyService(repo, model)
        .retrieve_vector_only("Which project does Asha Rao manage?", 5)
        .answer
        == "Boreal"
    )


def test_embedding_version_change_rebuilds_without_duplicate_chunks(vector_setup):
    db, model, repo, _, _, pipeline, docs, initial = vector_setup
    from app.extraction.models import stable_id

    class VersionedEncoder:
        version = stable_id("embedding", model.version, "test-new-policy")

        def encode(self, texts):
            return model.encode(texts)

    count = db.execute("MATCH (c:Chunk) RETURN count(c) AS n")
    changed = VersionedEncoder()
    result = VectorIndexer(repo, changed).index([d.source_id for d in docs], pipeline.version)
    assert result["build_id"] != initial["build_id"]
    assert count == db.execute("MATCH (c:Chunk) RETURN count(c) AS n")
    with pytest.raises(VectorFailure, match="vector_corpus_unavailable"):
        VectorOnlyService(repo, model).retrieve_vector_only(
            "Which project does Asha Rao manage?", 5
        )
    assert (
        VectorOnlyService(repo, changed)
        .retrieve_vector_only("Which project does Asha Rao manage?", 5)
        .answer
        == "Boreal"
    )


def test_incomplete_embedding_batches_cannot_publish(vector_setup):
    _, model, repo, _, _, pipeline, docs, _ = vector_setup
    sources = [d.source_id for d in docs]
    records = repo.canonical(sources, pipeline.version)
    other = VectorRepository(repo.db, repo.corpus + "-partial")
    build = "vector-build:" + uuid4().hex
    token = other.begin(build, model.version, sources, pipeline.version, "partial-plan")
    other.put(build, token, records[:1], model.encode([records[0]["text"]]), model.version)
    with pytest.raises(VectorFailure, match="incomplete_indexing"):
        other.publish(build, token, records, sources, pipeline.version)
    with pytest.raises(VectorFailure, match="vector_corpus_unavailable"):
        other.current(model.version)
    other.fail(build, token, "incomplete_indexing")


def test_indexing_claim_excludes_concurrent_and_expired_writer(vector_setup):
    db, model, repo, _, _, pipeline, docs, _ = vector_setup
    sources = [d.source_id for d in docs]
    other = VectorRepository(db, repo.corpus + "-claims")
    build = "vector-build:" + uuid4().hex
    token = other.begin(build, model.version, sources, pipeline.version, "claim-plan")
    with pytest.raises(VectorFailure, match="indexing_busy"):
        other.begin(build, model.version, sources, pipeline.version, "claim-plan")
    db.execute("MATCH (c:VectorCorpus {id:$id}) SET c.lease_until=0", {"id": other.corpus})
    new_token = other.begin(build, model.version, sources, pipeline.version, "claim-plan")
    records = other.canonical(sources, pipeline.version)
    with pytest.raises(VectorFailure, match="indexing_claim_expired"):
        other.put(build, token, records[:1], model.encode([records[0]["text"]]), model.version)
    other.fail(build, new_token, "test_cleanup")


def test_missing_chunk_prevents_reindexing_incomplete_source(vector_setup):
    db, model, repo, indexer, _, pipeline, docs, _ = vector_setup
    db.execute("MATCH (c:Chunk {document_id:$d}) DETACH DELETE c", {"d": docs[0].id})
    with pytest.raises(VectorFailure, match="source_corpus_incomplete"):
        indexer.index([d.source_id for d in docs], pipeline.version)


def test_rebuild_racing_with_query_is_explicit_error(vector_setup):
    _, model, repo, _, _, pipeline, docs, _ = vector_setup

    class RacingRepository(VectorRepository):
        changed = False

        def current(self, version):
            build = super().current(version)
            if not self.changed:
                self.changed = True
                self.begin(
                    "vector-build:" + uuid4().hex,
                    version,
                    [d.source_id for d in docs],
                    pipeline.version,
                    "race-plan",
                )
            return build

    racing = RacingRepository(repo.db, repo.corpus)
    with pytest.raises(VectorFailure, match="vector_corpus_unavailable"):
        VectorOnlyService(racing, model).retrieve_vector_only(
            "Which project does Asha Rao manage?", 5
        )


def test_unavailable_model_is_explicit(real_minilm):
    # Actual cache-only inference with an isolated empty cache must fail, not fabricate.
    env = {
        **os.environ,
        "HF_HOME": os.path.join(os.environ.get("TEMP", "."), "graphrag-empty-" + uuid4().hex),
    }
    result = subprocess.run(
        [os.sys.executable, "-m", "scripts.check_missing_model"],
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=210,
    )
    assert result.returncode == 0, result.stderr
    assert "embedding_model_unavailable" in result.stdout
