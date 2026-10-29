import argparse
import json
import logging

from app.core.config import Settings
from app.core.logging import configure_logging
from app.db.migrations import MigrationFailure, migrate
from app.db.neo4j import GraphDatabaseClient
from app.graph.fixtures import read_evaluations, read_fixture
from app.repositories.fixture import FixtureConflict, load_fixture, reset_fixture
from app.services.validation import GraphValidationFailure, validate_graph


def main():
    parser = argparse.ArgumentParser(description="Stage 1 trusted graph maintenance")
    parser.add_argument("command", choices=["migrate", "load", "validate", "reset"])
    parser.add_argument("--confirm-fixture", help="Required for development-only scoped reset")
    args = parser.parse_args()
    settings = Settings()
    configure_logging(settings.neo4j_password.get_secret_value())
    db = GraphDatabaseClient(settings)
    try:
        fixture = read_fixture()
        if args.command == "migrate":
            result = {"applied": migrate(db)}
        elif args.command == "load":
            result = load_fixture(db, fixture)
        elif args.command == "validate":
            result = validate_graph(db, fixture, read_evaluations())
        else:
            reset_fixture(db, fixture.id, args.confirm_fixture)
            result = {"reset": fixture.id, "schema_preserved": True}
        print(json.dumps(result, indent=2))
    except (MigrationFailure, FixtureConflict, GraphValidationFailure) as exc:
        logging.getLogger(__name__).error("Graph maintenance failed: %s", exc)
        raise SystemExit(1) from None
    except Exception:
        logging.getLogger(__name__).error(
            "Graph maintenance failed; check local database and schema"
        )
        raise SystemExit(1) from None
    finally:
        db.close()


if __name__ == "__main__":
    main()
