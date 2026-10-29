import socket

import pytest

from app.db.migrations import migrate
from app.db.neo4j import DatabaseUnavailable, GraphDatabaseClient
from app.graph.fixtures import graph_rows, read_evaluations, read_fixture
from app.graph.queries import THREE_HOP, TWO_HOP
from app.main import create_app
from app.models.fixtures import Entity, Fixture
from app.repositories.fixture import FixtureConflict, load_fixture, reset_fixture
from app.services.validation import GraphValidationFailure, validate_graph
from tests.client import api_client

pytestmark = pytest.mark.integration


def test_connection_success(real_database):
    real_database.driver.verify_connectivity()
    assert real_database.execute("RETURN 1 AS ok") == [{"ok": 1}]


def test_connection_outage(real_database):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        settings = real_database.settings.model_copy(
            update={"neo4j_uri": f"bolt://127.0.0.1:{port}"}
        )
        db = GraphDatabaseClient(settings)
        try:
            assert db.ready() is False
            with pytest.raises(DatabaseUnavailable):
                db.execute("RETURN 1")
        finally:
            db.close()


def test_migrations_created(loaded_database):
    versions = loaded_database.execute(
        "MATCH (m:SchemaMigration) RETURN m.version AS version ORDER BY version"
    )
    assert versions == [{"version": v} for v in ("001", "002", "003", "004")]
    assert len(loaded_database.execute("SHOW CONSTRAINTS")) >= 18


def test_migrations_idempotent(loaded_database):
    before = loaded_database.execute("SHOW CONSTRAINTS")
    assert migrate(loaded_database) == []
    assert loaded_database.execute("SHOW CONSTRAINTS") == before


def test_fixture_load_and_counts(loaded_database):
    fixture = read_fixture()
    nodes, edges = graph_rows(fixture)
    assert loaded_database.execute(
        "MATCH (n:GraphNode {fixture_id: $id}) RETURN count(n) AS count", {"id": fixture.id}
    ) == [{"count": len(nodes)}]
    assert loaded_database.execute(
        "MATCH ()-[r {fixture_id: $id}]->() RETURN count(r) AS count", {"id": fixture.id}
    ) == [{"count": len(edges)}]


def test_fixture_load_idempotent(loaded_database):
    fixture = read_fixture()
    first = validate_graph(loaded_database, fixture, read_evaluations())
    load_fixture(loaded_database, fixture)
    load_fixture(loaded_database, fixture)
    assert validate_graph(loaded_database, fixture, read_evaluations()) == first


def test_full_graph_and_provenance_validation(loaded_database):
    assert validate_graph(loaded_database, read_fixture(), read_evaluations())["facts"] == 30


def test_evidence_references_resolve(loaded_database):
    rows = loaded_database.execute(
        """
        MATCH ()-[r]->() WHERE r.fixture_id = $id AND r.source_chunk_id IS NOT NULL
        OPTIONAL MATCH (c:Chunk {id: r.source_chunk_id})-[:PART_OF]->
                       (d:Document {id: r.source_document_id})
        RETURN count(r) AS facts, count(c) AS chunks, count(d) AS documents
    """,
        {"id": read_fixture().id},
    )
    assert rows == [{"facts": 30, "chunks": 30, "documents": 30}]


def test_two_hop_path(loaded_database):
    rows = loaded_database.execute(
        TWO_HOP, {"person": "person:priya", "fixture": read_fixture().id}
    )
    assert rows == [
        {
            "nodes": ["person:priya", "project:atlas", "tech:postgres-atlas"],
            "facts": ["fact:001", "fact:003"],
        }
    ]


def test_three_hop_path(loaded_database):
    rows = loaded_database.execute(
        THREE_HOP, {"person": "person:priya", "fixture": read_fixture().id}
    )
    assert rows[0]["answer"] == "AWS"
    assert rows[0]["facts"] == ["fact:001", "fact:003", "fact:005"]


def test_distractor_has_separate_path(loaded_database):
    rows = loaded_database.execute(
        THREE_HOP, {"person": "person:morgan", "fixture": read_fixture().id}
    )
    assert rows[0]["answer"] == "Azure"
    assert rows[0]["nodes"][2] == "tech:postgres-east"


def test_conflicting_fixture_rejected_atomically(loaded_database):
    data = read_fixture().model_dump(mode="json")
    data["entities"][0]["name"] = "Changed entity"
    with pytest.raises(FixtureConflict):
        load_fixture(loaded_database, Fixture.model_validate(data))
    validate_graph(loaded_database, read_fixture(), read_evaluations())


@pytest.mark.parametrize(
    "mutation", ["orphan_evidence", "bad_quote", "missing_edge", "reversed_edge"]
)
def test_validation_detects_tampered_provenance(loaded_database, mutation):
    # Roll back the deliberate corruption; never leave the shared fixture altered.
    original = loaded_database.execute
    with loaded_database.driver.session(
        database=loaded_database.settings.neo4j_database
    ) as session:
        with session.begin_transaction() as tx:
            if mutation == "orphan_evidence":
                query = "MATCH ()-[r:MANAGES {id: $id}]->() SET r.source_chunk_id = 'chunk:absent'"
            elif mutation == "bad_quote":
                query = "MATCH ()-[r:MANAGES {id: $id}]->() SET r.quote = 'Unsupported fact'"
            elif mutation == "missing_edge":
                query = "MATCH ()-[r:MANAGES {id: $id}]->() DELETE r"
            else:
                query = (
                    "MATCH (a)-[r:MANAGES {id: $id}]->(b) WITH a,b,r,properties(r) AS props "
                    "DELETE r CREATE (b)-[reversed:MANAGES]->(a) SET reversed = props"
                )
            tx.run(query, id="fact:001").consume()

            class TransactionView:
                def execute(self, query, parameters=None):
                    return [r.data() for r in tx.run(query, parameters or {})]

            with pytest.raises(GraphValidationFailure):
                validate_graph(TransactionView(), read_fixture(), read_evaluations())
            tx.rollback()
    assert original(
        "MATCH ()-[r:MANAGES {id: $id}]->() RETURN r.source_chunk_id AS chunk", {"id": "fact:001"}
    ) == [{"chunk": "chunk:01"}]


def test_scoped_reset_preserves_unrelated_data_and_refuses_external_edges(loaded_database):
    from uuid import uuid4

    token = uuid4().hex
    fid, nid, other = f"fixture:test-{token}", f"person:test-{token}", f"test:other-{token}"
    fixture = Fixture(
        id=fid,
        entities=[Entity(id=nid, label="Person", name="Reset test", scope=token)],
        documents=[],
        chunks=[],
        facts=[],
    )
    try:
        load_fixture(loaded_database, fixture)
        loaded_database.execute(
            "CREATE (o:ResetTestControl {id: $other}) "
            "WITH o MATCH (n:GraphNode {id: $node}) CREATE (n)-[:TEST_LINK]->(o)",
            {"other": other, "node": nid},
        )
        with pytest.raises(FixtureConflict, match="external edges"):
            reset_fixture(loaded_database, fid, fid)
        assert loaded_database.execute(
            "MATCH (n:GraphNode {id: $id}) RETURN count(n) AS n", {"id": nid}
        ) == [{"n": 1}]
        loaded_database.execute(
            "MATCH (:GraphNode {id: $node})-[r:TEST_LINK]->"
            "(:ResetTestControl {id: $other}) DELETE r",
            {"node": nid, "other": other},
        )
        reset_fixture(loaded_database, fid, fid)
        assert loaded_database.execute(
            "MATCH (n:GraphNode {id: $id}) RETURN count(n) AS n", {"id": nid}
        ) == [{"n": 0}]
        assert loaded_database.execute(
            "MATCH (n:ResetTestControl {id: $id}) RETURN count(n) AS n", {"id": other}
        ) == [{"n": 1}]
    finally:
        # Clean up only records created by this test's unique IDs.
        loaded_database.execute(
            "MATCH (:GraphNode {id: $node})-[r:TEST_LINK]->"
            "(:ResetTestControl {id: $other}) DELETE r",
            {"node": nid, "other": other},
        )
        reset_fixture(loaded_database, fid, fid)
        loaded_database.execute("MATCH (n:ResetTestControl {id: $id}) DELETE n", {"id": other})
        loaded_database.execute("MATCH (n:FixtureLock {id: $id}) DELETE n", {"id": fid})


@pytest.mark.anyio
async def test_api_with_real_database(real_database):
    # The app owns a separate driver and closes it on shutdown.
    async with api_client(create_app(real_database.settings)) as client:
        assert (await client.get("/health")).status_code == 200
        assert (await client.get("/ready")).status_code == 200
