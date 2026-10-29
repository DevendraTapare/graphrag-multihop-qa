from unittest.mock import Mock

import pytest

from app.graph.fixtures import read_fixture
from app.repositories.fixture import FixtureConflict, load_fixture, reset_fixture


@pytest.mark.parametrize(
    "mode,confirmation",
    [
        ("production", "fixture:corporate-v1"),
        ("test", "fixture:corporate-v1"),
        ("development", None),
        ("development", "wrong-fixture"),
    ],
)
def test_reset_guard_precedes_database_access(settings, mode, confirmation):
    database = Mock(settings=settings.model_copy(update={"app_env": mode}))
    with pytest.raises(FixtureConflict, match="explicit fixture ID confirmation"):
        reset_fixture(database, "fixture:corporate-v1", confirmation)
    database.driver.session.assert_not_called()


def test_loader_refuses_missing_constraints(settings):
    database = Mock(settings=settings)
    database.execute.return_value = []
    with pytest.raises(FixtureConflict, match="migrations"):
        load_fixture(database, read_fixture())
    database.driver.session.assert_not_called()
