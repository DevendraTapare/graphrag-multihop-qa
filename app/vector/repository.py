"""Only node metadata is read. No factual or structural relationship traversal."""

import json
import time
from uuid import uuid4

from neo4j import unit_of_work
from neo4j.exceptions import DriverError, Neo4jError

from app.db.neo4j import DatabaseUnavailable
from app.extraction.chunking import sentences
from app.extraction.models import stable_id, text_hash
from app.vector.embedding import DIMENSION, MODEL, validate_vector
from app.vector.models import RetrievedChunk, VectorFailure

INDEX = "chunk_minilm_cosine"

# Source and run publication are checked independently of any extracted facts.
CANONICAL = """
MATCH (s:IngestionSource), (i:Ingestion), (d:Document), (c:Chunk)
WHERE s.id IN $sources AND s.status = 'ready'
  AND i.id = s.current_run_id AND i.id = s.desired_run_id AND i.status = 'ready'
  AND s.processing_version = $processing AND i.processing_version = $processing
  AND i.content_hash = s.content_hash AND d.id = i.document_id
  AND d.source_id = s.id AND d.content_hash = s.content_hash
  AND c.document_id = d.id AND c.ingestion_id = i.id
  AND c.content_hash = d.content_hash AND c.processing_version = i.processing_version
RETURN properties(s) AS source, properties(i) AS run,
       properties(d) AS document, properties(c) AS chunk
ORDER BY c.id
"""

SEARCH = """
CALL db.index.vector.queryNodes($index, $candidates, $vector) YIELD node, score
WHERE node.build_id = $build AND node.embedding_version = $embedding
MATCH (active:VectorCorpus {id: $corpus}), (published:VectorBuild {id: $build}),
      (s:IngestionSource {id: node.source_id}), (i:Ingestion {id: node.ingestion_id}),
      (d:Document {id: node.document_id}), (c:Chunk {id: node.chunk_id})
WHERE active.status = 'ready' AND published.status = 'ready'
  AND active.current_build = published.id AND active.desired_build = published.id
  AND published.embedding_version = $embedding
  AND s.status = 'ready' AND i.status = 'ready'
  AND s.current_run_id = i.id AND s.desired_run_id = i.id
  AND s.processing_version = node.processing_version
  AND i.processing_version = node.processing_version
  AND i.document_id = d.id AND d.source_id = s.id
  AND s.content_hash = node.content_hash AND i.content_hash = node.content_hash
  AND d.content_hash = node.content_hash AND c.content_hash = node.content_hash
  AND c.document_id = d.id AND c.ingestion_id = i.id
  AND c.processing_version = node.processing_version
RETURN properties(node) AS embedding, properties(s) AS source, properties(i) AS run,
       properties(d) AS document, properties(c) AS chunk, score
ORDER BY score DESC, c.id
LIMIT $k
"""


def canonical_record(row):
    s, i, d, c = (row[k] for k in ("source", "run", "document", "chunk"))
    try:
        valid = (
            0 <= c["start"] < c["end"] <= len(d["text"])
            and d["text"][c["start"] : c["end"]] == c["text"]
            and text_hash(d["text"]) == d["content_hash"] == c["content_hash"]
            and d["id"] == stable_id("autodoc", s["id"], d["content_hash"])
            and c["document_id"] == d["id"] == i["document_id"]
            and c["ingestion_id"] == i["id"] == s["current_run_id"] == s["desired_run_id"]
            and s["status"] == i["status"] == "ready"
            and s["content_hash"] == i["content_hash"] == d["content_hash"]
            and s["processing_version"] == i["processing_version"] == c["processing_version"]
        )
    except (KeyError, TypeError):
        valid = False
    if not valid:
        raise VectorFailure("source_provenance_invalid")
    complete = [
        span
        for span in sentences(d["text"])
        if not span.in_code and c["start"] <= span.start < span.end <= c["end"]
    ]
    return {
        "source_id": s["id"],
        "ingestion_id": i["id"],
        "document_id": d["id"],
        "chunk_id": c["id"],
        "content_hash": d["content_hash"],
        "chunk_hash": text_hash(c["text"]),
        "processing_version": c["processing_version"],
        "source_filename": d["source_filename"],
        "original_document_id": d.get("original_document_id"),
        "start": c["start"],
        "end": c["end"],
        "text": c["text"],
        "sentence_starts": [span.start - c["start"] for span in complete],
        "sentence_ends": [span.end - c["start"] for span in complete],
    }


class VectorRepository:
    def __init__(self, database, corpus="fictional-v1"):
        self.db, self.corpus = database, corpus

    def read(self, query, parameters=None):
        return self.db.execute(query, parameters, timeout=self.db.settings.vector_query_timeout)

    def write(self, callback, *args):
        @unit_of_work(timeout=self.db.settings.neo4j_import_timeout)
        def work(tx):
            return callback(tx, *args)

        try:
            with self.db.driver.session(database=self.db.settings.neo4j_database) as session:
                return session.execute_write(work)
        except (DriverError, Neo4jError, OSError) as exc:
            raise DatabaseUnavailable("Vector write unavailable") from exc

    def require_index(self):
        rows = self.read("SHOW VECTOR INDEXES YIELD * WHERE name = $name", {"name": INDEX})
        if len(rows) != 1 or rows[0]["state"] != "ONLINE":
            raise VectorFailure("vector_index_unavailable")
        r = rows[0]
        config = r["options"]["indexConfig"]
        if (
            r["labelsOrTypes"] != ["ChunkEmbedding"]
            or r["properties"] != ["embedding"]
            or config.get("vector.dimensions") != DIMENSION
            or str(config.get("vector.similarity_function", "")).casefold() != "cosine"
        ):
            raise VectorFailure("vector_index_incompatible")
        return r

    def canonical(self, sources, processing):
        return [
            canonical_record(r)
            for r in self.read(CANONICAL, {"sources": sources, "processing": processing})
        ]

    def begin(self, build, version, sources, processing, signature):
        token, now = uuid4().hex, time.time()
        return self.write(self._begin, build, version, sources, processing, signature, token, now)

    def _begin(self, tx, build, version, sources, processing, signature, token, now):
        row = tx.run(
            "MERGE (c:VectorCorpus {id: $corpus}) SET c.lock_marker = $token "
            "RETURN properties(c) AS c",
            corpus=self.corpus,
            token=token,
        ).single()["c"]
        if row.get("claim_token") and row.get("lease_until", 0) > now:
            raise VectorFailure("indexing_busy")
        if row.get("current_build") == build:
            return None
        # Invalidate old build before any embedding work. Failure cannot publish old evidence.
        tx.run(
            "MATCH (c:VectorCorpus {id: $corpus}) "
            "SET c.current_build = null, c.desired_build = $build, c.status = 'processing', "
            "c.claim_token = $token, c.lease_until = $lease "
            "MERGE (b:VectorBuild {id: $build}) SET b.status = 'processing', "
            "b.embedding_version = $version, b.model = $model, b.source_ids = $sources, "
            "b.processing_version = $processing, b.signature = $signature, "
            "b.error_category = null, b.started_at = $now",
            corpus=self.corpus,
            build=build,
            token=token,
            lease=now + 300,
            version=version,
            model=MODEL,
            sources=sources,
            processing=processing,
            signature=signature,
            now=now,
        ).consume()
        return token

    def _guard(self, tx, build, token):
        row = tx.run(
            "MATCH (c:VectorCorpus {id: $corpus}) SET c.lock_marker = $token "
            "RETURN properties(c) AS c",
            corpus=self.corpus,
            token=token,
        ).single()
        if (
            not row
            or row["c"].get("claim_token") != token
            or (
                row["c"].get("desired_build") != build
                or row["c"].get("lease_until", 0) < time.time()
            )
        ):
            raise VectorFailure("indexing_claim_expired")
        tx.run(
            "MATCH (c:VectorCorpus {id: $id}) SET c.lease_until = $lease",
            id=self.corpus,
            lease=time.time() + 300,
        ).consume()

    def put(self, build, token, records, vectors, version):
        rows = [
            {
                **r,
                "id": stable_id("chunk-vector", build, r["chunk_id"]),
                "build_id": build,
                "embedding_version": version,
                "model": MODEL,
                "embedding": validate_vector(v),
            }
            for r, v in zip(records, vectors, strict=True)
        ]
        self.write(self._put, build, token, rows)

    def _put(self, tx, build, token, rows):
        self._guard(tx, build, token)
        tx.run(
            "UNWIND $rows AS row MERGE (e:ChunkEmbedding {id: row.id}) SET e = row", rows=rows
        ).consume()

    def publish(self, build, token, records, sources, processing):
        return self.write(self._publish, build, token, records, sources, processing)

    def _publish(self, tx, build, token, records, sources, processing):
        self._guard(tx, build, token)
        current = [
            canonical_record(r.data())
            for r in tx.run(CANONICAL, sources=sources, processing=processing)
        ]
        if current != records:
            raise VectorFailure("source_changed_during_indexing")
        stored = [
            r["e"]
            for r in tx.run(
                "MATCH (e:ChunkEmbedding {build_id: $build}) "
                "RETURN properties(e) AS e ORDER BY e.chunk_id",
                build=build,
            )
        ]
        if len(stored) != len(records):
            raise VectorFailure("incomplete_indexing")
        for r, e in zip(records, stored, strict=True):
            if any(e.get(k) != v for k, v in r.items() if v is not None):
                raise VectorFailure("indexed_provenance_invalid")
            validate_vector(e["embedding"])
        summary = {
            "build_id": build,
            "documents": len({r["document_id"] for r in records}),
            "chunks": len(records),
            "status": "ready",
        }
        tx.run(
            "MATCH (c:VectorCorpus {id: $corpus}), (b:VectorBuild {id: $build}) "
            "SET c.status = 'ready', c.current_build = $build, c.claim_token = null, "
            "c.lease_until = 0, b.status = 'ready', b.summary_json = $summary, b.ready_at = $now",
            corpus=self.corpus,
            build=build,
            summary=json.dumps(summary),
            now=time.time(),
        ).consume()
        return summary

    def fail(self, build, token, category):
        self.read(
            "MATCH (c:VectorCorpus {id: $corpus}), (b:VectorBuild {id: $build}) "
            "WHERE c.claim_token = $token AND c.desired_build = $build "
            "SET c.status = 'failed', c.current_build = null, c.claim_token = null, "
            "b.status = 'failed', b.error_category = $category",
            {"corpus": self.corpus, "build": build, "token": token, "category": category},
        )

    def current(self, version):
        rows = self.read(
            "MATCH (c:VectorCorpus {id: $corpus}), (b:VectorBuild {id: c.current_build}) "
            "WHERE c.status = 'ready' AND b.status = 'ready' AND c.desired_build = b.id "
            "AND b.embedding_version = $version RETURN properties(b) AS b",
            {"corpus": self.corpus, "version": version},
        )
        if len(rows) != 1:
            raise VectorFailure("vector_corpus_unavailable")
        return rows[0]["b"]

    def search(self, vector, k, version):
        self.require_index()
        build = self.current(version)
        # 5.26 has no metadata prefilter. Exhaust candidates on this bounded local corpus,
        # then filter publication and take k. This prevents historical vectors starving k.
        count = self.read("MATCH (e:ChunkEmbedding) RETURN count(e) AS n")[0]["n"]
        if count > 10000:
            raise VectorFailure("vector_corpus_capacity")
        if not count:
            return build["id"], []
        rows = self.read(
            SEARCH,
            {
                "index": INDEX,
                "candidates": count,
                "vector": validate_vector(vector),
                "build": build["id"],
                "corpus": self.corpus,
                "embedding": version,
                "k": k,
            },
        )
        if self.current(version)["id"] != build["id"]:
            raise VectorFailure("vector_corpus_changed")
        chunks = []
        for row in rows:
            record = canonical_record(row)
            e = row["embedding"]
            if any(e.get(key) != value for key, value in record.items() if value is not None):
                raise VectorFailure("indexed_provenance_invalid")
            chunks.append(RetrievedChunk(**record, score=row["score"], embedding_version=version))
        return build["id"], chunks
