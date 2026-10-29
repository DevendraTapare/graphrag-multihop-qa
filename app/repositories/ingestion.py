import json
from collections import defaultdict
from dataclasses import dataclass
from uuid import uuid4

from neo4j import unit_of_work
from neo4j.exceptions import DriverError, Neo4jError

from app.db.neo4j import DatabaseUnavailable, GraphDatabaseClient
from app.extraction.models import (
    AcceptedFact,
    IngestionFailure,
    SourceDocument,
    TextChunk,
    ValidatedExtraction,
    stable_id,
    text_hash,
    utcnow,
)
from app.extraction.pipeline import ExtractionPipeline
from app.graph.fixtures import graph_rows, read_fixture
from app.graph.schema import DIRECTIONS, FactType, Label
from app.models.fixtures import normalize_name

VISIBLE_FACTS = """
MATCH (s:IngestionSource {id: $source})
MATCH (i:Ingestion {id: s.current_run_id, status: 'ready'})
MATCH (a)-[r]->(b)
WHERE s.status = 'ready' AND s.desired_run_id = i.id AND r.ingestion_id = i.id
  AND s.processing_version = $version AND i.processing_version = $version
  AND r.provenance_status = 'verified_rule' AND r.content_hash = s.content_hash
  AND r.processing_version = i.processing_version AND r.source_document_id = i.document_id
RETURN a.id AS subject, b.id AS object, type(r) AS predicate, properties(r) AS properties
ORDER BY r.id
"""


@dataclass(frozen=True)
class Claim:
    source_id: str
    run_id: str
    document_id: str
    content_hash: str
    version: str
    token: str


def batches(items, size):
    for start in range(0, len(items), size):
        yield items[start : start + size]


class IngestionRepository:
    def __init__(
        self,
        database: GraphDatabaseClient,
        pipeline: ExtractionPipeline,
        batch_size: int = 20,
        lease_seconds: int = 300,
    ):
        if not 1 <= batch_size <= 100 or not 1 <= lease_seconds <= 3600:
            raise ValueError("Invalid transactional batch or lease bounds")
        self.db, self.pipeline = database, pipeline
        self.batch_size, self.lease_seconds = batch_size, lease_seconds
        nodes, _ = graph_rows(read_fixture())
        self.curated_nodes = {n["properties"]["id"]: n["properties"] for n in nodes}

    def write(self, callback, *args):
        @unit_of_work(timeout=self.db.settings.neo4j_import_timeout)
        def transaction(tx):
            return callback(tx, *args)

        try:
            with self.db.driver.session(database=self.db.settings.neo4j_database) as session:
                return session.execute_write(transaction)
        except (DriverError, Neo4jError, OSError) as exc:
            raise IngestionFailure("database_unavailable") from exc

    def read(self, query, parameters=None):
        try:
            return self.db.execute(query, parameters)
        except DatabaseUnavailable as exc:
            raise IngestionFailure("database_unavailable") from exc

    def require_schema(self):
        names = {r["name"] for r in self.read("SHOW CONSTRAINTS")}
        if not {
            "graph_node_id",
            "ingestion_source_id",
            "ingestion_run_id",
            *[f"{t.value.lower()}_id" for t in FactType],
            "part_of_id",
            "derived_from_id",
            "mentions_id",
        }.issubset(names):
            raise IngestionFailure("ingestion_migration_required")

    def _merge_node(self, tx, label: str, props: dict, immutable: list[str]):
        if label not in {"Document", "Chunk", *[label.value for label in Label]}:
            raise IngestionFailure("unsupported_entity_label")
        existing = tx.run(
            "MATCH (n:GraphNode {id: $id}) RETURN properties(n) AS props, labels(n) AS labels",
            id=props["id"],
        ).single()
        if existing and (
            set(existing["labels"]) != {"GraphNode", label}
            or any(existing["props"].get(k) != props.get(k) for k in immutable)
        ):
            raise IngestionFailure("canonical_or_snapshot_collision")
        tx.run(
            f"MERGE (n:GraphNode:{label} {{id: $id}}) ON CREATE SET n = $props",
            id=props["id"],
            props=props,
        ).consume()

    def start(self, document: SourceDocument) -> Claim | None:
        self.require_schema()
        token, now = uuid4().hex, utcnow()
        claim = Claim(
            document.source_id,
            stable_id("ingestion", document.id, self.pipeline.version),
            document.id,
            document.content_hash,
            self.pipeline.version,
            token,
        )
        return self.write(self._start, document, claim, now.isoformat(), now.timestamp())

    def _start(self, tx, document, claim, now, epoch):
        source = tx.run(
            "MERGE (s:IngestionSource {id: $id}) ON CREATE SET s.created_at = $now "
            "SET s.lock_marker = $token RETURN properties(s) AS data",
            id=claim.source_id,
            now=now,
            token=claim.token,
        ).single()["data"]
        if source.get("status") == "processing" and source.get("lease_until", 0) > epoch:
            if source.get("claim_token") == claim.token:
                return claim  # Replay after an uncertain commit acknowledges the same claim.
            raise IngestionFailure("ingestion_busy")
        if source.get("current_run_id") == claim.run_id and source.get("status") == "ready":
            run = tx.run(
                "MATCH (i:Ingestion {id: $id, status: 'ready'}) RETURN i.id AS id", id=claim.run_id
            ).single()
            if run:
                return None
        previous = source.get("desired_run_id")
        if source.get("status") == "processing" and previous:
            tx.run(
                "MATCH (i:Ingestion {id: $id}) SET i.status = 'failed', "
                "i.error_category = 'interrupted_lease_expired', i.failed_at = $now, "
                "i.state_history = i.state_history + ['failed']",
                id=previous,
                now=now,
            ).consume()
        props = {
            "id": document.id,
            "title": document.source_filename,
            "text": document.text,
            "source_id": document.source_id,
            "source_filename": document.source_filename,
            "content_hash": document.content_hash,
            "ingestion_version": document.ingestion_version,
            "original_document_id": document.original_document_id,
            "created_at": document.created_at.isoformat(),
            "origin": "automatic_ingestion",
        }
        self._merge_node(tx, "Document", props, [k for k in props if k != "created_at"])
        tx.run(
            "MERGE (i:Ingestion {id: $run}) "
            "ON CREATE SET i.created_at = $now, i.state_history = [] "
            "SET i.status = 'pending', i.state_history = i.state_history + ['pending'], "
            "i.source_id = $source, i.document_id = $document, i.source_filename = $filename, "
            "i.content_hash = $hash, i.processing_version = $version, i.error_category = null, "
            "i.processed_at = null, i.failed_at = null, i.summary_json = null, "
            "i.rejections_json = '[]', i.accepted_candidate_count = 0, "
            "i.entity_count = 0, i.fact_count = 0, i.rejected_count = 0 "
            "WITH i SET i.status = 'processing', "
            "i.state_history = i.state_history + ['processing'], "
            "i.started_at = $now, i.claim_token = $token "
            "WITH i MATCH (s:IngestionSource {id: $source}) "
            "SET s.status = 'processing', s.desired_run_id = $run, s.current_run_id = null, "
            "s.document_id = $document, s.content_hash = $hash, s.processing_version = $version, "
            "s.claim_token = $token, s.lease_until = $lease, s.updated_at = $now",
            run=claim.run_id,
            source=claim.source_id,
            document=document.id,
            filename=document.source_filename,
            hash=document.content_hash,
            version=claim.version,
            now=now,
            token=claim.token,
            lease=epoch + self.lease_seconds,
        ).consume()
        return claim

    def _guard(self, tx, claim: Claim, epoch: float):
        row = tx.run(
            "MATCH (s:IngestionSource {id: $id}) SET s.lock_marker = $token "
            "RETURN properties(s) AS data",
            id=claim.source_id,
            token=claim.token,
        ).single()
        state = row["data"] if row else {}
        if (
            state.get("claim_token") != claim.token
            or state.get("desired_run_id") != claim.run_id
            or state.get("status") != "processing"
            or state.get("lease_until", 0) < epoch
            or state.get("content_hash") != claim.content_hash
            or state.get("processing_version") != claim.version
        ):
            raise IngestionFailure("stale_ingestion_claim")
        tx.run(
            "MATCH (s:IngestionSource {id: $id}) SET s.lease_until = $lease",
            id=claim.source_id,
            lease=epoch + self.lease_seconds,
        ).consume()

    def _merge_edges(self, tx, kind: str, rows: list[dict]):
        if kind not in {t.value for t in FactType} | {"MENTIONS", "PART_OF", "DERIVED_FROM"}:
            raise IngestionFailure("unsupported_relationship_type")
        for row in rows:
            existing = list(
                tx.run(
                    "MATCH (a)-[r {id: $id}]->(b) RETURN a.id AS source, b.id AS target, "
                    "type(r) AS kind, properties(r) AS props",
                    id=row["props"]["id"],
                )
            )
            if existing:
                if len(existing) != 1:
                    raise IngestionFailure("assertion_identity_collision")
                previous = dict(existing[0])
                expected = {**row, "kind": kind}
                # Original creation time survives reprocessing and transaction replay.
                previous["props"].pop("created_at", None)
                expected["props"] = {k: v for k, v in row["props"].items() if k != "created_at"}
                if previous != expected:
                    raise IngestionFailure("assertion_identity_collision")
        count = tx.run(
            "UNWIND $rows AS row MATCH (a:GraphNode {id: row.source}), "
            "(b:GraphNode {id: row.target}) "
            f"MERGE (a)-[r:{kind} {{id: row.props.id}}]->(b) ON CREATE SET r = row.props "
            "RETURN count(r) AS count",
            rows=rows,
        ).single()["count"]
        if count != len(rows):
            raise IngestionFailure("missing_assertion_endpoint")

    def put_chunks(self, claim, document, chunks):
        self.pipeline.validator.validate_sources(document, chunks, claim.version)
        for batch in batches(chunks, self.batch_size):
            self.write(self._put_chunks, claim, batch, utcnow().timestamp())

    def record_plan(self, claim, chunks, result):
        self.write(self._record_plan, claim, chunks, result, utcnow().timestamp())

    def _record_plan(self, tx, claim, chunks, result, epoch):
        self._guard(tx, claim, epoch)
        tx.run(
            "MATCH (i:Ingestion {id: $run}) SET i.expected_chunk_count = $chunks, "
            "i.accepted_candidate_count = $accepted, i.rejected_count = $rejected, "
            "i.rejections_json = $rejections, i.extracted_entity_count = $entities",
            run=claim.run_id,
            chunks=len(chunks),
            accepted=len(result.facts),
            rejected=len(result.rejections),
            entities=len(result.entities),
            rejections=json.dumps([r.model_dump() for r in result.rejections]),
        ).consume()

    def _put_chunks(self, tx, claim, chunks, epoch):
        self._guard(tx, claim, epoch)
        for chunk in chunks:
            props = {
                **chunk.model_dump(),
                "ingestion_id": claim.run_id,
                "origin": "automatic_ingestion",
            }
            self._merge_node(tx, "Chunk", props, list(props))
            for kind in ("PART_OF", "DERIVED_FROM"):
                self._merge_edges(
                    tx,
                    kind,
                    [
                        {
                            "source": chunk.id,
                            "target": chunk.document_id,
                            "props": {
                                "id": stable_id("auto-edge", kind, chunk.id, chunk.document_id),
                                "ingestion_id": claim.run_id,
                                "method": "verbatim_excerpt",
                            },
                        }
                    ],
                )

    def put_entities(self, claim, document, chunks, result):
        unique = {e.canonical_id: e for e in result.entities}
        mentions = [e.candidate for e in result.entities]
        for resolved in result.entities:
            self.pipeline.validator.validate_entity(document, chunks, resolved.candidate)
            if (
                self.pipeline.registry.resolve(resolved.candidate, document, mentions)
                != resolved.canonical_id
            ):
                raise IngestionFailure("canonical_identity_proof_mismatch")
        for group in batches(list(unique), self.batch_size):
            self.write(self._put_entities, claim, group, utcnow().timestamp())
        for group in batches(result.entities, self.batch_size):
            self.write(self._put_mentions, claim, group, utcnow().timestamp())

    def _put_entities(self, tx, claim, ids, epoch):
        self._guard(tx, claim, epoch)
        for id in ids:
            entity = self.pipeline.registry.entries[id].entity
            props = self.curated_nodes.get(id) or {
                "id": id,
                "name": entity.name,
                "scope": entity.scope,
                "normalized_name": normalize_name(entity.name),
                "origin": "controlled_registry",
            }
            self._merge_node(
                tx, entity.label.value, props, ["id", "name", "scope", "normalized_name"]
            )

    def _put_mentions(self, tx, claim, entities, epoch):
        self._guard(tx, claim, epoch)
        rows = []
        for entity in entities:
            candidate = entity.candidate
            rows.append(
                {
                    "source": candidate.source_chunk_id,
                    "target": entity.canonical_id,
                    "props": {
                        "id": stable_id("auto-edge", "MENTIONS", claim.run_id, candidate.id),
                        "ingestion_id": claim.run_id,
                        "mention_start": candidate.start,
                        "mention_end": candidate.end,
                        "mention": candidate.mention,
                    },
                }
            )
        self._merge_edges(tx, "MENTIONS", rows)

    def fact_row(self, claim: Claim, fact: AcceptedFact) -> dict:
        c = fact.candidate
        return {
            "source": fact.subject_id,
            "target": fact.object_id,
            "props": {
                "id": fact.id,
                "ingestion_id": claim.run_id,
                "source_id": fact.source_id,
                "source_document_id": c.source_document_id,
                "source_chunk_id": c.source_chunk_id,
                "content_hash": fact.content_hash,
                "processing_version": fact.processing_version,
                "ingestion_version": fact.ingestion_version,
                "quote": c.evidence,
                "evidence_start": c.start,
                "evidence_end": c.end,
                "extraction_method": c.extraction_method,
                "extraction_version": c.extraction_version,
                "rule_id": c.rule_id,
                "rule_score": c.rule_score,
                "provenance_status": fact.provenance_status,
                "created_at": fact.created_at.isoformat(),
                "candidate_json": c.model_dump_json(),
            },
        }

    def put_facts(self, claim, document, chunks, batch, result):
        grouped = defaultdict(list)
        for fact in result.facts:
            self.pipeline.validator.verify_fact(
                fact, document, chunks, batch.entities, claim.version
            )
            grouped[fact.candidate.predicate.value].append(self.fact_row(claim, fact))
        for kind, rows in grouped.items():
            for group in batches(rows, self.batch_size):
                self.write(self._put_facts, claim, kind, group, utcnow().timestamp())

    def _put_facts(self, tx, claim, kind, rows, epoch):
        self._guard(tx, claim, epoch)
        if kind not in {t.value for t in FactType}:
            raise IngestionFailure("unsupported_relationship_type")
        for row in rows:
            props = row["props"]
            proof = list(
                tx.run(
                    "MATCH (c:Chunk {id: $chunk, ingestion_id: $run})-[:PART_OF]->"
                    "(d:Document {id: $document}), (a:GraphNode {id: $subject}), "
                    "(b:GraphNode {id: $object}) RETURN properties(c) AS chunk, "
                    "properties(d) AS document, labels(a) AS source_labels, "
                    "labels(b) AS target_labels",
                    chunk=props["source_chunk_id"],
                    run=claim.run_id,
                    document=props["source_document_id"],
                    subject=row["source"],
                    object=row["target"],
                )
            )
            if len(proof) != 1:
                raise IngestionFailure("missing_persisted_source_evidence")
            source = proof[0]["document"]
            chunk = proof[0]["chunk"]
            if (
                source.get("content_hash") != claim.content_hash
                or text_hash(source["text"]) != claim.content_hash
                or chunk.get("content_hash") != claim.content_hash
                or chunk.get("processing_version") != claim.version
                or not chunk["start"]
                <= props["evidence_start"]
                < props["evidence_end"]
                <= chunk["end"]
                or source["text"][props["evidence_start"] : props["evidence_end"]] != props["quote"]
                or source["text"][chunk["start"] : chunk["end"]] != chunk["text"]
            ):
                raise IngestionFailure("persisted_source_provenance_mismatch")
            expected_source, expected_target = DIRECTIONS[FactType(kind)]
            if set(proof[0]["source_labels"]) != {"GraphNode", expected_source.value} or set(
                proof[0]["target_labels"]
            ) != {"GraphNode", expected_target.value}:
                raise IngestionFailure("invalid_persisted_entity_type")
        self._merge_edges(tx, kind, rows)

    def publish(
        self,
        claim: Claim,
        document: SourceDocument,
        chunks: list[TextChunk],
        result: ValidatedExtraction,
    ):
        rows = [self.fact_row(claim, f) for f in result.facts]
        now = utcnow()
        return self.write(self._publish, claim, document, chunks, result, rows, now)

    def _publish(self, tx, claim, document, chunks, result, expected, now):
        prior = tx.run(
            "MATCH (s:IngestionSource {id: $source}) SET s.lock_marker = $token "
            "WITH s MATCH (i:Ingestion {id: $run}) "
            "WHERE s.current_run_id = $run AND s.status = 'ready' AND i.status = 'ready' "
            "RETURN i.summary_json AS summary",
            source=claim.source_id,
            token=claim.token,
            run=claim.run_id,
        ).single()
        if prior:
            return json.loads(prior["summary"])
        self._guard(tx, claim, now.timestamp())
        actual = [
            r.data()
            for r in tx.run(
                "MATCH (a)-[r]->(b) WHERE r.ingestion_id = $run "
                "AND r.provenance_status IS NOT NULL "
                "RETURN a.id AS source, b.id AS target, type(r) AS kind, properties(r) AS props",
                run=claim.run_id,
            )
        ]
        expected_by_id = {
            r["props"]["id"]: {**r, "kind": f.candidate.predicate.value}
            for r, f in zip(expected, result.facts, strict=True)
        }
        if len(actual) != len(expected_by_id):
            raise IngestionFailure("incomplete_fact_batch")
        for row in actual:
            target = expected_by_id.get(row["props"].get("id"))
            if not target:
                raise IngestionFailure("unexpected_fact_in_batch")

            def comparable(value):
                return {
                    **value,
                    "props": {k: v for k, v in value["props"].items() if k != "created_at"},
                }

            if comparable(row) != comparable(target):
                raise IngestionFailure("stored_fact_provenance_mismatch")
        stored_chunks = [
            r["props"]
            for r in tx.run(
                "MATCH (c:Chunk {ingestion_id: $run}) RETURN properties(c) AS props",
                run=claim.run_id,
            )
        ]
        expected_chunks = {
            c.id: {**c.model_dump(), "ingestion_id": claim.run_id, "origin": "automatic_ingestion"}
            for c in chunks
        }
        if len(stored_chunks) != len(chunks) or any(
            expected_chunks.get(c.get("id")) != c for c in stored_chunks
        ):
            raise IngestionFailure("incomplete_chunk_batch")
        for chunk in chunks:
            links = list(
                tx.run(
                    "MATCH (:Chunk {id: $chunk})-[r:PART_OF|DERIVED_FROM]->(d) "
                    "WHERE r.ingestion_id = $run RETURN type(r) AS kind, d.id AS document",
                    chunk=chunk.id,
                    run=claim.run_id,
                )
            )
            if sorted((r["kind"], r["document"]) for r in links) != [
                ("DERIVED_FROM", document.id),
                ("PART_OF", document.id),
            ]:
                raise IngestionFailure("orphan_source_chunk")
        stored = tx.run(
            "MATCH (d:Document {id: $id}) RETURN d.text AS text, d.content_hash AS hash",
            id=document.id,
        ).single()
        if not stored or (stored["text"], stored["hash"]) != (document.text, document.content_hash):
            raise IngestionFailure("stored_document_provenance_mismatch")
        actual_mentions = {
            r["id"]
            for r in tx.run(
                "MATCH ()-[r:MENTIONS {ingestion_id: $run}]->() RETURN r.id AS id", run=claim.run_id
            )
        }
        expected_mentions = {
            stable_id("auto-edge", "MENTIONS", claim.run_id, e.candidate.id)
            for e in result.entities
        }
        if actual_mentions != expected_mentions:
            raise IngestionFailure("incomplete_entity_batch")
        summary = {
            "document_id": document.id,
            "source_id": document.source_id,
            "run_id": claim.run_id,
            "status": "ready",
            "content_hash": document.content_hash,
            "processing_version": claim.version,
            "chunks": len(chunks),
            "entity_mentions": len(result.entities),
            "entities": len({e.canonical_id for e in result.entities}),
            "facts": len(result.facts),
            "rejected_candidates": len(result.rejections),
        }
        tx.run(
            "MATCH (i:Ingestion {id: $run}), (s:IngestionSource {id: $source}), "
            "(d:Document {id: $document}) "
            "SET i.status = 'ready', i.state_history = i.state_history + ['ready'], "
            "i.processed_at = $now, i.summary_json = $summary, i.rejections_json = $rejections, "
            "i.entity_count = $entities, i.fact_count = $facts, i.rejected_count = $rejected, "
            "i.claim_token = null, s.status = 'ready', s.current_run_id = $run, "
            "s.claim_token = null, s.lease_until = 0, s.updated_at = $now, d.processed_at = $now",
            run=claim.run_id,
            source=claim.source_id,
            document=document.id,
            now=now.isoformat(),
            summary=json.dumps(summary, sort_keys=True),
            rejections=json.dumps([r.model_dump() for r in result.rejections]),
            entities=summary["entities"],
            facts=summary["facts"],
            rejected=summary["rejected_candidates"],
        ).consume()
        return summary

    def fail(self, claim: Claim, category: str):
        self.write(self._fail, claim, category, utcnow().isoformat())

    def _fail(self, tx, claim, category, now):
        row = tx.run(
            "MATCH (s:IngestionSource {id: $source}) SET s.lock_marker = $token "
            "RETURN s.claim_token AS token, s.desired_run_id AS run",
            source=claim.source_id,
            token=claim.token,
        ).single()
        if row and row["token"] == claim.token and row["run"] == claim.run_id:
            tx.run(
                "MATCH (i:Ingestion {id: $run}), (s:IngestionSource {id: $source}) "
                "SET i.status = 'failed', i.error_category = $category, i.failed_at = $now, "
                "i.state_history = i.state_history + ['failed'], i.claim_token = null, "
                "s.status = 'failed', s.current_run_id = null, "
                "s.claim_token = null, s.lease_until = 0",
                run=claim.run_id,
                source=claim.source_id,
                category=category,
                now=now,
            ).consume()

    def results(self, source_id: str | None = None) -> list[dict]:
        return self.read(
            "MATCH (i:Ingestion) WHERE $source IS NULL OR i.source_id = $source "
            "RETURN properties(i) AS ingestion ORDER BY i.created_at, i.id",
            {"source": source_id},
        )

    def record_load_failure(self, source_id: str, filename: str, category: str):
        self.require_schema()
        now, token = utcnow().isoformat(), uuid4().hex
        run_id = stable_id("ingestion", source_id, "load-failure", category, self.pipeline.version)
        self.write(self._record_load_failure, source_id, filename, category, run_id, now, token)

    def _record_load_failure(self, tx, source_id, filename, category, run_id, now, token):
        tx.run(
            "MERGE (s:IngestionSource {id: $source}) ON CREATE SET s.created_at = $now "
            "SET s.lock_marker = $token "
            "WITH s OPTIONAL MATCH "
            "(previous:Ingestion {id: s.desired_run_id, status: 'processing'}) "
            "FOREACH (p IN CASE WHEN previous IS NULL THEN [] ELSE [previous] END | "
            "SET p.status = 'failed', p.error_category = $category, p.failed_at = $now, "
            "p.state_history = p.state_history + ['failed']) "
            "WITH s MERGE (i:Ingestion {id: $run}) "
            "ON CREATE SET i.created_at = $now, "
            "i.state_history = ['pending','processing','failed'] "
            "SET i.source_id = $source, i.source_filename = $filename, i.status = 'failed', "
            "i.error_category = $category, i.failed_at = $now, i.processing_version = $version, "
            "i.started_at = $now, i.fact_count = 0, i.entity_count = 0, i.rejected_count = 0, "
            "i.rejections_json = '[]', s.current_run_id = null, s.desired_run_id = $run, "
            "s.status = 'failed', s.claim_token = null, s.lease_until = 0, s.updated_at = $now",
            source=source_id,
            filename=filename,
            category=category,
            run=run_id,
            now=now,
            token=token,
            version=self.pipeline.version,
        ).consume()

    def visible_facts(self, source_id: str) -> list[dict]:
        return self.read(VISIBLE_FACTS, {"source": source_id, "version": self.pipeline.version})

    def summary(self, source_id: str) -> dict:
        rows = self.read(
            "MATCH (s:IngestionSource {id: $source}), (i:Ingestion {id: s.desired_run_id}) "
            "RETURN i.status AS status, i.summary_json AS summary, "
            "i.error_category AS error_category, "
            "i.id AS run_id, s.id AS source_id",
            {"source": source_id},
        )
        if not rows:
            raise IngestionFailure("ingestion_not_found")
        return json.loads(rows[0]["summary"]) if rows[0]["status"] == "ready" else rows[0]
