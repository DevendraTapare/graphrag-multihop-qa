from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.db.neo4j import DatabaseUnavailable
from app.graph_rag.models import GraphFailure
from app.main import create_app
from tests.client import api_client

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(
    "payload",
    [
        {"question": " "},
        {"question": "a" * 1001},
        {"question": 3},
        {"question": "hello", "top_k": 0},
        {"question": "hello", "top_k": 11},
        {"question": "hello", "top_k": True},
        {"question": "hello", "max_hops": 4},
        {"question": "hello", "max_hops": 0},
        {"question": "hello", "max_hops": 1.5},
        {"question": "hello", "cypher": "MATCH (n) DELETE n"},
    ],
)
async def test_hybrid_input_rejected_before_service(settings, payload):
    aligned = SimpleNamespace(hybrid=Mock(), close=Mock())
    async with api_client(create_app(settings, Mock(), aligned=aligned)) as client:
        response = await client.post("/api/v1/rag/hybrid/query", json=payload)
    assert response.status_code == 422 and response.headers["X-Request-ID"]
    aligned.hybrid.query.assert_not_called()


@pytest.mark.parametrize(
    "error,status",
    [
        (DatabaseUnavailable("private token"), 503),
        (GraphFailure("graph_request_timeout"), 504),
        (RuntimeError("private token"), 500),
    ],
)
async def test_hybrid_errors_are_safe(settings, error, status):
    service = Mock()
    service.query.side_effect = error
    aligned = SimpleNamespace(hybrid=service, close=Mock())
    async with api_client(create_app(settings, Mock(), aligned=aligned)) as client:
        response = await client.post(
            "/api/v1/rag/hybrid/query", json={"question": "Which project does Lina Shaw manage?"}
        )
    assert response.status_code == status
    assert "private" not in response.text and "answer" not in response.json()
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
