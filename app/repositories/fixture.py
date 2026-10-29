from collections import defaultdict

from app.db.neo4j import GraphDatabaseClient
from app.graph.fixtures import graph_rows
from app.models.fixtures import Fixture


class FixtureConflict(ValueError):
    pass


def require_import_constraints(database: GraphDatabaseClient) -> None:
    constraints = {r["name"]: r for r in database.execute("SHOW CONSTRAINTS")}
    required = {"graph_node_id": ("GraphNode", "NODE"), "fixture_lock_id": ("FixtureLock", "NODE")}
    for kind in (
        "MANAGES",
        "WORKS_FOR",
        "USES",
        "HOSTED_ON",
        "BELONGS_TO",
        "MENTIONS",
        "DERIVED_FROM",
        "PART_OF",
    ):
        required[f"{kind.lower()}_id"] = (kind, "RELATIONSHIP")
    for name, (label, entity_type) in required.items():
        constraint = constraints.get(name)
        if (
            not constraint
            or constraint["labelsOrTypes"] != [label]
            or constraint["properties"] != ["id"]
            or constraint["entityType"] != entity_type
            or "UNIQUENESS" not in constraint["type"]
        ):
            raise FixtureConflict("Run schema migrations before importing fixtures")


def load_fixture(database: GraphDatabaseClient, fixture: Fixture) -> dict[str, int]:
    """Atomic import. Immutable snapshots reject collisions and changed fixture payloads."""
    require_import_constraints(database)
    nodes, edges = graph_rows(fixture)
    with database.driver.session(database=database.settings.neo4j_database) as session:
        with session.begin_transaction(timeout=database.settings.neo4j_import_timeout) as tx:
            # Reserve a local import lock via a write, serializing concurrent fixture imports.
            tx.run(
                "MERGE (l:FixtureLock {id: $id}) SET l.touched = datetime()",
                id=fixture.id,
            ).consume()
            expected_nodes = {r["properties"]["id"]: r for r in nodes}
            for existing in tx.run(
                "UNWIND $nodes AS row MATCH (n:GraphNode {id: row.properties.id}) "
                "RETURN n.id AS id, properties(n) AS props, labels(n) AS labels",
                nodes=nodes,
            ):
                expected = expected_nodes[existing["id"]]
                if existing["props"] != expected["properties"] or set(existing["labels"]) != {
                    "GraphNode",
                    expected["label"],
                }:
                    raise FixtureConflict(f"Node collision or changed snapshot: {existing['id']}")
            grouped_nodes = defaultdict(list)
            for row in nodes:
                grouped_nodes[row["label"]].append(row["properties"])
            for label, rows in grouped_nodes.items():
                # Labels come only from validated enums and fixed Document / Chunk labels.
                tx.run(
                    f"UNWIND $rows AS row MERGE (n:GraphNode:{label} {{id: row.id}}) "
                    "ON CREATE SET n = row",
                    rows=rows,
                ).consume()
            expected_edges = {
                r["properties"]["id"]: {
                    "source": r["source"],
                    "target": r["target"],
                    "kind": r["kind"],
                    "props": r["properties"],
                }
                for r in edges
            }
            seen = set()
            for existing in tx.run(
                "UNWIND $edges AS row MATCH (a)-[r {id: row.properties.id}]->(b) "
                "RETURN a.id AS source, b.id AS target, type(r) AS kind, properties(r) AS props",
                edges=edges,
            ):
                id = existing["props"]["id"]
                if id in seen or dict(existing) != expected_edges[id]:
                    raise FixtureConflict(f"Relationship collision: {id}")
                seen.add(id)
            grouped_edges = defaultdict(list)
            for row in edges:
                grouped_edges[row["kind"]].append(row)
            for kind, rows in grouped_edges.items():
                count = tx.run(
                    "UNWIND $rows AS row MATCH (a:GraphNode {id: row.source}), "
                    "(b:GraphNode {id: row.target}) "
                    f"MERGE (a)-[r:{kind} {{id: row.properties.id}}]->(b) "
                    "ON CREATE SET r = row.properties RETURN count(r) AS count",
                    rows=rows,
                ).single()["count"]
                if count != len(rows):
                    raise FixtureConflict("Missing fixture relationship endpoint")
            tx.commit()
    return {"nodes": len(nodes), "relationships": len(edges), "facts": len(fixture.facts)}


def reset_fixture(database: GraphDatabaseClient, fixture_id: str, confirmation: str | None) -> None:
    if database.settings.app_env != "development" or confirmation != fixture_id:
        raise FixtureConflict(
            "Reset requires development mode and explicit fixture ID confirmation"
        )
    with database.driver.session(database=database.settings.neo4j_database) as session:
        with session.begin_transaction(timeout=database.settings.neo4j_import_timeout) as tx:
            tx.run(
                "MERGE (l:FixtureLock {id: $id}) SET l.touched = datetime()", id=fixture_id
            ).consume()
            external = tx.run(
                "MATCH (n:GraphNode {fixture_id: $id})-[r]-() "
                "WHERE r.fixture_id IS NULL OR r.fixture_id <> $id RETURN count(r) AS count",
                id=fixture_id,
            ).single()["count"]
            if external:
                raise FixtureConflict("Reset refused: external edges reference fixture nodes")
            tx.run("MATCH ()-[r {fixture_id: $id}]->() DELETE r", id=fixture_id).consume()
            tx.run("MATCH (n:GraphNode {fixture_id: $id}) DELETE n", id=fixture_id).consume()
            tx.commit()
