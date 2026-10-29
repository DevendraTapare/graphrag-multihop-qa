import pytest

from app.core.config import Settings


@pytest.fixture
def anyio_backend():
    return "asyncio"


def pytest_addoption(parser):
    parser.addoption("--run-integration", action="store_true", help="Require a real Neo4j database")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-integration"):
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(
                    pytest.mark.skip(reason="Use --run-integration for real Neo4j tests")
                )


@pytest.fixture
def settings():
    return Settings(_env_file=None, neo4j_password="unit-test-secret-12345")
