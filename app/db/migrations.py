import hashlib
from pathlib import Path

from app.db.neo4j import DatabaseUnavailable, GraphDatabaseClient
from app.models.fixtures import safe_filename

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


class MigrationFailure(RuntimeError):
    pass


def migrate(database: GraphDatabaseClient, directory: Path = MIGRATIONS) -> list[str]:
    files = sorted(directory.glob("*.cypher"))
    versions = [p.name[:3] for p in files]
    if len(versions) != len(set(versions)) or any(not safe_filename(p.name) for p in files):
        raise MigrationFailure("Migration filenames must have unique ordered numeric versions")
    database.execute(
        "CREATE CONSTRAINT schema_migration_version IF NOT EXISTS "
        "FOR (m:SchemaMigration) REQUIRE m.version IS UNIQUE"
    )
    applied = {
        r["version"]: r["checksum"]
        for r in database.execute(
            "MATCH (m:SchemaMigration) RETURN m.version AS version, m.checksum AS checksum"
        )
    }
    if set(applied) - set(versions):
        raise MigrationFailure("Database has migrations absent from this checkout")
    completed = []
    for path in files:
        version = path.name[:3]
        content = path.read_text(encoding="utf-8")
        checksum = hashlib.sha256(content.encode()).hexdigest()
        if version in applied:
            if applied[version] != checksum:
                raise MigrationFailure(f"Applied migration changed: {path.name}")
            continue
        if any(v > version for v in applied):
            raise MigrationFailure(f"Out-of-order migration: {path.name}")
        try:
            # Schema DDL commits separately. A partial failure is safely rerun using IF NOT EXISTS.
            for statement in content.split(";"):
                if statement.strip():
                    database.execute(statement.strip())
            database.execute(
                "MERGE (m:SchemaMigration {version: $version}) "
                "SET m.checksum = $checksum, m.name = $name, m.applied_at = datetime()",
                {"version": version, "checksum": checksum, "name": path.name},
            )
        except DatabaseUnavailable as exc:
            raise MigrationFailure(
                f"Schema migration failed: {path.name}; safely rerun after repair"
            ) from exc
        completed.append(path.name)
    database.execute("CALL db.awaitIndexes($seconds)", {"seconds": 30})
    return completed
