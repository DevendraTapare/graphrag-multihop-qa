from unittest.mock import Mock, patch

import pytest
from neo4j import Query
from neo4j.exceptions import ServiceUnavailable

from app.db.neo4j import DatabaseUnavailable, GraphDatabaseClient


def test_parameterized_query_and_pool_settings(settings):
    with patch("app.db.neo4j.GraphDatabase.driver") as factory:
        client = GraphDatabaseClient(settings)
        record = Mock()
        record.data.return_value = {"name": "value"}
        session = factory.return_value.session.return_value.__enter__.return_value
        session.run.return_value = [record]
        attack = "x' MATCH (n) DETACH DELETE n //"
        assert client.execute("RETURN $name AS name", {"name": attack}) == [{"name": "value"}]
        query = session.run.call_args.args[0]
        assert isinstance(query, Query)
        assert query.text == "RETURN $name AS name"
        assert attack not in query.text
        assert session.run.call_args.kwargs["parameters"] == {"name": attack}
        assert query.timeout == settings.neo4j_query_timeout
        assert factory.call_args.kwargs["max_connection_pool_size"] == settings.neo4j_pool_size
        client.close()
        factory.return_value.close.assert_called_once()


def test_safe_driver_error_and_readiness(settings):
    with patch("app.db.neo4j.GraphDatabase.driver") as factory:
        client = GraphDatabaseClient(settings)
        factory.return_value.session.side_effect = ServiceUnavailable("credentials=private")
        with pytest.raises(DatabaseUnavailable, match="Graph database operation failed") as caught:
            client.execute("RETURN 1")
        assert "private" not in str(caught.value)
        assert client.ready() is False


def test_driver_closes_session(settings):
    with patch("app.db.neo4j.GraphDatabase.driver") as factory:
        client = GraphDatabaseClient(settings)
        factory.return_value.session.return_value.__enter__.return_value.run.return_value = []
        client.execute("RETURN 1")
        factory.return_value.session.return_value.__exit__.assert_called_once()
