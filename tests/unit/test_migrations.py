from unittest.mock import Mock

import pytest

from app.db.migrations import MigrationFailure, migrate
from app.db.neo4j import DatabaseUnavailable


def test_migration_order_and_parameterized_tracking(tmp_path):
    (tmp_path / "002_second.cypher").write_text("RETURN 2;")
    (tmp_path / "001_first.cypher").write_text("RETURN 1;")
    database = Mock()
    database.execute.return_value = []
    assert migrate(database, tmp_path) == ["001_first.cypher", "002_second.cypher"]
    queries = [c.args[0] for c in database.execute.call_args_list]
    assert queries.index("RETURN 1") < queries.index("RETURN 2")
    tracked = [c for c in database.execute.call_args_list if c.args[0].startswith("MERGE")]
    assert tracked[0].args[1]["version"] == "001"


def test_migration_failure_is_reported_without_credentials(tmp_path):
    (tmp_path / "001_bad.cypher").write_text("BAD QUERY;")
    database = Mock()
    database.execute.side_effect = [[], [], DatabaseUnavailable("private")]
    with pytest.raises(MigrationFailure, match="001_bad.cypher") as error:
        migrate(database, tmp_path)
    assert "private" not in str(error.value)


def test_checksum_drift_fails(tmp_path):
    (tmp_path / "001_first.cypher").write_text("RETURN 1;")
    database = Mock()
    database.execute.side_effect = [[], [{"version": "001", "checksum": "incorrect"}]]
    with pytest.raises(MigrationFailure, match="changed"):
        migrate(database, tmp_path)


def test_duplicate_versions_fail(tmp_path):
    (tmp_path / "001_a.cypher").write_text("RETURN 1;")
    (tmp_path / "001_b.cypher").write_text("RETURN 2;")
    with pytest.raises(MigrationFailure, match="unique"):
        migrate(Mock(), tmp_path)
