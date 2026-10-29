from app.db.migrations import MIGRATIONS
from app.db.neo4j import GraphDatabaseClient
from app.graph.fixtures import graph_rows
from app.graph.queries import EVALUATION_PATH, THREE_HOP, TWO_HOP
from app.models.fixtures import Evaluation, Fixture, validate_evaluations


class GraphValidationFailure(ValueError):
    pass


def validate_graph(database: GraphDatabaseClient, fixture: Fixture, evaluations: list[Evaluation]):
    validate_evaluations(fixture, evaluations)
    nodes, edges = graph_rows(fixture)
    actual_nodes = database.execute(
        "MATCH (n:GraphNode) WHERE n.fixture_id = $fixture "
        "RETURN properties(n) AS props, labels(n) AS labels",
        {"fixture": fixture.id},
    )
    expected_nodes = {n["properties"]["id"]: n for n in nodes}
    if len(actual_nodes) != len(nodes):
        raise GraphValidationFailure("Unexpected fixture node counts")
    for row in actual_nodes:
        expected = expected_nodes.get(row["props"].get("id"))
        if (
            not expected
            or row["props"] != expected["properties"]
            or set(row["labels"])
            != {
                "GraphNode",
                expected["label"],
            }
        ):
            raise GraphValidationFailure(
                "Node snapshot mismatch, duplicate logical entity or orphan chunk"
            )
    actual_edges = database.execute(
        "MATCH (a)-[r]->(b) WHERE r.fixture_id = $fixture "
        "OR (a.fixture_id = $fixture AND b.fixture_id = $fixture AND r.ingestion_id IS NULL) "
        "RETURN a.id AS source, b.id AS target, type(r) AS kind, properties(r) AS properties",
        {"fixture": fixture.id},
    )
    expected_edges = {e["properties"]["id"]: e for e in edges}
    if len(actual_edges) != len(edges):
        raise GraphValidationFailure("Unexpected fixture relationship counts")
    seen = set()
    for row in actual_edges:
        id = row["properties"].get("id")
        if id in seen or expected_edges.get(id) != row:
            raise GraphValidationFailure(
                "Relationship direction, identity or evidence provenance mismatch"
            )
        seen.add(id)
    constraints = {r["name"]: r for r in database.execute("SHOW CONSTRAINTS")}
    indexes = {r["name"]: r for r in database.execute("SHOW INDEXES")}
    # Inspect definitions as well as names: IF NOT EXISTS alone cannot prove schema correctness.
    for path in sorted(MIGRATIONS.glob("*.cypher")):
        for statement in path.read_text().split(";"):
            words = statement.split()
            if not words:
                continue
            name = words[3] if words[1] == "VECTOR" else words[2]
            if words[1] == "CONSTRAINT":
                import re

                label = re.search(r":(\w+)[)\]]", statement).group(1)
                schema = constraints.get(name)
                expected_type = "RELATIONSHIP" if "[r:" in statement else "NODE"
                if (
                    not schema
                    or schema["labelsOrTypes"] != [label]
                    or schema["properties"] != ["id"]
                ):
                    raise GraphValidationFailure(f"Missing or incorrect constraint: {name}")
                if schema["entityType"] != expected_type or "UNIQUENESS" not in schema["type"]:
                    raise GraphValidationFailure(f"Incorrect constraint type: {name}")
            else:
                import re

                label = re.search(r":(\w+)\)", statement).group(1)
                props = re.findall(r"n\.(\w+)", statement)
                schema = indexes.get(name)
                if (
                    not schema
                    or schema["state"] != "ONLINE"
                    or schema["labelsOrTypes"] != [label]
                    or schema["properties"] != props
                    or schema["type"] != ("VECTOR" if words[1] == "VECTOR" else "RANGE")
                ):
                    raise GraphValidationFailure(f"Missing or incorrect index: {name}")
    if "schema_migration_version" not in constraints:
        raise GraphValidationFailure("Missing migration version constraint")
    for e in evaluations:
        if e.answerable:
            result = database.execute(
                EVALUATION_PATH,
                {
                    "start": e.expected_path[0],
                    "nodes": e.expected_path,
                    "facts": e.supporting_fact_ids,
                    "fixture": fixture.id,
                },
            )
            if result != [{"count": 1}]:
                raise GraphValidationFailure(f"Missing evaluation evidence path: {e.id}")
    params = {"person": "person:priya", "fixture": fixture.id}
    return {
        "nodes": len(nodes),
        "relationships": len(edges),
        "facts": len(fixture.facts),
        "answerable_paths": sum(e.answerable for e in evaluations),
        "two_hop": database.execute(TWO_HOP, params),
        "three_hop": database.execute(THREE_HOP, params),
    }
