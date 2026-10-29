import pytest

from app.core.config import Settings
from app.db.migrations import migrate
from app.db.neo4j import GraphDatabaseClient
from app.graph.fixtures import read_fixture
from app.repositories.fixture import load_fixture


@pytest.fixture(scope="session")
def real_database():
    db = GraphDatabaseClient(Settings())
    try:
        assert db.ready(), "Neo4j is required; start Docker Compose (no silent integration skips)"
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session")
def loaded_database(real_database):
    migrate(real_database)
    load_fixture(real_database, read_fixture())
    return real_database
