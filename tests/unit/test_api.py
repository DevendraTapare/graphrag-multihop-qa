import logging
from unittest.mock import Mock

import pytest
from fastapi import Query

from app.db.neo4j import DatabaseUnavailable
from app.main import create_app
from tests.client import api_client

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("available", [True, False])
async def test_liveness_readiness_and_cleanup(settings, available):
    database = Mock()
    database.ready.return_value = available
    async with api_client(create_app(settings, database)) as client:
        for prefix in ("", "/api/v1"):
            assert (await client.get(prefix + "/health")).json() == {"status": "alive"}
            response = await client.get(prefix + "/ready")
            assert response.status_code == (200 if available else 503)
            assert settings.neo4j_password.get_secret_value() not in response.text
    database.close.assert_called_once()


@pytest.mark.parametrize("incoming", ["valid-id_123", "bad id", "a" * 100, ""])
async def test_request_ids(settings, incoming):
    async with api_client(create_app(settings, Mock())) as client:
        response = await client.get("/health", headers={"X-Request-ID": incoming})
    actual = response.headers["X-Request-ID"]
    assert actual == incoming if incoming == "valid-id_123" else len(actual) == 32


@pytest.mark.parametrize(
    "exception,status",
    [(DatabaseUnavailable("password=hidden"), 503), (RuntimeError("secret internals"), 500)],
)
async def test_safe_errors(settings, exception, status):
    app = create_app(settings, Mock())

    @app.get("/test-error")
    def fail():
        raise exception

    async with api_client(app) as client:
        response = await client.get("/test-error")
    assert response.status_code == status
    assert "hidden" not in response.text
    assert "secret internals" not in response.text
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


async def test_validation_errors_hide_input(settings):
    app = create_app(settings, Mock())

    @app.get("/test-input")
    def input_endpoint(number: int = Query()):
        return number

    async with api_client(app) as client:
        response = await client.get("/test-input?number=private-value")
    assert response.status_code == 422
    assert "private-value" not in response.text


def test_no_query_api(settings):
    app = create_app(settings, Mock())
    paths = app.openapi()["paths"]
    assert set(paths) == {
        "/health",
        "/ready",
        "/api/v1/health",
        "/api/v1/ready",
        "/api/v1/rag/vector/query",
        "/api/v1/rag/graph/query",
        "/api/v1/rag/hybrid/query",
        "/api/v1/rag/aligned/graph/query",
        "/api/v1/rag/aligned/vector/query",
        "/api/v1/rag/aligned/ready",
    }
    assert "cypher" not in str(paths["/api/v1/rag/vector/query"])


def test_redaction(settings):
    import json

    from app.core.logging import JsonFormatter, configure_logging, request_id

    secret = settings.neo4j_password.get_secret_value()
    configure_logging(secret)
    token = request_id.set("test-rid")
    try:
        record = logging.LogRecord(
            "test",
            logging.ERROR,
            "",
            1,
            f"{secret} password=other bolt://user:pass@host token=abc",
            (),
            None,
        )
        result = JsonFormatter().format(record)
        data = json.loads(result)
        assert data["request_id"] == "test-rid"
        for sensitive in (secret, "other", "user:pass", "abc"):
            assert sensitive not in result
    finally:
        request_id.reset(token)
