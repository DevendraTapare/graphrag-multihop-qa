"""All graph mutations occur in a fresh disposable Community container."""

import asyncio
import concurrent.futures
import json
import socket
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.db.migrations import MIGRATIONS
from app.db.neo4j import DatabaseUnavailable, GraphDatabaseClient
from app.extraction.documents import snapshot
from app.extraction.pipeline import ExtractionPipeline
from app.extraction.registry import EntityRegistry
from app.graph.fixtures import ROOT, read_fixture
from app.graph_rag.models import GraphFailure
from app.graph_rag.repository import GraphPolicy, GraphRepository
from app.graph_rag.service import GraphOnlyService
from app.main import create_app
from app.repositories.fixture import load_fixture
from app.repositories.ingestion import IngestionRepository
from app.services.ingestion import IngestionService
from tests.client import api_client
from tests.integration.test_vector import isolated_vector_database as isolated_vector_database

pytestmark = pytest.mark.integration
HERO = (
    "Which cloud platform hosts the database used by the project managed by "
    "Priya (Lumen employee 001)?"
)


@pytest.fixture
def graph_case(graph_database):
    db = graph_database
    # Refuse whole-database test cleanup against the development endpoint.
    assert db.settings.neo4j_uri != Settings().neo4j_uri
    assert db.settings.neo4j_uri.startswith("bolt://127.0.0.1:")
    db.execute("MATCH (n) WHERE NOT n:SchemaMigration DETACH DELETE n")
    load_fixture(db, read_fixture())
    pipeline = ExtractionPipeline()
    ingest = IngestionService(IngestionRepository(db, pipeline))
    sources, keys = set(), {}

    def add(text, key=None):
        key = key or "graph-test:" + uuid4().hex
        doc = snapshot(key, "graph-test.txt", text)
        ingest.ingest(doc, lambda: doc)
        sources.add(doc.source_id)
        keys[doc.source_id] = key
        return doc

    docs = [
        add(t)
        for t in (
            "Priya (Lumen employee 001) manages Project Atlas.",
            "Project Atlas uses its PostgreSQL instance.",
            "The PostgreSQL instance for Project Atlas is hosted on AWS.",
        )
    ]

    def service(curated=False, max_candidates=128, max_answers=10, repository_type=GraphRepository):
        policy = GraphPolicy(
            tuple(sorted(sources)), pipeline.version, read_fixture().id if curated else None
        )
        return GraphOnlyService(
            repository_type(db, policy, max_candidates), pipeline, max_answers=max_answers
        )

    return SimpleNamespace(
        db=db,
        pipeline=pipeline,
        docs=docs,
        add=add,
        service=service,
        keys=keys,
        sources=sources,
        ingest=ingest,
    )


@pytest.fixture(scope="module")
def graph_database(isolated_vector_database):
    # The shared disposable-container fixture uses a one-second probe timeout.
    # Use the project's normal connection bound for the sustained graph workload.
    settings = isolated_vector_database.settings.model_copy(update={"neo4j_connection_timeout": 3})
    db = GraphDatabaseClient(settings, write_retry_time=3)
    try:
        yield db
    finally:
        db.close()


def test_actual_one_two_three_hop_paths(graph_case):
    c = graph_case
    service = c.service()
    for q, answer, hops in (
        ("Which project does Priya (Lumen employee 001) manage?", "Atlas", 1),
        (
            "Which database does the project managed by Priya (Lumen employee 001) use?",
            "PostgreSQL",
            2,
        ),
        (HERO, "AWS", 3),
    ):
        r = service.query(q)
        assert r.answer == answer and not r.abstained and r.hop_count == hops
        assert len(r.reasoning_path) == hops and len(r.citations) == hops
        assert all(s.supports for s in r.reasoning_path)
        assert r.paths_discarded == 0


def test_curated_and_automatic_supports_stay_distinct(graph_case):
    r = graph_case.service(curated=True).query(HERO)
    assert r.answer == "AWS" and len(r.reasoning_paths) == 1
    assert {c.source_kind for c in r.citations} == {"curated", "automatic"}
    assert len(r.citations) == 6


def test_all_citations_resolve_exact_original_text(graph_case):
    c = graph_case
    r = c.service(curated=True).query(HERO)
    for cite in r.citations:
        doc = c.db.execute(
            "MATCH (d:Document {id:$id}) RETURN d.text AS text", {"id": cite.document_id}
        )[0]
        chunk = c.db.execute(
            "MATCH (c:Chunk {id:$id}) RETURN properties(c) AS c", {"id": cite.chunk_id}
        )[0]["c"]
        assert doc["text"][cite.start : cite.end] == cite.quote
        assert chunk["start"] <= cite.start < cite.end <= chunk["end"]


def test_duplicate_first_names_abstain(graph_case):
    r = graph_case.service(curated=True).query("Which project does Priya manage?")
    assert r.reason == "entity_ambiguous" and r.abstained and not r.reasoning_paths
    assert set(r.resolution.candidate_ids) == {"person:priya", "person:priya-cedar"}


def test_similar_projects_and_deployments_are_distinct(graph_case):
    service = graph_case.service(curated=True)
    a = service.query("Which cloud platform hosts the database used by Project Atlas?")
    b = service.query("Which cloud platform hosts the database used by Project Atlas East?")
    assert (a.answer, b.answer) == ("AWS", "Azure")
    assert a.reasoning_paths[0].nodes[1].id != b.reasoning_paths[0].nodes[1].id
    unknown = service.query("Which database does Project Atlas North use?")
    assert unknown.reason == "entity_not_found"


def test_explicit_context_and_reverse_direction(graph_case):
    c = graph_case
    c.add("Priya (Lumen employee 001) works for Lumen Orchard.")
    r = c.service().query("Which organization employs the manager of Project Atlas?")
    assert r.answer == "Lumen Orchard" and r.hop_count == 2
    assert r.reasoning_path[0].direction == "incoming"
    assert r.reasoning_path[0].stored_source_id == "person:priya"
    assert r.reasoning_path[0].source.id == "project:atlas"


def test_shared_project_alias_is_ambiguous(graph_case, tmp_path):
    data = json.loads((ROOT / "data/extraction/entity_registry.json").read_text())
    for entry in data["entries"]:
        if entry["entity"]["id"] in {"project:atlas", "project:atlas-east"}:
            entry["aliases"].append("Shared Project")
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(data))
    pipeline = ExtractionPipeline(registry=EntityRegistry(path))
    policy = GraphPolicy((), pipeline.version, read_fixture().id)
    r = GraphOnlyService(GraphRepository(graph_case.db, policy), pipeline).query(
        "Which database does Project Shared Project use?"
    )
    assert r.reason == "entity_ambiguous" and len(r.resolution.candidate_ids) == 2


def test_incorrect_stored_direction_cannot_answer(graph_case):
    c = graph_case
    rows = c.db.execute(
        "MATCH (a)-[r:USES]->(b) WHERE r.source_id=$s "
        "RETURN a.id AS a,b.id AS b,properties(r) AS p",
        {"s": c.docs[1].source_id},
    )
    row = rows[0]
    c.db.execute("MATCH ()-[r:USES {id:$id}]->() DELETE r", {"id": row["p"]["id"]})
    c.db.execute(
        "MATCH (a:GraphNode {id:$a}),(b:GraphNode {id:$b}) CREATE (b)-[r:USES]->(a) SET r=$p", row
    )
    r = c.service().query(HERO)
    assert r.abstained and r.reason == "missing_intermediate_evidence"


def test_wrong_instance_endpoint_cannot_reuse_quote(graph_case):
    c = graph_case
    props = c.db.execute(
        "MATCH ()-[r:USES]->() WHERE r.source_id=$s RETURN properties(r) AS p",
        {"s": c.docs[1].source_id},
    )[0]["p"]
    c.db.execute("MATCH ()-[r:USES {id:$id}]->() DELETE r", {"id": props["id"]})
    c.db.execute(
        "MATCH (a:Project {id:'project:atlas'}),(b:Technology {id:'tech:postgres-east'}) "
        "CREATE (a)-[r:USES]->(b) SET r=$p",
        {"p": props},
    )
    r = c.service().query(HERO)
    assert r.abstained and r.paths_discarded > 0
    assert r.diagnostics["automatic_fact_proof_invalid"] > 0


def test_unrelated_nearby_nodes_do_not_change_paths(graph_case):
    c = graph_case
    before = c.service().query(HERO)
    c.db.execute(
        "MATCH (p:Project {id:'project:atlas'}) "
        "CREATE (n:GraphNode:Person {id:'person:noise',name:'Priya Shadow'})-[:MANAGES]->(p)"
    )
    after = c.service().query(HERO)
    assert before.reasoning_paths == after.reasoning_paths and after.answer == "AWS"


def test_cycles_do_not_expand_traversal(graph_case):
    c = graph_case
    c.db.execute(
        "MATCH (t:Technology {id:'tech:postgres-atlas'}),(p:Project {id:'project:atlas'}) "
        "CREATE (t)-[:USES {id:'cycle:bad'}]->(p)"
    )
    r = c.service().query(HERO)
    assert r.answer == "AWS" and r.candidate_path_count == 3
    assert len({n.id for n in r.reasoning_paths[0].nodes}) == 4


def test_unsupported_direct_shortcut_is_not_reasoning(graph_case):
    c = graph_case
    c.db.execute("MATCH ()-[r:USES]->() WHERE r.source_id=$s DELETE r", {"s": c.docs[1].source_id})
    c.db.execute(
        "MATCH (p:Person {id:'person:priya'}),(a:Platform {id:'platform:aws'}) "
        "CREATE (p)-[:HOSTED_ON {id:'shortcut:bad',provenance_status:'verified_rule'}]->(a)"
    )
    r = c.service().query(HERO)
    assert r.abstained and not r.reasoning_paths


def add_east_branch(c, cloud="Azure"):
    c.add("Priya (Lumen employee 001) manages Project Atlas East.")
    c.add("Project Atlas East uses its own PostgreSQL instance.")
    c.add(f"The PostgreSQL instance for Project Atlas East is hosted on {cloud}.")


def test_multiple_paths_with_different_answers_abstain(graph_case):
    c = graph_case
    add_east_branch(c)
    r = c.service().query(HERO)
    assert r.reason == "conflicting_answers" and r.abstained and len(r.reasoning_paths) == 2
    assert {p.nodes[-1].name for p in r.reasoning_paths} == {"AWS", "Azure"}


def test_plural_question_returns_all_supported_answers(graph_case):
    c = graph_case
    add_east_branch(c)
    q = (
        "Which cloud platforms host the databases used by the projects managed by "
        "Priya (Lumen employee 001)?"
    )
    r = c.service().query(q)
    assert r.answer == "AWS; Azure" and len(r.reasoning_paths) == 2 and len(r.citations) == 6
    bounded = c.service(max_answers=1).query(q)
    assert bounded.reason == "answer_limit_exceeded" and bounded.abstained


def test_distinct_intermediates_with_same_answer_keep_both_chains(graph_case):
    c = graph_case
    add_east_branch(c, "AWS")
    r = c.service().query(HERO)
    assert r.answer == "AWS" and len(r.reasoning_paths) == 2
    assert len({p.nodes[2].id for p in r.reasoning_paths}) == 2


def test_complete_path_cannot_hide_incomplete_branch(graph_case):
    c = graph_case
    c.add("Priya (Lumen employee 001) manages Project Atlas East.")
    r = c.service().query(HERO)
    assert r.abstained and r.reason == "missing_intermediate_evidence"
    assert len(r.reasoning_paths) == 1  # Complete alternative is diagnostic, not an answer.


def test_independent_support_survives_one_failed_source(graph_case):
    c = graph_case
    other = c.add(c.docs[0].text)
    before = c.service().query(HERO)
    assert len(before.reasoning_path[0].supports) == 2
    c.db.execute(
        "MATCH (s:IngestionSource {id:$id}) SET s.status='failed',s.current_run_id=null",
        {"id": c.docs[0].source_id},
    )
    after = c.service().query(HERO)
    assert after.answer == "AWS" and len(after.reasoning_path[0].supports) == 1
    assert after.reasoning_path[0].supports[0].source_id == other.source_id


@pytest.mark.parametrize(
    "mutation",
    [
        "chunk_missing",
        "orphaned",
        "document_deleted",
        "quote_changed",
        "document_corrupt",
        "run_failed",
        "source_processing",
        "stale_version",
        "incomplete_publication",
    ],
)
def test_invalid_source_or_provenance_never_answers(graph_case, mutation):
    c = graph_case
    d = c.docs[2]
    if mutation == "chunk_missing":
        c.db.execute("MATCH (n:Chunk {document_id:$d}) DETACH DELETE n", {"d": d.id})
    elif mutation == "orphaned":
        c.db.execute(
            "MATCH (:Chunk {document_id:$d})-[r:PART_OF|DERIVED_FROM]->() DELETE r", {"d": d.id}
        )
    elif mutation == "document_deleted":
        c.db.execute("MATCH (n:Document {id:$d}) DETACH DELETE n", {"d": d.id})
    elif mutation == "quote_changed":
        c.db.execute(
            "MATCH ()-[r:HOSTED_ON]->() WHERE r.source_id=$s SET r.quote='unsupported text'",
            {"s": d.source_id},
        )
    elif mutation == "document_corrupt":
        c.db.execute("MATCH (n:Document {id:$d}) SET n.text='corrupted'", {"d": d.id})
    elif mutation == "run_failed":
        c.db.execute(
            "MATCH (s:IngestionSource {id:$s}),(i:Ingestion {id:s.current_run_id}) "
            "SET i.status='failed'",
            {"s": d.source_id},
        )
    elif mutation == "source_processing":
        c.db.execute(
            "MATCH (s:IngestionSource {id:$s}) SET s.status='processing'", {"s": d.source_id}
        )
    elif mutation == "stale_version":
        c.db.execute(
            "MATCH (s:IngestionSource {id:$s}) SET s.processing_version='processing:stale'",
            {"s": d.source_id},
        )
    else:
        c.db.execute(
            "MATCH (s:IngestionSource {id:$s}),(i:Ingestion {id:s.current_run_id}) "
            "SET i.expected_chunk_count=100",
            {"s": d.source_id},
        )
    r = c.service().query(HERO)
    assert r.abstained and r.answer is None and not r.answers
    assert not r.citations and not r.reasoning_path


def test_corrected_source_excludes_old_relationship(graph_case):
    c = graph_case
    old = c.docs[2]
    updated = c.add(
        "The PostgreSQL instance for Project Atlas is hosted on Azure.", c.keys[old.source_id]
    )
    r = c.service().query(HERO)
    assert r.answer == "Azure"
    assert old.id not in {x.document_id for x in r.citations}
    assert updated.id in {x.document_id for x in r.citations}


def test_candidate_overflow_abstains_without_first_path_choice(graph_case):
    r = graph_case.service(max_candidates=1).query(HERO)
    assert r.abstained and r.reason == "candidate_limit_exceeded" and r.candidate_path_count == 2


def test_graph_does_not_need_vector_index_or_model(graph_case):
    c = graph_case
    c.db.execute("DROP INDEX chunk_minilm_cosine")
    try:
        assert c.service().query(HERO).answer == "AWS"
    finally:
        for statement in (MIGRATIONS / "004_chunk_vectors.cypher").read_text().split(";"):
            if statement.strip():
                c.db.execute(statement)
        c.db.execute("CALL db.awaitIndexes(30)")


def test_actual_queries_are_bounded_and_have_no_vector_search(graph_case):
    c = graph_case
    observed = []

    class Recorded:
        def execute(self, query, parameters=None, **kwargs):
            observed.append((query, parameters, kwargs))
            return c.db.execute(query, parameters, **kwargs)

    base = c.service()
    repo = GraphRepository(Recorded(), base.repo.policy)
    assert GraphOnlyService(repo, c.pipeline).query(HERO).answer == "AWS"
    assert all("db.index.vector" not in q and "ChunkEmbedding" not in q for q, _, _ in observed)
    reasoning = [(q, p) for q, p, _ in observed if "MATCH p=" in q]
    assert reasoning and all("LIMIT $limit" in q and p["limit"] <= 129 for q, p in reasoning)
    assert all("PART_OF" not in q and "MENTIONS" not in q and "*" not in q for q, _ in reasoning)
    assert all(0 < opts["timeout"] <= 10 for _, _, opts in observed)


def test_concurrent_source_change_returns_explicit_error(graph_case):
    c = graph_case

    class Racing(GraphRepository):
        def recheck(self, *args):
            c.db.execute(
                "MATCH (s:IngestionSource {id:$s}) SET s.status='failed'",
                {"s": c.docs[2].source_id},
            )
            return super().recheck(*args)

    with pytest.raises(GraphFailure, match="graph_snapshot_changed"):
        c.service(repository_type=Racing).query(HERO)


def test_request_deadline_does_not_return_an_answer(graph_case):
    service = graph_case.service()
    service.request_timeout = 1e-9
    with pytest.raises(GraphFailure, match="graph_request_timeout"):
        service.query(HERO)


def test_neo4j_unavailable_then_real_recovery(graph_case):
    c = graph_case
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        settings = c.db.settings.model_copy(
            update={"neo4j_uri": f"bolt://127.0.0.1:{sock.getsockname()[1]}"}
        )
        unavailable = GraphDatabaseClient(settings)
        try:
            normal = c.service()
            service = GraphOnlyService(GraphRepository(unavailable, normal.repo.policy), c.pipeline)
            with pytest.raises(DatabaseUnavailable):
                service.query(HERO)
        finally:
            unavailable.close()
    assert c.service().query(HERO).answer == "AWS"


def test_concurrent_real_queries_are_consistent(graph_case):
    service = graph_case.service()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: service.query(HERO), range(8)))
    assert all(
        r.answer == "AWS" and r.reasoning_paths == results[0].reasoning_paths for r in results
    )
    assert len({r.request_id for r in results}) == 8


@pytest.mark.anyio
async def test_real_graph_api_and_request_ids(graph_case):
    c = graph_case
    async with api_client(create_app(c.db.settings, graph_service=c.service())) as client:
        results = await asyncio.gather(
            *[
                client.post("/api/v1/rag/graph/query", json={"question": HERO, "max_hops": 3})
                for _ in range(3)
            ]
        )
        assert all(r.status_code == 200 and r.json()["answer"] == "AWS" for r in results)
        assert all(r.json()["request_id"] == r.headers["X-Request-ID"] for r in results)
        bad = await client.post("/api/v1/rag/graph/query", json={"question": HERO, "max_hops": 4})
        assert bad.status_code == 422


def test_forged_curated_assertion_cannot_create_conflict(graph_case):
    c = graph_case
    props = c.db.execute("MATCH ()-[r:HOSTED_ON {id:'fact:005'}]->() RETURN properties(r) AS p")[0][
        "p"
    ]
    props["id"] = "fact:forged"
    c.db.execute(
        "MATCH (a:Technology {id:'tech:postgres-atlas'}),"
        "(b:Platform {id:'platform:azure'}) CREATE (a)-[r:HOSTED_ON]->(b) SET r=$p",
        {"p": props},
    )
    r = c.service(curated=True).query(HERO)
    assert r.answer == "AWS" and r.paths_discarded > 0
    assert "fact:forged" not in {x.fact_id for x in r.citations}


def test_corrupted_curated_fact_retains_valid_automatic_support(graph_case):
    c = graph_case
    c.db.execute("MATCH ()-[r:HOSTED_ON {id:'fact:005'}]->() SET r.quote='unsupported'")
    r = c.service(curated=True).query(HERO)
    assert r.answer == "AWS" and r.paths_discarded > 0
    assert "fact:005" not in {x.fact_id for x in r.citations}


def test_high_confidence_unapproved_method_is_excluded(graph_case):
    c = graph_case
    c.db.execute(
        "MATCH ()-[r:HOSTED_ON]->() WHERE r.source_id=$s "
        "SET r.extraction_method='unverified_inference',r.rule_score=1.0",
        {"s": c.docs[2].source_id},
    )
    assert c.service().query(HERO).abstained


def test_structural_links_cannot_replace_missing_facts(graph_case):
    c = graph_case
    c.db.execute(
        "MATCH ()-[r:MANAGES]->() WHERE r.source_id=$s DELETE r", {"s": c.docs[0].source_id}
    )
    c.db.execute(
        "MATCH (a:Person {id:'person:priya'}),(b:Project {id:'project:atlas'}) "
        "CREATE (a)-[:MENTIONS]->(b), (a)-[:PART_OF]->(b)"
    )
    r = c.service().query(HERO)
    assert r.abstained and not r.reasoning_paths


@pytest.mark.parametrize(
    "question,answer",
    [
        ("Which project does Morgan manage?", "Atlas East"),
        ("Which organization employs Morgan?", "Cedar Kite"),
        ("Which database does Project Comet use?", "Neo4j"),
        ("Which organization owns Project Delta?", "Tidal Lantern"),
        ("On which platform is the Postgres instance for Project Atlas East hosted?", "Azure"),
    ],
)
def test_all_factual_relationship_types_have_validated_paths(graph_case, question, answer):
    r = graph_case.service(curated=True).query(question)
    assert r.answer == answer and r.hop_count == 1 and r.citations
