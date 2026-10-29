from collections.abc import Mapping
from typing import Any

from neo4j import GraphDatabase, Query
from neo4j.exceptions import DriverError, Neo4jError

from app.core.config import Settings


class DatabaseUnavailable(Exception):
    """Safe boundary between driver failures and application responses."""


class GraphDatabaseClient:
    def __init__(self, settings: Settings, *, write_retry_time: float = 0):
        self.settings = settings
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
            connection_timeout=settings.neo4j_connection_timeout,
            connection_acquisition_timeout=settings.neo4j_connection_timeout,
            max_connection_pool_size=settings.neo4j_pool_size,
            max_transaction_retry_time=write_retry_time,
            liveness_check_timeout=0,
        )

    def execute(
        self,
        cypher: str,
        parameters: Mapping[str, Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> list[dict]:
        """Internal trusted queries only. Values must be passed as parameters."""
        try:
            with self.driver.session(database=self.settings.neo4j_database) as session:
                result = session.run(
                    Query(cypher, timeout=timeout or self.settings.neo4j_query_timeout),
                    parameters=dict(parameters or {}),
                )
                return [record.data() for record in result]
        except (DriverError, Neo4jError, OSError) as exc:
            raise DatabaseUnavailable("Graph database operation failed") from exc

    def ready(self) -> bool:
        try:
            return self.execute("RETURN 1 AS ok") == [{"ok": 1}]
        except DatabaseUnavailable:
            return False

    def close(self) -> None:
        self.driver.close()
