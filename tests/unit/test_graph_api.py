from unittest.mock import Mock

import pytest

from app.db.neo4j import DatabaseUnavailable
from app.graph_rag.models import GraphFailure
from app.main import create_app
from tests.client import api_client

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(
    "body",
    [
        {"question": ""},
        {"question": "x" * 1001},
        {"question": "q", "max_hops": 4},
        {"question": "q", "max_hops": True},
        {"question": "q", "cypher": "MATCH (n) RETURN n"},
    ],
)
async def test_graph_api_rejects_invalid_input(settings, body):
    service = Mock()
    async with api_client(create_app(settings, Mock(), graph_service=service)) as client:
        response = await client.post("/api/v1/rag/graph/query", json=body)
        assert response.status_code == 422 and "answer" not in response.json()
    service.query.assert_not_called()


@pytest.mark.parametrize(
    "category,status",
    [
        ("graph_request_timeout", 504),
        ("graph_query_timeout", 504),
        ("graph_snapshot_changed", 503),
        ("database", 503),
    ],
)
async def test_graph_api_infrastructure_is_not_an_abstention(settings, category, status):
    service = Mock()
    service.query.side_effect = (
        DatabaseUnavailable("private") if category == "database" else GraphFailure(category)
    )
    async with api_client(create_app(settings, Mock(), graph_service=service)) as client:
        response = await client.post(
            "/api/v1/rag/graph/query", json={"question": "Which project does Morgan manage?"}
        )
    assert response.status_code == status and "answer" not in response.json()
    assert "private" not in response.text
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
