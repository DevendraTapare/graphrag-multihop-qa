"""Exact, indexed-start paths of one to three allowlisted factual relationships."""

import json
from dataclasses import dataclass

from app.db.neo4j import DatabaseUnavailable
from app.extraction.models import stable_id
from app.graph.fixtures import ROOT
from app.graph_rag.models import GraphFailure, Plan


@dataclass(frozen=True)
class GraphPolicy:
    sources: tuple[str, ...]
    processing_version: str
    curated_fixture_id: str | None = "fixture:corporate-v1"

    @classmethod
    def load(cls):
        raw = json.loads((ROOT / "data/runtime/graph_corpus_v1.json").read_text(encoding="utf-8"))
        return cls(tuple(raw["source_ids"]), raw["processing_version"], raw["curated_fixture_id"])


ELIGIBILITY = """
all(r IN relationships(p) WHERE
 (r.extraction_method = 'manual_fixture' AND r.fixture_id = $fixture)
 OR (r.extraction_method = 'deterministic_rules' AND r.provenance_status = 'verified_rule'
     AND r.processing_version = $processing AND r.source_id IN $sources AND EXISTS {
       MATCH (s:IngestionSource {id: r.source_id}), (i:Ingestion {id: r.ingestion_id})
       WHERE s.status = 'ready' AND i.status = 'ready'
         AND s.current_run_id = i.id AND s.desired_run_id = i.id
         AND s.processing_version = $processing AND i.processing_version = $processing
         AND s.content_hash = r.content_hash AND i.content_hash = r.content_hash
         AND i.document_id = r.source_document_id AND i.source_id = s.id
     }))
"""


def path_template(plan, depth):
    # Revalidate even internal model instances. User captures never become query fragments.
    plan = Plan.model_validate(plan.model_dump())
    if not 1 <= depth <= plan.hop_count <= 3:
        raise GraphFailure("invalid_graph_plan")
    pattern = f"(n0:{plan.start_type.value} {{id: $start}})"
    for j, step in enumerate(plan.steps[:depth], 1):
        target = f"(n{j}:{step.types[1].value})"
        relation = f"[r{j}:{step.relation.value}]"
        pattern += (
            f"-{relation}->{target}" if step.direction == "outgoing" else f"<-{relation}-{target}"
        )
    return f"""
MATCH p={pattern}
WHERE {ELIGIBILITY}
RETURN [n IN nodes(p) | {{properties: properties(n), labels: labels(n)}}] AS nodes,
       [r IN relationships(p) | {{properties: properties(r), kind: type(r),
         source: startNode(r).id, target: endNode(r).id}}] AS edges
LIMIT $limit
"""


METADATA = """
UNWIND $rows AS ref
OPTIONAL MATCH (c:Chunk {id: ref.chunk})
OPTIONAL MATCH (d:Document {id: ref.document})
OPTIONAL MATCH (s:IngestionSource {id: ref.source})
OPTIONAL MATCH (i:Ingestion {id: ref.run})
CALL (c) {
  OPTIONAL MATCH (c)-[link:PART_OF|DERIVED_FROM]->(parent:Document)
  RETURN collect({kind: type(link), target: parent.id, properties: properties(link)}) AS links
}
CALL (i) {
  OPTIONAL MATCH (whole:Chunk {ingestion_id: i.id})
  RETURN collect(properties(whole)) AS chunks
}
RETURN ref.key AS key, properties(c) AS chunk, labels(c) AS chunk_labels,
       properties(d) AS document, labels(d) AS document_labels,
       properties(s) AS source, properties(i) AS run, links, chunks
"""


def edge_key(edge):
    return stable_id(
        "graph-edge", edge["source"], edge["kind"], edge["properties"].get("id"), edge["target"]
    )


def state_signature(rows):
    def clean(value, field=None):
        if isinstance(value, dict):
            return {
                k: clean(v, k)
                for k, v in value.items()
                if k not in {"lock_marker", "claim_token", "lease_until", "updated_at"}
            }
        if isinstance(value, list):
            values = [clean(v) for v in value]
            if field in {None, "labels", "links", "chunks"}:
                return sorted(values, key=lambda v: json.dumps(v, sort_keys=True, default=str))
            return values
        return value

    return json.dumps(clean(rows), sort_keys=True, default=str)


class GraphRepository:
    def __init__(self, database, policy, max_candidates=128, query_timeout=10):
        if not 1 <= max_candidates <= 256 or not 0 < query_timeout <= 30:
            raise ValueError("Invalid graph query bounds")
        self.db, self.policy = database, policy
        self.max_candidates, self.query_timeout = max_candidates, query_timeout

    def read(self, query, parameters, budget):
        try:
            return self.db.execute(
                query, parameters, timeout=min(self.query_timeout, budget.remaining())
            )
        except DatabaseUnavailable as exc:
            code = getattr(exc.__cause__, "code", "") or ""
            if "TransactionTimedOut" in code:
                raise GraphFailure("graph_query_timeout") from exc
            raise

    def capture(self, plan, start, budget):
        rows = []
        for depth in range(1, plan.hop_count + 1):
            found = self.read(
                path_template(plan, depth),
                {
                    "start": start,
                    "fixture": self.policy.curated_fixture_id,
                    "processing": self.policy.processing_version,
                    "sources": list(self.policy.sources),
                    "limit": self.max_candidates - len(rows) + 1,
                },
                budget,
            )
            rows.extend({**r, "depth": depth} for r in found)
            if len(rows) > self.max_candidates:
                return rows, True
            if not found:
                break
        return rows, False

    def metadata(self, rows, budget):
        edges = {edge_key(e): e for row in rows for e in row["edges"]}
        refs = [
            {
                "key": key,
                "document": e["properties"].get("source_document_id"),
                "chunk": e["properties"].get("source_chunk_id"),
                "source": e["properties"].get("source_id"),
                "run": e["properties"].get("ingestion_id"),
            }
            for key, e in edges.items()
        ]
        if not refs:
            return {}
        return {r["key"]: r for r in self.read(METADATA, {"rows": refs}, budget)}

    def recheck(self, plan, start, rows, metadata, budget):
        current, overflow = self.capture(plan, start, budget)
        if overflow or state_signature(current) != state_signature(rows):
            raise GraphFailure("graph_snapshot_changed")
        if state_signature(self.metadata(current, budget)) != state_signature(metadata):
            raise GraphFailure("graph_snapshot_changed")
