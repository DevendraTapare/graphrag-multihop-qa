import json
import time

from app.db.neo4j import DatabaseUnavailable
from app.extraction.models import stable_id
from app.vector.models import VectorFailure


class VectorIndexer:
    def __init__(self, repository, embedder):
        self.repo, self.embedder = repository, embedder

    def index(self, sources, processing):
        self.repo.require_index()
        sources = sorted(set(sources))
        records = self.repo.canonical(sources, processing)
        # Empty documents may have zero chunks; verify every requested source is ready.
        ready = self.repo.read(
            "MATCH (s:IngestionSource), (i:Ingestion) WHERE s.id IN $sources "
            "AND s.status = 'ready' AND i.id = s.current_run_id AND i.id = s.desired_run_id "
            "AND i.status = 'ready' AND s.processing_version = $p AND i.processing_version = $p "
            "RETURN s.id AS id, i.expected_chunk_count AS expected_chunks",
            {"sources": sources, "p": processing},
        )
        if {r["id"] for r in ready} != set(sources):
            raise VectorFailure("source_corpus_incomplete")
        if any(
            sum(c["source_id"] == r["id"] for c in records) != r["expected_chunks"] for r in ready
        ):
            raise VectorFailure("source_corpus_incomplete")
        signature = stable_id("vector-plan", records, sources, processing, self.embedder.version)
        build = stable_id("vector-build", self.repo.corpus, signature)
        token = self.repo.begin(build, self.embedder.version, sources, processing, signature)
        if token is None:
            current = self.repo.current(self.embedder.version)
            # Recheck stored vectors and provenance, without altering publication.
            stored = self.repo.read(
                "MATCH (e:ChunkEmbedding {build_id: $build}) RETURN properties(e) AS e "
                "ORDER BY e.chunk_id",
                {"build": build},
            )
            from app.vector.embedding import validate_vector

            if len(stored) != len(records):
                raise VectorFailure("incomplete_indexing")
            for r, e in zip(records, stored, strict=True):
                if any(e["e"].get(k) != v for k, v in r.items() if v is not None):
                    raise VectorFailure("indexed_provenance_invalid")
                validate_vector(e["e"]["embedding"])
            return {**json.loads(current["summary_json"]), "cached": True}
        started = time.perf_counter()
        try:
            for start in range(0, len(records), 32):
                group = records[start : start + 32]
                vectors = self.embedder.encode([r["text"] for r in group])
                self.repo.put(build, token, group, vectors, self.embedder.version)
            summary = self.repo.publish(build, token, records, sources, processing)
            return {
                **summary,
                "cached": False,
                "indexing_ms": (time.perf_counter() - started) * 1000,
            }
        except Exception as exc:
            category = exc.category if isinstance(exc, VectorFailure) else "indexing_failed"
            try:
                self.repo.fail(build, token, category)
            except DatabaseUnavailable:
                pass
            raise
