from unittest.mock import Mock

import pytest

from app.db.neo4j import DatabaseUnavailable
from app.main import create_app
from app.vector.models import VectorFailure
from tests.client import api_client

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(
    "body",
    [
        {"question": ""},
        {"question": "q", "top_k": 11},
        {"question": "q", "top_k": True},
        {"question": "q", "cypher": "MATCH (n) RETURN n"},
    ],
)
async def test_vector_invalid_input(settings, body):
    service = Mock()
    async with api_client(create_app(settings, Mock(), service)) as client:
        r = await client.post("/api/v1/rag/vector/query", json=body)
        assert r.status_code == 422
    service.retrieve_vector_only.assert_not_called()


@pytest.mark.parametrize(
    "error",
    [
        "embedding_model_unavailable",
        "vector_index_unavailable",
        "vector_corpus_unavailable",
        "embedding_timeout",
        "source_provenance_invalid",
        "database",
    ],
)
async def test_vector_infrastructure_errors_are_not_abstentions(settings, error):
    service = Mock()
    service.retrieve_vector_only.side_effect = (
        DatabaseUnavailable("private") if error == "database" else VectorFailure(error)
    )
    async with api_client(create_app(settings, Mock(), service)) as client:
        r = await client.post(
            "/api/v1/rag/vector/query", json={"question": "Which project does Asha manage?"}
        )
        assert r.status_code == 503
        assert "answer" not in r.json() and "private" not in r.text
