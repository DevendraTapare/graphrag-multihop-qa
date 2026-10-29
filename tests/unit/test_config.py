import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_environment_config(monkeypatch):
    monkeypatch.setenv("NEO4J_PASSWORD", "environment-secret-123")
    monkeypatch.setenv("NEO4J_DATABASE", "test-graph")
    monkeypatch.setenv("NEO4J_POOL_SIZE", "7")
    settings = Settings(_env_file=None)
    assert settings.neo4j_database == "test-graph"
    assert settings.neo4j_pool_size == 7
    assert "environment-secret-123" not in repr(settings)


@pytest.mark.parametrize(
    "password",
    [
        "short",
        "replace-with-local-random-secret",
        "spaces are invalid",
        "abcdefghijkl/",
        "abcdefghijkl$",
    ],
)
def test_password_validation(password):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, neo4j_password=password)


@pytest.mark.parametrize(
    "uri",
    ["https://localhost", "bolt://user:secret@localhost", "bolt://", "bolt://localhost?token=123"],
)
def test_uri_validation(uri):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, neo4j_uri=uri, neo4j_password="unit-secret-123456")


@pytest.mark.parametrize(
    "field,value", [("neo4j_pool_size", 0), ("neo4j_query_timeout", -1), ("api_port", 70000)]
)
def test_bounds(field, value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, neo4j_password="unit-secret-123456", **{field: value})
