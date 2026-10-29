"""Fixed validation queries. These are not retrieval endpoints."""

TWO_HOP = """
MATCH (p:Person {id: $person})-[m:MANAGES]->(j:Project)-[u:USES]->(t:Technology)
WHERE m.fixture_id = $fixture AND u.fixture_id = $fixture
RETURN [p.id, j.id, t.id] AS nodes, [m.id, u.id] AS facts
"""

THREE_HOP = """
MATCH (p:Person {id: $person})-[m:MANAGES]->(j:Project)
      -[u:USES]->(t:Technology)-[h:HOSTED_ON]->(c:Platform)
WHERE m.fixture_id = $fixture AND u.fixture_id = $fixture AND h.fixture_id = $fixture
RETURN [p.id, j.id, t.id, c.id] AS nodes, [m.id, u.id, h.id] AS facts, c.name AS answer
"""

EVALUATION_PATH = """
MATCH p=(a:GraphNode {id: $start})-[:MANAGES|WORKS_FOR|USES|HOSTED_ON|BELONGS_TO*1..3]->(b)
WHERE [n IN nodes(p) | n.id] = $nodes AND [r IN relationships(p) | r.id] = $facts
  AND all(r IN relationships(p) WHERE r.fixture_id = $fixture)
RETURN count(p) AS count
"""
